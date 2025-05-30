'''Encapsulate functions for calling large model proxy API interface'''
from typing import List, Dict

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai import Stream

from core.client.LLMclientbase import LLMclientbase
from overrides import override


# Instantiation function
class LLMclientgeneric(LLMclientbase):

    def __init__(self, *args, **krgs):
        super().__init__()

    # This function only handles single-turn dialogue, no streaming output, no history input
    @override
    def chat_with_ai(self, prompt: str) -> str | None:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    # This function supports streaming output and can input history, is the main functional function
    @override
    def chat_with_ai_stream(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.construct_message(prompt, history if history else []),
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
            stream=True,
        )
        return response

    # This function is used to construct messages, for prompt engineering
    @override
    def construct_message(
        self, prompt: str, history: List[List[str]] | None = None
    ) -> List[Dict[str, str]] | str | None:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant who enjoys answering various questions. Your task is to provide professional, accurate, and insightful answers to users.",
            }
        ]

        for user_input, ai_response in history:
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": ai_response.__repr__()})

        messages.append({"role": "user", "content": prompt})
        return messages

    # This function is used for direct message input dialogue, used in ppt/word generation
    @override
    def chat_using_messages(self, messages: List[Dict]) -> str | None:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            top_p=0.7,
            temperature=0.95,
            max_tokens=1024,
        )

        return response.choices[0].message.content
