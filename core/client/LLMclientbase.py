from env import get_env_value
from abc import abstractmethod

from openai import OpenAI
from openai import Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from typing import List, Dict


# Abstract class for constructing client
class LLMclientbase(object):
    def __init__(self):
        """
        Initialize LLM client base class
        """
        self.__client = OpenAI(
            api_key=get_env_value(
                "LLM_API_KEY"
            ),  # Initialize OpenAI client with API key from environment variables
            base_url=get_env_value(
                "LLM_BASE_URL"
            ),  # Initialize OpenAI client with base URL from environment variables
        )
        self.__model_name = get_env_value("MODEL_NAME")  # Use model name from environment variables

    @property
    def client(self):
        return self.__client

    @property
    def model_name(self):
        return self.__model_name

    # All abstract functions below
    @abstractmethod
    def chat_with_ai(self, prompt: str) -> str | None:
        """
        Chat with AI and return AI's response
        :param prompt: User input prompt
        :return: AI's response, may be None
        """
        raise NotImplementedError()

    @abstractmethod
    def chat_with_ai_stream(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        """
        Stream chat with AI and return streaming response
        :param prompt: User input prompt
        :param history: Chat history, defaults to None
        :return: Streaming chat completion or streaming chat chunk
        """
        raise NotImplementedError()

    @abstractmethod
    def construct_message(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> List[Dict[str, str]] | str | None:
        """
        Construct message for chatting with AI
        :param prompt: User input prompt
        :param history: Chat history, defaults to None
        :return: Constructed message list or string, may be None
        """
        raise NotImplementedError()

    @abstractmethod
    def chat_using_messages(self, messages: List[Dict]) -> str | None:
        """
        Chat with AI using message list and return AI's response
        :param messages: Message list
        :return: AI's response, may be None
        """
        raise NotImplementedError()
