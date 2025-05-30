'''Internet search service implementation'''
from typing import List
from langchain_core.documents import Document
from core.model.Internet.Internet_model import INSTANCE

def retrieve(question: str) -> List[Document]:
    """
    Retrieve relevant documents from internet search results
    
    Args:
        question (str): The search query
        
    Returns:
        List[Document]: List of retrieved documents
    """
    retriever = INSTANCE.retriever
    return retriever.get_relevant_documents(question) 