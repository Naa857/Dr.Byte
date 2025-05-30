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
    audio = AudioSegment.from_file(audio_file_path)  # 自动识别格式
    wav_file_path = audio_file_path.rsplit(".", 1)[0] + ".wav"  # 生成 WAV 文件路径
    audio.export(wav_file_path, format="wav")  # 将音频文件导出为 WAV 格式
    return wav_file_path


def audio_to_text(audio_file_path):
    # 创建识别器对象
    # 如果不是 WAV 格式，先转换为 WAV
    if not audio_file_path.endswith(".wav"):
        audio_file_path = convert_audio_to_wav(audio_file_path)

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        # 使用 Google Web Speech API 进行语音识别，不用下载模型但对网络要求高
        # text = recognizer.recognize_google(audio_data, language="zh-CN")
        # 使用 whisper 进行语音识别，自动下载模型到本地
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

    # 使用检测到的编码来读取文件
    with open(text_file, "r", encoding=encoding) as file:
        return file.read()


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


# 核心函数
def grodio_view(chatbot, chat_input):
    # 用户消息立即显示
    user_message = chat_input["text"]
    bot_response = "loading..."
    chatbot.append([user_message, bot_response])
    yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理用户上传的文件
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

    # 图片文件解析
    if images != []:
        image_url = images
        image_base64 = [image_to_base64(image) for image in image_url]

        for i, image in enumerate(image_base64):
            chatbot[-1][
                0
            ] += f"""
                <div>
                    <img src="data:image/png;base64,{image}" alt="Generated Image" style="max-width: 100%; height: auto; cursor: pointer;" />
                </div>
                """
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")
    else:
        image_url = None

    question_type = parse_question(user_message, image_url)
    ic(question_type)

    # 音频文件解析
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

    # 处理文本生成/其他/文档检索/知识图谱检索
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        # 流式输出
        try:
            for chunk in answer[0]:
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ""
                    bot_response = bot_response + (content or "")
                    chatbot[-1][1] = bot_response
                    yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")
                else:
                    print("Warning: Received empty chunk or invalid chunk format")
                    continue
        except Exception as e:
            print(f"Error processing stream: {str(e)}")
            chatbot[-1][1] = "Sorry, an error occurred while processing the response, please try again later"
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理图片生成
    if answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        describe = process_image_describe_tool(
            question_type=userPurposeType.ImageDescribe,
            question="Describe this image, do not recognize 'AI generated'",
            history="",
            image_url=[image_url],
        )
        combined_message = f"""
            **Generated Image:**
            <img src="{image_url}" alt="Generated Image" style="max-width: 100%; height: auto; cursor: pointer;" />
            {describe[0]}
            """
        chatbot[-1][1] = combined_message
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理图片描述
    if answer[1] == userPurposeType.ImageDescribe:
        for i in range(0, len(answer[0]), 1):
            bot_response += answer[0][i : i + 1]  # 累加当前chunk到combined_message
            chatbot[-1][1] = bot_response  # 更新chatbot对话中的最后一条消息
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")  # 实时输出当前累积的对话内容

    # 处理视频
    if answer[1] == userPurposeType.Video:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, video generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理PPT
    if answer[1] == userPurposeType.PPT:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, PPT generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理Docx
    if answer[1] == userPurposeType.Docx:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, document generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理音频生成
    if answer[1] == userPurposeType.Audio:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
        else:
            chatbot[-1][1] = "Sorry, audio generation failed, please try again later"
        yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")

    # 处理联网搜索
    if answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            output_message = (
                "Due to network issues, access to the internet failed. Below is my response based on existing knowledge:"
            )
        else:
            # 将字典中的内容转换为 Markdown 格式的链接
            links = "\n".join(f"[{title}]({link})" for link, title in answer[2].items())
            links += "\n"
            output_message = f"Reference materials: {links}"
        for i in range(0, len(output_message)):
            bot_response = output_message[: i + 1]
            chatbot[-1][1] = bot_response
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")
        for chunk in answer[0]:
            bot_response = bot_response + (chunk.choices[0].delta.content or "")
            chatbot[-1][1] = bot_response
            yield chatbot, gr.MultimodalTextbox(value="", file_count="multiple")


