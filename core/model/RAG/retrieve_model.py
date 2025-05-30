'''RAG retrieval model class for local knowledge base'''
from core.model.model_base import Modelbase
from core.model.model_base import ModelStatus
from config.config import Config
from env import get_app_root

import os
import shutil
import markdown  # pip install markdown
import unstructured  # pip install unstructured
import docx  # pip install python-docx

from langchain_community.embeddings import ModelScopeEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    JSONLoader,
    MHTMLLoader,
    TextLoader,
    CSVLoader,
)
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from modelscope.hub.snapshot_download import snapshot_download


# Retrieval model
class Retrievemodel(Modelbase):

    _retriever: VectorStoreRetriever

    def __init__(self, *args, **krgs):
        super().__init__(*args, **krgs)

        # Please modify this to your own embedding model download location
        self._embedding_download_path = Config.get_instance().get_with_nested_params(
            "model", "embedding", "model-path"
        )
        self._embedding_model_name = Config.get_instance().get_with_nested_params(
            "model", "embedding", "model-name"
        )
        self._embedding_model_path = os.path.join(
            self._embedding_download_path, self._embedding_model_name
        )
        if not os.path.exists(self._embedding_model_path):
            try:
                # If empty, download model from modelscope
                model_dir = snapshot_download(
                    self._embedding_model_name,
                    cache_dir=self._embedding_download_path,
                )
                print(f"Model downloaded and saved to {model_dir}")
            except Exception as e:
                print(f"Failed to download model: {e}")
                if os.path.exists(self._embedding_model_path):
                    shutil.rmtree(self._embedding_model_path)
        # self._loader = PyPDFDirectoryLoader
        self._text_splitter = RecursiveCharacterTextSplitter
        # self._embedding = OpenAIEmbeddings()
        self._embedding = ModelScopeEmbeddings(model_id=self._embedding_model_path)
        self._data_path = Config.get_instance().get_with_nested_params(
            "Knowledge-base-path"
        )
        if not os.path.exists(self._data_path):
            os.makedirs(self._data_path)
        self._user_retrievers = {}


    # Build vector store
    def build(self):

        # Load PDF files
        pdf_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        pdf_docs = pdf_loader.load()

        # Load Word files
        docx_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.docx",
            loader_cls=UnstructuredWordDocumentLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        docx_docs = docx_loader.load()

        # Load txt files
        txt_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.txt",
            loader_cls=TextLoader,
            silent_errors=True,
            loader_kwargs={"autodetect_encoding": True},
            use_multithreading=True,
        )
        txt_docs = txt_loader.load()

        # Load csv files
        csv_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.csv",
            loader_cls=CSVLoader,
            silent_errors=True,
            loader_kwargs={"autodetect_encoding": True},
            use_multithreading=True,
        )
        csv_docs = csv_loader.load()

        # Load html files
        html_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.html",
            loader_cls=UnstructuredHTMLLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        html_docs = html_loader.load()

        mhtml_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.mhtml",
            loader_cls=MHTMLLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        mhtml_docs = mhtml_loader.load()

        # Load markdown files
        markdown_loader = DirectoryLoader(
            self._data_path,
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader,
            silent_errors=True,
            use_multithreading=True,
        )
        markdown_docs = markdown_loader.load()

        # To use JSON data, you need to set jq statements and content_key to extract specific fields, which varies with different JSON data structures and is quite cumbersome.
        # Official documentation: https://api.python.langchain.com/en/latest/document_loaders/langchain_community.document_loaders.json_loader.JSONLoader.html
        # json_loader = DirectoryLoader(self._data_path, glob="**/*.json", loader_kwargs={"jq_schema": ".","text_content":False},loader_cls=JSONLoader, silent_errors=True)
        # json_docs = json_loader.load()

        # Merge documents
        docs = (
            pdf_docs
            + docx_docs
            + txt_docs
            + csv_docs
            + html_docs
            + mhtml_docs
            + markdown_docs
        )

        # Create a RecursiveCharacterTextSplitter object to split documents into chunks, chunk_size is the maximum chunk size, chunk_overlap is the size that can overlap between chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=100
        )
        splits = text_splitter.split_documents(docs)

        # Use FAISS to create a vector database, storing the split documents and their embedding vectors
        vectorstore = FAISS.from_documents(documents=splits, embedding=self._embedding)
        # Convert vector store to retriever, set retrieval parameter k to 6, meaning return the 6 most similar documents
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

        # Set model status to BUILDING
        self._model_status = ModelStatus.BUILDING

    @property
    def retriever(self) -> VectorStoreRetriever:
        if self._model_status == ModelStatus.FAILED:
            self.build()
            return self._retriever
        else:
            return self._retriever

    def build_user_vector_store(self):
        """Load files from user's folder and build vector store for user based on user ID"""
        user_data_path = os.path.join("user_data", self.user_id)  # User's independent folder
        if not os.path.exists(user_data_path):
            print(f"User folder {user_data_path} does not exist")
            return

        try:
            # Clean up old vector store (if it exists)
            if self.user_id in self._user_retrievers:
                del self._user_retrievers[self.user_id]
                print(f"Old vector store for user {self.user_id} has been deleted")

                # Load files from user's folder and build vector store
                # Load PDF files
                pdf_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.pdf",
                    loader_cls=PyPDFLoader,
                    silent_errors=True,
                    use_multithreading=True,
                )
                pdf_docs = pdf_loader.load()

                # Load Word files
                docx_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.docx",
                    loader_cls=UnstructuredWordDocumentLoader,
                    silent_errors=True,
                    use_multithreading=True,
                )
                docx_docs = docx_loader.load()

                # Load txt files
                txt_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.txt",
                    loader_cls=TextLoader,
                    silent_errors=True,
                    loader_kwargs={"autodetect_encoding": True},
                    use_multithreading=True,
                )
                txt_docs = txt_loader.load()

                # Load csv files
                csv_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.csv",
                    loader_cls=CSVLoader,
                    silent_errors=True,
                    loader_kwargs={"autodetect_encoding": True},
                    use_multithreading=True,
                )
                csv_docs = csv_loader.load()

                # Load html files
                html_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.html",
                    loader_cls=UnstructuredHTMLLoader,
                    silent_errors=True,
                    use_multithreading=True,
                )
                html_docs = html_loader.load()

                mhtml_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.mhtml",
                    loader_cls=MHTMLLoader,
                    silent_errors=True,
                    use_multithreading=True,
                )
                mhtml_docs = mhtml_loader.load()

                # Load markdown files
                markdown_loader = DirectoryLoader(
                    user_data_path,
                    glob="**/*.md",
                    loader_cls=UnstructuredMarkdownLoader,
                    silent_errors=True,
                    use_multithreading=True,
                )
                markdown_docs = markdown_loader.load()

                # To use JSON data, you need to set jq statements and content_key to extract specific fields, which varies with different JSON data structures and is quite cumbersome.
                # Official documentation: https://api.python.langchain.com/en/latest/document_loaders/langchain_community.document_loaders.json_loader.JSONLoader.html
                # json_loader = DirectoryLoader(self._data_path, glob="**/*.json", loader_kwargs={"jq_schema": ".","text_content":False},loader_cls=JSONLoader, silent_errors=True)
                # json_docs = json_loader.load()

                # Merge documents
                docs = (
                    pdf_docs
                    + docx_docs
                    + txt_docs
                    + csv_docs
                    + html_docs
                    + mhtml_docs
                    + markdown_docs
                )

                if not docs:
                    print(f"User {self.user_id} folder has no documents")
                    return

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=2000, chunk_overlap=100
                )
                splits = text_splitter.split_documents(docs)

                # Build vector store for the user
                vectorstore = FAISS.from_documents(
                    documents=splits, embedding=self._embedding
                )
                user_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

                # Store user's retriever in dictionary
                self._user_retrievers[self.user_id] = user_retriever
                print(f"User {self.user_id} vector store has been built")

        except Exception as e:
            print(f"Error building user {self.user_id} vector store: {e}")

    def get_user_retriever(self) -> VectorStoreRetriever:
        """Get user's retriever, return None if it doesn't exist"""
        return self._user_retrievers.get(self.user_id, None)

    def upload_user_file(self, file):
        """Store user uploaded file in user's folder"""
        user_data_path = os.path.join("user_data", self.user_id)
        os.makedirs(user_data_path, exist_ok=True)  # Ensure user folder exists

        file_path = os.path.join(user_data_path, file.name)
        with open(file_path, "wb") as f:
            f.write(file.read())

        print(f"File {file.name} has been successfully uploaded to user {self.user_id}'s folder")

    # Show user uploaded files
    def list_uploaded_files(self):
        """Show files already uploaded in user's folder"""
        user_data_path = os.path.join("user_data", self.user_id)
        if not os.path.exists(user_data_path):
            print(f"User folder {user_data_path} does not exist")
            return []

        files = os.listdir(user_data_path)
        if files:
            print(f"Files already uploaded by user {self.user_id}:")
            for file in files:
                print(file)
        else:
            print(f"User {self.user_id} folder is empty")

        return files

    # Delete specified file or empty user folder
    def delete_uploaded_file(self, filename=None):
        """Delete specified file from user's folder or empty folder"""
        user_data_path = os.path.join("user_data", self.user_id)
        if not os.path.exists(user_data_path):
            print(f"User folder {user_data_path} does not exist")
            return

        if filename:
            file_path = os.path.join(user_data_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {filename} has been successfully deleted")
            else:
                print(f"File {filename} does not exist")
        else:
            # Empty folder
            for file in os.listdir(user_data_path):
                file_path = os.path.join(user_data_path, file)
                os.remove(file_path)
            print(f"User {self.user_id} folder has been emptied")

    def view_uploaded_file(self, filename):
        """Return file path of user file based on filename"""
        user_data_path = os.path.join("user_data", self.user_id)  # Define user folder path
        file_path = os.path.join(user_data_path, filename)  # Concatenate full file path

        if not os.path.exists(file_path):
            print(f"File {filename} does not exist")
            return None

        # Return full path of file when file exists
        print(f"File {filename} path has been successfully retrieved")
        return file_path


INSTANCE = Retrievemodel()
