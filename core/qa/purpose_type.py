from enum  import Enum

class userPurposeType(Enum):
    # Predefined possible question types based on user input text
    text = 0  # Unknown question
    Audio = 1   # Audio generation
    Video = 2   # Video generation
    ImageGeneration = 3 # Text to image
    ImageDescribe = 4 # Image to text
    RAG = 5  # Based on file description, with a vector database, for individual users, try to answer from vector database, may involve retrieval enhancement
    Hello = 6   # Greeting, gives specific output
    PPT=7      # PPT generation
    InternetSearch = 8 # Internet search
    Docx = 9   # Generate word file
    KnowledgeGraph = 10 # Knowledge graph based Q&A
 
  
purpose_map={
"Other":userPurposeType.text,
"Text Generation":userPurposeType.text,
"Audio Generation":userPurposeType.Audio,
"Video Generation":userPurposeType.Video,
"Image Description":userPurposeType.ImageDescribe,
"Image Generation":userPurposeType.ImageGeneration,
"Knowledge Base Based":userPurposeType.RAG,
"Greeting":userPurposeType.Hello,
"PPT Generation":userPurposeType.PPT,
"Word Generation":userPurposeType.Docx,
"Internet Search":userPurposeType.InternetSearch,
"Knowledge Graph Based":userPurposeType.KnowledgeGraph,
}

