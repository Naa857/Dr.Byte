'''Call the interface in model/Internet to retrieve searched materials'''
from typing import List,Tuple
from langchain_core.documents import Document
from core.internet.Internet_service import retrieve

def format_docs(docs:List[Document]):
    return "\n-------------Separator--------------\n".join(doc.page_content for doc in docs)

def retrieve_html(question:str)->Tuple[List[Document],str]:
    docs = retrieve(question) # Here we get the files
    _context = format_docs(docs) # Here we process it into text
    print(_context)
    return (docs,_context)