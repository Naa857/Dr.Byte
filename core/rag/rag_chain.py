# There are many types of retrieve, this file is used to call different RAG type interfaces
from core.rag.retrieve.retrieve_document import retrieve_docs
from typing import List
from openai import Stream
from openai.types.chat import ChatCompletionChunk
from core.client.clientfactory import Clientfactory


def invoke(question: str, history: List[List]) -> Stream[ChatCompletionChunk]:
    try:
        docs, _context = retrieve_docs(
            question
        )  # Here we get the retrieved file fragments and processed text
    except Exception as e:
        _context = ""

    prompt = f"Please answer the question based on the searched file information:\n{_context}\n Question:\n{question}"
    response = Clientfactory().get_client().chat_with_ai_stream(prompt)

    return response
