import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Search backend/ directory first, then project root
_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent

if (_backend_dir / ".env").exists():
    load_dotenv(_backend_dir / ".env")
elif (_project_root / ".env").exists():
    load_dotenv(_project_root / ".env")
else:
    load_dotenv()

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    
    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

config = Config()

if not config.ANTHROPIC_API_KEY:
    print("\n" + "=" * 60)
    print("WARNING: ANTHROPIC_API_KEY is not set!")
    print("The /api/query endpoint will fail.")
    print("Please create a .env file with your API key.")
    print("See .env.example for the expected format.")
    print("=" * 60 + "\n")
