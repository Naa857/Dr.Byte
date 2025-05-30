'''Select corresponding tool function for processing based on Q&A type'''
from typing import Tuple, List, Any

from core.qa.function_tool import map_question_to_function

from core.qa.purpose_type import userPurposeType


def get_answer(
    question: str, history: List[List | None] = None, question_type=None, image_url=None
) -> Tuple[Any, userPurposeType]:
    """
    Call corresponding function to get result based on question type
    """

    function = map_question_to_function(question_type)

    args = [question_type, question, history, image_url]
    result = function(*args)

    return result
