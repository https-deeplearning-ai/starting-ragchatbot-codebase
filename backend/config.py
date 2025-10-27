import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration settings for the RAG system"""

    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    # Embedding model settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Document processing settings
    CHUNK_SIZE: int = 800  # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100  # Characters to overlap between chunks
    MAX_RESULTS: int = 5  # Maximum search results to return
    MAX_HISTORY: int = 2  # Number of conversation messages to remember

    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

    # Startup performance settings
    LAZY_LOADING: bool = os.getenv("LAZY_LOADING", "true").lower() == "true"  # Enable lazy loading
    BACKGROUND_DOCUMENT_PROCESSING: bool = os.getenv("BACKGROUND_DOCUMENT_PROCESSING", "true").lower() == "true"
    PRELOAD_COMPONENTS: bool = os.getenv("PRELOAD_COMPONENTS", "false").lower() == "true"  # Pre-load all components
    QUICK_START: bool = os.getenv("QUICK_START", "false").lower() == "true"  # Skip document processing entirely


config = Config()