def gradio_audio_view(chatbot, audio_input):

    # 用户消息立即显示
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
    elif "作曲 作曲" in audio_message:
        user_message += "Please modify and output the following sentence without additional text, sentence: 'Sorry, I cannot understand music'"
    else:
        user_message += audio_message

    if user_message == "":
        user_message = "Please modify and output the following sentence without additional text, sentence: 'What would you like to know? I will do my best to help you'"

    question_type = parse_question(user_message)
    ic(question_type)
    answer = get_answer(user_message, chatbot, question_type)
    bot_response = ""

    # 处理文本生成/其他/文档检索/知识图谱检索
    if (
        answer[1] == userPurposeType.text
        or answer[1] == userPurposeType.RAG
        or answer[1] == userPurposeType.KnowledgeGraph
    ):
        # 语音输出
        try:
            bot_response = ""  # 确保初始化为空字符串
            for chunk in answer[0]:
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, 'content') else ""
                    if content is not None:  # 确保内容不是 None
                        bot_response = bot_response + str(content)  # 使用 str() 确保转换为字符串
                else:
                    print("Warning: Received empty chunk or invalid chunk format")
                    continue

            if not bot_response:  # 如果 bot_response 为空
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

    # 处理图片生成
    if answer[1] == userPurposeType.ImageGeneration:
        image_url = answer[0]
        describe = process_image_describe_tool(
            question_type=userPurposeType.ImageDescribe,
            question="Describe this image, do not recognize 'AI generated'",
            history=" ",
            image_url=[image_url],
        )
        combined_message = f"""
            **Generated Image:**
            <img src="{image_url}" alt="Generated Image" style="max-width: 100%; height: auto; cursor: pointer;" />
            {describe[0]}
            """
        chatbot[-1][1] = combined_message
        yield chatbot

    # 处理视频
    if answer[1] == userPurposeType.Video:
        if answer[0] is not None:
            chatbot[-1][1] = answer[0]
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

    # 处理PPT
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

    # 处理Docx
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

    # 处理音频生成
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

    # 处理联网搜索
    if answer[1] == userPurposeType.InternetSearch:
        if answer[3] == False:
            bot_response = (
                "Due to network issues, access to the internet failed. Below is my response based on existing knowledge:"
            )
        # 语音输出
        for chunk in answer[0]:
            # 获取每个块的数据
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


# 切换到语音模式的函数
def toggle_voice_mode():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
    )


# 切换回文本模式的函数
def toggle_text_mode():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


examples = [
    {"text": "你好，請介紹一下自己", "files": []},
    {"text": "What are the common symptoms of diabetes?", "files": []},
    {"text": "請幫我生成一張太極拳的圖片", "files": []},
    {"text": "Can you help me search for information about traditional Chinese medicine?", "files": []},
    {"text": "請幫我生成一份關於糖尿病的PPT，包含發病原因、症狀、治療藥物和預防措施", "files": []},
    {"text": "What foods are suitable for diabetic patients?", "files": []},
    {"text": "請幫我生成一份養生食譜的Word文檔", "files": []},
    {"text": "Can you analyze my medical report?", "files": []},
    {"text": "請幫我生成一個太極拳的視頻", "files": []},
    {"text": "What are the benefits of practicing Tai Chi?", "files": []},
    {"text": "請幫我生成一份關於中醫養生的PPT", "files": []},
    {"text": "Can you generate a Word document about healthy diet?", "files": []},
]


# 构建 Gradio 界面
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as demo:
    # 标题和描述
    gr.Markdown("# Dr.Byte🧑‍⚕️")

    # 创建聊天布局
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
                placeholder="\n## Welcome to talk to me \n————This project is open source, https://github.com/Warma10032/cyber-doctor",
            )

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
    # 切换按钮点击事件
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


# 启动应用
def start_gradio():
    demo.launch(server_port=10035, share=False)


if __name__ == "__main__":
    start_gradio()
