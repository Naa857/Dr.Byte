'''Interface for constructing different large model proxies externally, returns a large model proxy after construction'''
from core.client.ourAPI.client import OurAPI
from core.client.zhipuAPI.client import Image_generate_client, Image_describe_client
from core.client.zhipuAPI.client import Video_generate_client
from env import get_env_value
from core.qa.purpose_type import userPurposeType


class Clientfactory:
    # Initialize client dictionary using LLM_BASE_URL from environment variables
    map_client_dict = {get_env_value("LLM_BASE_URL")}

    # Initialize client url and apikey using LLM_BASE_URL and LLM_API_KEY from environment variables
    def __init__(self):
        self._client_url = get_env_value("LLM_BASE_URL")
        self._api_key = get_env_value("LLM_API_KEY")

    def get_client(self):
        """
        Get default client instance
        """
        return OurAPI()  # Return our own API client instance

    @staticmethod
    def get_special_client(client_type: str):
        """
        Get specific client instance based on client type
        :param client_type: Client type, string type
        :return: Corresponding client instance
        """
        print("get_special_client")
        if client_type == userPurposeType.ImageGeneration:
            return Image_generate_client
        if client_type == userPurposeType.ImageDescribe:
            return Image_describe_client
        if client_type == userPurposeType.Video:
            return Video_generate_client

        # Use text generation model by default
        return OurAPI()
