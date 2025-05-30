'''RAG retrieval model class for internet search'''
from core.model.model_base import Modelbase
from core.model.model_base import ModelStatus

import os
from env import get_app_root

from langchain_community.embeddings import ModelScopeEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import DirectoryLoader, MHTMLLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS

from config.config import Config

# Retrieval model
class InternetModel(Modelbase):
    
    _retriever: VectorStoreRetriever

    def __init__(self,*args,**krgs):
        super().__init__(*args,**krgs)

        # Please modify this to your own embedding model download location
        self._embedding_model_path =Config.get_instance().get_with_nested_params("model", "embedding", "model-name")
        self._text_splitter = RecursiveCharacterTextSplitter
        #self._embedding = OpenAIEmbeddings()
        self._embedding = ModelScopeEmbeddings(model_id=self._embedding_model_path)
        self._data_path = os.path.join(get_app_root(), "data/cache/internet")
        
        #self._logger: Logger = Logger("rag_retriever")

    # Build vector store
    def build(self):
        # Load html files
        html_loader = DirectoryLoader(self._data_path, glob="**/*.html", loader_cls=UnstructuredHTMLLoader, silent_errors=True, use_multithreading=True)
        html_docs = html_loader.load()
        
        mhtml_loader = DirectoryLoader(self._data_path, glob="**/*.mhtml", loader_cls=MHTMLLoader, silent_errors=True, use_multithreading=True)
        mhtml_docs = mhtml_loader.load()
        
        
        # Merge documents
        docs =  html_docs + mhtml_docs
        
        # Create a RecursiveCharacterTextSplitter object to split documents into chunks, chunk_size is the maximum chunk size, chunk_overlap is the size that can overlap between chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        
        # Use FAISS to create a vector database, storing the split documents and their embedding vectors
        vectorstore = FAISS.from_documents(documents=splits, embedding=self._embedding)
        # Convert vector store to retriever, set retrieval parameter k to 3, meaning return the 3 most similar documents
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        

        
    @property
    def retriever(self)-> VectorStoreRetriever:
        self.build()
        return self._retriever

INSTANCE = InternetModel()