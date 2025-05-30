'''Feature engineering for large models, making them output data in JSON format'''
import json
import re
from typing import List, Dict
from core.client.clientfactory import Clientfactory

# JSON template for generating docx content
__output_format_docx = json.dumps({
    "title": "example title",
    "sections": [
        {
            "heading": "Section 1",
            "paragraphs": [
                {
                    "heading": "Paragraph 1",
                    "content": "Details of paragraph 1"
                },
                {
                    "heading": "Paragraph 2",
                    "content": "Details of paragraph 2"
                }
            ]
        },
        {
            "heading": "Section 2",
            "paragraphs": [
                {
                    "heading": "Paragraph 1",
                    "content": "Details of paragraph 1"
                },
                {
                    "heading": "Paragraph 2",
                    "content": "Details of paragraph 2"
                },
                {
                    "heading": "Paragraph 3",
                    "content": "Details of paragraph 3"
                }
            ]
        }
    ]
}, ensure_ascii=True)

# Prompt for generating docx content
_GENERATE_DOCX_PROMPT_ = f'''Please generate detailed Word document content based on the user's request without omitting any details. Output according to this JSON format {__output_format_docx}. Only return JSON, do not wrap it in ```, and do not return markdown format.'''

# Construct message function, history is included
def __construct_messages_docx(question: str, history: List[List | None]) -> List[Dict[str, str]]:
    messages = [
        {"role": "system",
         "content": "You are now playing the role of information extraction. You are required to correctly extract information based on user input and AI responses."}]

    for user_input, ai_response in history:
        messages.append({"role": "user", "content": user_input})
        messages.append(
            {"role": "assistant", "content": repr(ai_response)})
    messages.append({"role": "system", "content": question})
    messages.append({"role": "user", "content": _GENERATE_DOCX_PROMPT_})

    return messages

# Function to generate docx content
def generate_docx_content(question: str,
                         history: List[List | None] | None = None) -> str:
    messages = __construct_messages_docx(question, history or [])
    print(messages)
    result = Clientfactory().get_client().chat_using_messages(messages)
    print(result)
    print(type(result))

    # Remove extra parts from generated content, such as "json" keyword or backticks
    result = re.sub(r'\bjson\b', '', result)
    result = re.sub(r'`', '', result)

    # Check if the end of generated content is correct
    index_of_last = result.rfind('"')
    total_result = None
    print(result)

    if index_of_last != -1 and result[index_of_last + 1:] == '}]}]}':
        # If format is correct, make no changes
        total_result = result
        print(total_result)
        return total_result
    else:
        # If format is incorrect, fix JSON ending
        total_result = result[:index_of_last + 1] + '}]}]}'
        print(total_result)
        return total_result
