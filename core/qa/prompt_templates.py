from core.qa.purpose_type import purpose_map

purpose_type_template = (
    f"You are a text classification tool assistant with {len(purpose_map)} categories: "
    f"Text Generation, Image Generation, Video Generation, Audio Generation, Image Description, Greeting, PPT Generation, Word Generation, Internet Search, Knowledge Base Based, Knowledge Graph Based, Other. "
    f"Here are some examples to help you classify: "
    f"'I want to learn about diabetes', classification result is Text Generation; "
    f"'Please generate an image of elderly people practicing Tai Chi', classification result is Image Generation; "
    f"'Can you generate a video about spring?', classification result is Video Generation; "
    f"'Please convert the above text to speech', classification result is Audio Generation; "
    f"'How to treat diabetes? Please answer in voice', classification result is Audio Generation; "
    f"'Please describe this beautiful image', classification result is Image Description; "
    f"'Hello! Who are you?', classification result is Greeting; "
    f"'Please create a PPT about diabetes', classification result is PPT Generation; "
    f"'Please create a Word report about diabetes', classification result is Word Generation; "
    f"'Please find health and wellness related knowledge on the internet', classification result is Internet Search; "
    f"'What diabetes-related knowledge is in the knowledge base?', classification result is Knowledge Base Based; "
    f"'What diabetes-related knowledge is in the knowledge graph?', classification result is Knowledge Graph Based; "
    f"'I have diabetes, help me create a diet and exercise plan', classification result is Text Generation; "
    f"If the content doesn't match any of the above categories, the classification result is Other. "
    f"Please refer to the examples above and directly give one classification result, no explanation, no extra content, no extra symbols, no extra spaces, no extra blank lines, no extra line breaks, no extra punctuation. "
    f"Please classify the following content: "
)


def get_question_parser_prompt(text: str) -> str:
    """
    Generate prompt based on input text
    :param text: Input text
    :return: prompt
    """
    return f"{purpose_type_template} {text}"
