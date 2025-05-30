'''Store tool functions for handling different Q&A types, core file'''

import base64
from typing import Callable, List, Dict, Tuple
import time
import json
from core.client.clientfactory import Clientfactory
from core.qa.purpose_type import userPurposeType
from pathlib import Path
from core.ppt_docx.ppt_generation import generate as generate_ppt
from core.ppt_docx.ppt_content import generate_ppt_content
from core.ppt_docx.docx_generation import generate_docx_content as generate_docx
from core.ppt_docx.docx_content import generate_docx_content
from core.rag.rag_chain import invoke as rag_chain
from core.audio.audio_extract import (
    extract_text,
    extract_language,
    extract_gender,
    get_tts_model_name,
)
from core.audio.audio_generate import audio_generate
from core.model.KG.search_service import search
from core.internet.Internet_chain import InternetSearchChain
from core.kg.Graph import GraphDao
from config.config import Config
from core.qa.purpose_type import userPurposeType
from env import get_env_value


_dao = GraphDao()

def is_file_path(path):
    return Path(path).exists()

def relation_tool(entities: List[Dict] | None) -> str | None:
    if not entities or len(entities) == 0:
        return None

    relationships = set()  # Use set to avoid duplicate relationships
    relationship_match = []

    searchKey = Config.get_instance().get_with_nested_params("model", "graph-entity", "search-key")
    # Traverse each entity and query relationships with other entities
    for entity in entities:
        entity_name = entity[searchKey]
        for k, v in entity.items():
            relationships.add(f"{entity_name} {k}: {v}")

        # Query relationships between each entity and other entities a-r-b
        relationship_match.append(_dao.query_relationship_by_name(entity_name))
        
    # Extract and record relationships between each entity and other entities
    for i in range(len(relationship_match)):
        for record in relationship_match[i]:
            # Get names of start and end nodes
            start_name = record["r"].start_node[searchKey]
            end_name = record["r"].end_node[searchKey]

            # Get relationship type
            rel = type(record["r"]).__name__  # Get relationship name, e.g. CAUSES

            # Build relationship string and add to set, ensuring no duplicates
            relationships.add(f"{start_name} {rel} {end_name}")

    # Return relationship set content
    if relationships:
        return ";".join(relationships)
    else:
        return None


def check_entity(question: str) -> List[Dict]:
    code, result = search(question)
    if code == 0:
        return result
    else:
        return None


def KG_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    kg_info = None
    try:
        # Before using knowledge graph, need to check entities in the question
        entities = check_entity(question)
        kg_info = relation_tool(entities)
    except:
        pass

    if kg_info is not None:
        print(f"KG_tool: \n {kg_info}")
        question = f"{question}\nFrom the information retrieved from the knowledge graph, the following information is obtained: {kg_info}\nPlease answer based on the information from the knowledge graph and provide the information retrieved from the knowledge graph"

    response = Clientfactory().get_client().chat_with_ai_stream(question, history)
    return (response, question_type)


# Function to handle text questions
def process_text_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    response = Clientfactory().get_client().chat_with_ai_stream(question, history)
    return (response, question_type)


# Handle RAG questions
def RAG_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    # First use question to retrieve docs
    response = rag_chain(question, history)
    return (response, question_type)


# Function to handle ImageGeneration questions
def process_images_tool(question_type, question, history, image_url=None):
    client = Clientfactory.get_special_client(client_type=question_type)
    response = client.images.generations(
        model=get_env_value("IMAGE_GENERATE_MODEL"),  # Fill in the model code to call
        prompt=question,
    )
    print(response.data[0].url)
    return (response.data[0].url, question_type)


def process_image_describe_tool(question_type, question, history, image_url=None):
    if question == "Please modify the following sentence and output it without additional text, sentence: 'What would you like to know? I will do my best to assist you.'":
        question = "Describe this image and explain the main content of the image"
    image_bases = []
    for img_url in image_url:
        if is_file_path(img_url):
            with open(img_url, "rb") as img_file:
                image_base = base64.b64encode(img_file.read()).decode("utf-8")
                image_bases.append(image_base)
        else:
            image_bases.append(img_url)

    # Build messages content
    message_content = []
    for image_base in image_bases:
        message_content.append({"type": "image_url", "image_url": {"url": image_base}})
    # Add question text content
    message_content.append({"type": "text", "text": question})

    client = Clientfactory.get_special_client(client_type=question_type)
    # Send request
    response = client.chat.completions.create(
        model=get_env_value("IMAGE_DESCRIBE_MODEL"),
        messages=[
            {
                "role": "user",
                "content": message_content,
            }
        ],
    )
    return (response.choices[0].message.content, question_type)


