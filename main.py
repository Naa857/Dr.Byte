import base64
from core.qa.answer import get_answer
from core.qa.question_parser import parse_question
from core.qa.function_tool import process_image_describe_tool
from core.qa.purpose_type import userPurposeType
from core.audio.audio_generate import audio_generate

import PyPDF2
import chardet
import mimetypes
import gradio as gr
from icecream import ic
from docx import Document
from pydub import AudioSegment
import speech_recognition as sr
from opencc import OpenCC
import os


AVATAR = ("resource/user.png", "resource/bot.jpg")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# pip install whisper
# pip install openai-whisper
# pip install soundfile
# pip install pydub
# pip install opencc-python-reimplemented


def convert_to_simplified(text):
    converter = OpenCC("t2s")
    return converter.convert(text)


def convert_audio_to_wav(audio_file_path):
    audio = AudioSegment.from_file(audio_file_path)  # Automatically detect format
    wav_file_path = audio_file_path.rsplit(".", 1)[0] + ".wav"  # Generate WAV file path
    audio.export(wav_file_path, format="wav")  # Export audio file to WAV format
    return wav_file_path


def audio_to_text(audio_file_path):
    # Create recognizer object
    # If not WAV format, convert to WAV first
    if not audio_file_path.endswith(".wav"):
        audio_file_path = convert_audio_to_wav(audio_file_path)

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        # Use Google Web Speech API for speech recognition, no model download required but needs good network
        # text = recognizer.recognize_google(audio_data, language="zh-CN")
        # Use whisper for speech recognition, automatically downloads model locally
        text = recognizer.recognize_whisper(audio_data, language="zh")
        text_simplified = convert_to_simplified(text)
    return text_simplified


