from setuptools import setup, find_packages

setup(
    name="dr.byte",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "gradio",
        "PyPDF2",
        "python-docx",
        "pydub",
        "SpeechRecognition",
        "opencc-python-reimplemented",
        "icecream",
    ],
) 