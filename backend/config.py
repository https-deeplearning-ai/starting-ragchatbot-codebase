import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings (via AWS Bedrock)
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")
    AWS_PROFILE: str = os.getenv("AWS_PROFILE", "")
    
    # Embedding model settings
    EMBEDDING_MODEL: str = os.getenv("EMBED_MODEL", "")
    
    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

config = Config()