# pip install PyPDF2
def pdf_to_str(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def docx_to_str(file_path):
    doc = Document(file_path)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return "\n".join(text)


# pip install chardet
def text_file_to_str(text_file):
    with open(text_file, "rb") as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result["encoding"]

    # Read file using detected encoding
    with open(text_file, "r", encoding=encoding) as file:
        return file.read()


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


# Core function
def grodio_view(chatbot, chat_input):
    # Display user message immediately
    user_message = chat_input["text"]
    bot_response = "loading..."
    chatbot.append([user_message, bot_response])
    yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process uploaded files
    files = chat_input["files"]
    audios = []
    images = []
    pdfs = []
    docxs = []
    texts = []

    for file in files:
        file_type, _ = mimetypes.guess_type(file)
        if file_type.startswith("audio/"):
            audios.append(file)
        elif file_type.startswith("image/"):
            images.append(file)
        elif file_type.startswith("application/pdf"):
            pdfs.append(file)
        elif file_type.startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            docxs.append(file)
        elif file_type.startswith("text/"):
            texts.append(file)
        else:
            user_message += "Please modify and output the following sentence without additional text, sentence: 'This file type is not supported'"
            print(f"Unknown file type: {file_type}")

    # Process image files
    if images != []:
        image_url = images
        image_base64 = [image_to_base64(image) for image in image_url]

        for i, image in enumerate(image_base64):
            chatbot[-1][
                0
            ] += f"""
                <div>
                    <img src=\"data:image/png;base64,{image}\" style=\"max-width: 100%; height: auto; cursor: pointer;\" />
                </div>
                """
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None
    else:
        image_url = None

    question_type = parse_question(user_message, image_url)
    ic(question_type)

    # Process audio files
    if audios != []:
        for i, audio in enumerate(audios):
            audio_message = audio_to_text(audio)
            if audio_message == "":
                user_message += "Please modify and output the following sentence without additional text, sentence: 'Audio recognition failed, please try again later'"
            elif "作曲" in audio_message:
                user_message += "Please modify and output the following sentence without additional text, sentence: 'Sorry, I cannot understand music'"
            else:
                user_message += f"Audio {i+1} content: {audio_message}"

    if pdfs != []:
        for i, pdf in enumerate(pdfs):
            pdf_text = pdf_to_str(pdf)
            user_message += f"PDF{i+1} content: {pdf_text}"

    if docxs != []:
        for i, docx in enumerate(docxs):
            docx_text = docx_to_str(docx)
            user_message += f"DOCX{i+1} content: {docx_text}"

    if texts != []:
        for i, text in enumerate(texts):
            text_string = text_file_to_str(text)
            user_message += f"Text {i+1} content: {text_string}"

    if user_message == "":
        user_message = "Please modify and output the following sentence without additional text, sentence: 'What would you like to know? I will do my best to help you'"
    answer = get_answer(user_message, chatbot, question_type, image_url)
    bot_response = ""

    # Process text generation/other/document retrieval/knowledge graph retrieval
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        # Stream output
        try:
            for chunk in answer[0]:
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ""
                    bot_response = bot_response + (content or "")
                    chatbot[-1][1] = bot_response
                    yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None
                else:
                    print("Warning: Received empty chunk or invalid chunk format")
                    continue
        except Exception as e:
            print(f"Error processing stream: {str(e)}")
            chatbot[-1][1] = "Sorry, an error occurred while processing the response, please try again later"
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process image generation
    if answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        # No longer generate image description message
        chatbot[-1][1] = (image_url, "image")
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process video
    if answer[1] == userPurposeType.Video:
        if answer[0] is not None:
            video_url = answer[0][0]
            chatbot[-1][1] = f'<video width="50%" controls><source src="{video_url}" type="video/mp4"></video>'
        else:
            chatbot[-1][1] = "Sorry, video generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process PPT
    if answer[1] == userPurposeType.PPT:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, PPT generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process Docx
    if answer[1] == userPurposeType.Docx:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, document generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process audio generation
    if answer[1] == userPurposeType.Audio:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, audio generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process internet search
    if answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            output_message = (
                "Due to network issues, access to the internet failed. Below is my response based on existing knowledge:"
            )
        else:
            # Convert dictionary content to Markdown format links
            links = "\n".join(f"[{title}]({link})" for link, title in answer[2].items())
            links += "\n"
            output_message = f"Reference materials: {links}"
        for i in range(0, len(output_message)):
            bot_response = output_message[: i + 1]
            chatbot[-1][1] = bot_response
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None
        try:
            for chunk in answer[0]:
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ""
                    if content is not None:
                        bot_response = bot_response + content
                        chatbot[-1][1] = bot_response
                        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None
        except Exception as e:
            print(f"Error processing internet search response: {str(e)}")
            chatbot[-1][1] = "Sorry, an error occurred while processing the search results. Please try again."
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None


def gradio_audio_view(chatbot, audio_input):
    # Display user message immediately
    if audio_input is None:
        user_message = ""
    else:
        user_message = (audio_input, "audio")
    bot_response = "loading..."
    chatbot.append([user_message, bot_response])
    yield chatbot

    if audio_input is None:
        audio_message = "No audio"
    else:
        audio_message = audio_to_text(audio_input)

    chatbot[-1][0] = audio_message

    user_message = ""
    if audio_message == "No audio":
        user_message += "Please modify and output the following sentence without additional text, sentence: 'Welcome to talk to me, I will answer you with voice'"
    elif audio_message == "":
        user_message += "Please modify and output the following sentence without additional text, sentence: 'Audio recognition failed, please try again later'"
    elif "作曲" in audio_message:
        user_message += "Please modify and output the following sentence without additional text, sentence: 'Sorry, I cannot understand music'"
    else:
        user_message += audio_message

    if user_message == "":
        user_message = "Please modify and output the following sentence without additional text, sentence: 'What would you like to know? I will do my best to help you'"

    question_type = parse_question(user_message)
    ic(question_type)
    answer = get_answer(user_message, chatbot, question_type)
    bot_response = ""

    # Process text generation/other/document retrieval/knowledge graph retrieval
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        # Audio output
        try:
            bot_response = ""  # Ensure initialized as empty string
            for chunk in answer[0]:
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ""
                    if content is not None:  # Ensure content is not None
                        bot_response = bot_response + str(content)  # Use str() to ensure string conversion
                else:
                    print("Warning: Received empty chunk or invalid chunk format")
                    continue

            if not bot_response:  # If bot_response is empty
                bot_response = "Sorry, no valid response could be obtained"

            try:
                chatbot[-1][1] = (
                    audio_generate(
                        text=bot_response,
                        model_name="en-HK-YanNeural",
                    ),
                    "audio",
                )
            except Exception as e:
                print(f"Audio generation failed, returning text directly: {str(e)}")
                chatbot[-1][1] = bot_response 
        except Exception as e:
            print(f"Error processing stream: {str(e)}")
            chatbot[-1][1] = "Sorry, an error occurred while processing the response, please try again later"
            
        yield chatbot

    # Process image generation
    if answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        # No longer generate image description message
        chatbot[-1][1] = (image_url, "image")
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple"), None

    # Process video
    if answer[1] == userPurposeType.Video:
        if answer[0] is not None:
            video_url = answer[0][0]
            chatbot[-1][1] = f'<video width="50%" controls><source src="{video_url}" type="video/mp4"></video>'
        else:
            try:
                chatbot[-1][1] = (
                    audio_generate(
                        text="Sorry, video generation failed, please try again later",
                        model_name="en-HK-YanNeural",
                    ),
                    "audio",
                )
            except Exception as e:
                chatbot[-1][1] = "Sorry, video generation failed, please try again later"
        yield chatbot

    # Process PPT
    if answer[1] == userPurposeType.PPT:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            try:
                chatbot[-1][1] = (
                    audio_generate(
                        text="Sorry, PPT generation failed, please try again later",
                        model_name="en-HK-YanNeural",
                    ),
                    "audio",
                )
            except Exception as e:
                chatbot[-1][1] = "Sorry, PPT generation failed, please try again later"
        yield chatbot

    # Process Docx
    if answer[1] == userPurposeType.Docx:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            try:
                chatbot[-1][1] = (
                    audio_generate(
                        text="Sorry, document generation failed, please try again later",
                        model_name="en-HK-YanNeural",
                    ),
                    "audio",
                )
            except Exception as e:
                chatbot[-1][1] = "Sorry, document generation failed, please try again later"
        yield chatbot

    # Process audio generation
    if answer[1] == userPurposeType.Audio:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            try:
                chatbot[-1][1] = (
                    audio_generate(
                        text="Sorry, audio generation failed, please try again later",
                        model_name="en-HK-YanNeural",
                    ),
                    "audio",
                )
            except Exception as e:
                chatbot[-1][1] = "Sorry, audio generation failed, please try again later"
        yield chatbot

    # Process internet search
    if answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            bot_response = (
                "Due to network issues, access to the internet failed. Below is my response based on existing knowledge:"
            )
        # Audio output
        for chunk in answer[0]:
            # Get data from each chunk
            chunk_content = chunk.choices[0].delta.content or ""
            bot_response += chunk_content

        try:
            chatbot[-1][1] = (
                audio_generate(
                    text=bot_response,
                    model_name="en-HK-YanNeural",
                ),
                "audio",
            )
        except Exception as e:
            print(f"Audio generation failed, returning text directly: {str(e)}")
            chatbot[-1][1] = bot_response
        yield chatbot


# Function to switch to voice mode
def toggle_voice_mode():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
    )