def process_ppt_tool(
    question_type, question: str, history: List[List[str] | None] = None, image_url=None
) -> Tuple[Tuple[str, str], userPurposeType]:
    raw_text: str = generate_ppt_content(question, history)
    try:
        ppt_content = json.loads(raw_text)
    except:
        return None, userPurposeType.PPT
    ppt_file: str = generate_ppt(
        ppt_content
    )  # This statement may not output in the correct format due to model limitations, which may cause conflicts. Use str regex to modify and delete some abnormal symbols, otherwise bugs will occur
    return (ppt_file, "ppt"), userPurposeType.PPT


def process_docx_tool(
    question_type, question: str, history: List[List[str] | None] = None, image_url=None
) -> Tuple[Tuple[str, str], userPurposeType]:
    # First generate word document content
    raw_text: str = generate_docx_content(question, history)
    try:
        docx_content = json.loads(raw_text)
    except:
        return None, userPurposeType.Docx
    docx_file: str = generate_docx(docx_content)
    return (docx_file, "docx"), userPurposeType.Docx


def process_text_video_tool(question_type, question, history, image_url=None):
    client = Clientfactory.get_special_client(client_type=question_type)
    try:
        chatRequest = client.videos.generations(
            model=get_env_value("VIDEO_GENERATE_MODEL"),
            prompt=question,
        )
        print(chatRequest)

        start_time = time.time()  # Start timing
        video_url = None
        timeout = 120
        while time.time() - start_time < timeout:
            # Request video generation result
            print(chatRequest.id)
            response = client.videos.retrieve_videos_result(id=chatRequest.id)

            # Check if task status is successful
            if response.task_status == "SUCCESS" and response.video_result:
                video_url = response.video_result[0].url
                print("Video URL:", video_url)
                return ((video_url, "video"), question_type)
            else:
                print("Task not completed, please wait...")

            # Wait for a while before requesting again
            time.sleep(2)  # Wait 2 seconds after each request before continuing

    except:
        return (None, question_type)


# Function to handle audio questions
def process_audio_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    # First let the large language model generate text to be converted to speech
    text = extract_text(question, history)
    # Determine which language to generate (Northeast, Shaanxi, Cantonese...)
    lang = extract_language(question)
    # Determine whether to generate male or female voice
    gender = extract_gender(question)
    # All three steps above interact with the large language model

    # Select model for generation
    model_name, success = get_tts_model_name(lang=lang, gender=gender)
    if success:
        audio_file = audio_generate(text, model_name)
    else:
        audio_file = audio_generate(
            "Due to missing target language package, I will reply to you in Mandarin." + text, model_name
        )
    return ((audio_file, "audio"), question_type)


# Function to handle InternetSearch questions
def process_InternetSearch_tool(
    question_type: userPurposeType,
    question: str,
    history: List[List | None] = None,
    image_url=None,
):
    response, links, success = InternetSearchChain(question, history)
    return (response, question_type, links, success)


QUESTION_TO_FUNCTION = {
    userPurposeType.text: process_text_tool,
    userPurposeType.RAG: RAG_tool,
    userPurposeType.ImageGeneration: process_images_tool,
    userPurposeType.Audio: process_audio_tool,
    userPurposeType.InternetSearch: process_InternetSearch_tool,
    userPurposeType.ImageDescribe: process_image_describe_tool,
    userPurposeType.PPT: process_ppt_tool,
    userPurposeType.Docx: process_docx_tool,
    userPurposeType.Video: process_text_video_tool,
    userPurposeType.KnowledgeGraph: KG_tool,
}


# Map question to function based on user's intent
def map_question_to_function(purpose: userPurposeType) -> Callable:
    if purpose in QUESTION_TO_FUNCTION:
        return QUESTION_TO_FUNCTION[purpose]
    else:
        raise ValueError("No function found for the given intent")
