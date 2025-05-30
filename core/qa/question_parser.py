'''Question type judgment function, classifies based on specific input and large model.'''
from typing import List, Dict

from core.client.clientfactory import Clientfactory

from core.qa.prompt_templates import get_question_parser_prompt
from core.qa.purpose_type import purpose_map
from core.qa.purpose_type import userPurposeType

from icecream import ic


def parse_question(question: str, image_url=None) -> userPurposeType:

    if "Based on the knowledge base" in question:
        return purpose_map["Knowledge Base Based"]
    
    if "Based on the knowledge graph" in question:
        return purpose_map["Knowledge Graph Based"]

    if "search" in question:
        return purpose_map["Internet Search"]
    
    if ("word" in question or "Word" in question or "WORD" in question) and ("generate" in question or "create" in question):
        return purpose_map["Word Generation"]
    
    if ("ppt" in question or "PPT" in question or "PPT" in question) and ("generate" in question or "create" in question):
        return purpose_map["PPT Generation"]
    
    if image_url is not None:
        return purpose_map["Image Description"]

    # In this function we use the large model to determine the question type
    prompt = get_question_parser_prompt(question)
    response = Clientfactory().get_client().chat_with_ai(prompt)
    ic("Large model classification result: " + response)

    if response == "Image Generation" and len(question) > 0:
        return purpose_map["Image Generation"]
    if response == "Video Generation" and len(question) > 0:
        return purpose_map["Video Generation"]
    if response == "PPT Generation" and len(question) > 0:
        return purpose_map["PPT Generation"]
    if response == "Word Generation" and len(question) > 0:
        return purpose_map["Word Generation"]
    if response == "Audio Generation" and len(question) > 0:
        return purpose_map["Audio Generation"]
    if response == "Text Generation":
        return purpose_map["Text Generation"]
    return purpose_map["Other"]



