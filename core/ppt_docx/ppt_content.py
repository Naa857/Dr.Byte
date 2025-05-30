'''Feature engineering for large models, making them output data in JSON format'''
import json
from typing import List, Dict
import re

from core.client.clientfactory import Clientfactory

# Output format
__output_format = json.dumps({
    "title": "example title",
    "pages": [
        {
            "title": "title for page 1",
            "content": [
                {
                    "title": "title for paragraph 1",
                    "description": "detail for paragraph 1",
                },
                {
                    "title": "title for paragraph 2",
                    "description": "detail for paragraph 2",
                },
            ],
        },
        {
            "title": "title for page 2",
            "content": [
                {
                    "title": "title for paragraph 1",
                    "description": "detail for paragraph 1",
                },
                {
                    "title": "title for paragraph 2",
                    "description": "detail for paragraph 2",
                },
                {
                    "title": "title for paragraph 3",
                    "description": "detail for paragraph 3",
                },
            ],
        },
    ],
}, ensure_ascii=True)

_GENERATE_PPT_PROMPT_ = f'''Please generate detailed PPT content based on the user's request without omitting any details. Output according to this JSON format {__output_format}. Only return JSON, do not wrap it in ```, and do not return markdown format.'''

def __construct_messages(question: str, history: List[List | None]) -> List[Dict[str, str]]:
    messages = [
        {"role": "system",
         "content": "You are now playing the role of information extraction. You are required to correctly extract information based on user input and AI responses."}]

    for user_input, ai_response in history:
        messages.append({"role": "user", "content": user_input})
        messages.append(
            {"role": "assistant", "content": repr(ai_response)})
    messages.append({"role": "system", "content": question})
    messages.append({"role": "user", "content": _GENERATE_PPT_PROMPT_})

    return messages

# Generate ppt content and check format
def generate_ppt_content(question: str,
                         history: List[List | None] | None = None) -> str:
    messages = __construct_messages(question, history or [])
    print(messages)
    result = Clientfactory().get_client().chat_using_messages(messages)
    print(result)
    print(type(result))

    result = re.sub(r'\bjson\b', '', result)
    result = re.sub(r'`','',result)

    index_of_last = result.rfind('"')
    total_result=None
    print(result)

    if index_of_last!= -1 and result[index_of_last + 1:] == '}]}]}':
        # If already correct, make no changes
        total_result = result
        print(total_result)
        return total_result
    else:
        total_result = result[:index_of_last + 1] + '}]}]}'
        print(total_result)
        return total_result