# Function to switch back to text mode
def toggle_text_mode():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


examples = [
    {"text": "Hello, please introduce yourself", "files": []},
    {"text": "Please generate an image of Tai Chi", "files": []},
    {"text": "Can you help me search for information about traditional Chinese medicine?", "files": []},
    {"text": "Please generate a PPT about diabetes, including causes, symptoms, treatment drugs and preventive measures", "files": []},
    {"text": "Please generate a Word document about health recipes", "files": []},
    {"text": "Please generate a Tai Chi video", "files": []},
    {"text": "Based on the knowledge base, what is sub-health?", "files": []},
]


# Build Gradio interface
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as demo:
    # Title and description
    gr.Markdown("# Dr.Byte🧑‍⚕️")

    # Create chat layout
    with gr.Row():
        with gr.Column(scale=10):
            chatbot = gr.Chatbot(
                height=600,
                avatar_images=AVATAR,
                show_copy_button=True,
                latex_delimiters=[
                    {"left": "\\(", "right": "\\)", "display": True},
                    {"left": "\\[", "right": "\\]", "display": True},
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$", "right": "$", "display": True},
                ],
                placeholder="\n## Welcome to talk to me \n",
            )
            # Add image display component

    with gr.Row():
        with gr.Column(scale=9):
            chat_input = gr.MultimodalTextbox(
                interactive=True,
                file_count="multiple",
                placeholder="Enter message or upload files...",
                show_label=False,
            )
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                label="Voice Input",
                visible=False,
                type="filepath",
            )
        with gr.Column(scale=1):
            clear = gr.ClearButton([chatbot, chat_input, audio_input], value="Clear Record")
            toggle_voice_button = gr.Button("Voice Conversation Mode", visible=True)
            toggle_text_button = gr.Button("Text Conversation Mode", visible=False)
            submit_audio_button = gr.Button("Send", visible=False)

    with gr.Row() as example_row:
        example_component = gr.Examples(
            examples=examples, inputs=chat_input, visible=True, examples_per_page=15
        )

    chat_input.submit(
        fn=grodio_view, 
        inputs=[chatbot, chat_input], 
        outputs=[chatbot, chat_input]
    )
    # Toggle button click events
    toggle_voice_button.click(
        fn=toggle_voice_mode,
        inputs=None,
        outputs=[
            chat_input,
            audio_input,
            toggle_voice_button,
            toggle_text_button,
            submit_audio_button,
        ],
    )

    toggle_text_button.click(
        fn=toggle_text_mode,
        inputs=None,
        outputs=[
            chat_input,
            audio_input,
            toggle_voice_button,
            toggle_text_button,
            submit_audio_button,
        ],
    )

    submit_audio_button.click(
        fn=gradio_audio_view, inputs=[chatbot, audio_input], outputs=[chatbot]
    )


# Start application
def start_gradio():
    demo.launch(server_port=10035, share=False)


if __name__ == "__main__":
    start_gradio()
