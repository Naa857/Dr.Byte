'''Feature engineering for large models, extracting text and language for TTS'''
from typing import List, Dict
from core.client.clientfactory import Clientfactory

_GENERATE_AUDIO_PROMPT_ = (
    "Please extract the text that needs to be converted to speech from the above conversation, do not include prompt text"
)


def __construct_messages(
    question: str, history: List[List | None]
) -> List[Dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": "You are now playing the role of information extraction. You are required to correctly extract information based on user input and AI responses, without including prompt text",
        }
    ]

    for user_input, ai_response in history:
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": repr(ai_response)})

    messages.append({"role": "user", "content": question})
    messages.append({"role": "user", "content": _GENERATE_AUDIO_PROMPT_})

    return messages


def extract_text(question: str, history: List[List | None] | None = None) -> str:
    messages = __construct_messages(question, history or [])
    result = Clientfactory().get_client().chat_using_messages(messages)

    return result


def extract_language(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are now playing the role of information extraction. You are required to correctly extract information based on user input and AI responses, do not repeat, without including prompt text",
        },
        {
            "role": "user",
            "content": f"""
            Please extract the language for text-to-speech from the following text. The result can only be one of these 5 options (Mandarin, Shaanxi dialect, Northeastern dialect, Cantonese, Taiwanese),
            If the text contains language information but not one of these 5, such as English, Japanese... then return a single word: other,
            If the following text does not contain language information, return a single word: none.
            (Note: Do not include any symbols or prompt information in the result):\n{text}
            """,
        },
    ]
    result = Clientfactory().get_client().chat_using_messages(messages)
    return result


def get_tts_model_name(lang: str, gender: str) -> str:
    return "en-HK-YanNeural", False  # Can set a default return value to prevent unmatched cases


def extract_gender(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are now playing the role of information extraction. You are required to correctly extract information based on user input and AI responses, do not repeat, without including prompt text",
        },
        {
            "role": "user",
            "content": f"Please extract the voice gender for text-to-speech from the following text. The result can only be one of two options: male or female. If the following text does not contain voice gender information, "
            f"return a single word: none. (Note: Do not include any symbols or prompt information in the result):\n{text}",
        },
    ]

    result = Clientfactory().get_client().chat_using_messages(messages)

    return result
