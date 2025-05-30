'''Large model feature engineering, extract search keywords'''
from typing import List, Dict
from core.client.clientfactory import Clientfactory

_GENERATE_Internet_PROMPT_ = (
    "Please extract a searchable question from the user's query (without any extra content)"
)


def __construct_messages(
    question: str, history: List[List | None]
) -> List[Dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": "You are now playing the role of information extraction. Based on user input and AI responses, correctly extract information without including prompt text",
        }
    ]

    messages.append({"role": "user", "content": f"User question: {question}"})
    messages.append({"role": "user", "content": _GENERATE_Internet_PROMPT_})

    return messages


def extract_question(question: str, history: List[List | None] | None = None) -> str:
    messages = __construct_messages(question, history or [])
    result = Clientfactory().get_client().chat_using_messages(messages)

    return result
