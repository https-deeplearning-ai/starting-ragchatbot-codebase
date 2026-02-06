"""Configuration diagnostics tests"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import config


class TestConfigurationDiagnostics:
    """Tests to diagnose configuration-related issues"""

    def test_api_key_is_set(self):
        """Verify API key is configured"""
        if not config.ANTHROPIC_API_KEY:
            pytest.fail(
                "ANTHROPIC_API_KEY is not set. "
                "Please create a .env file with ANTHROPIC_API_KEY=your-key"
            )

    def test_api_key_not_placeholder(self):
        """Verify API key is not a placeholder value"""
        if config.ANTHROPIC_API_KEY in ["", "your-key", "sk-xxx", "test-key"]:
            pytest.fail(
                f"ANTHROPIC_API_KEY appears to be a placeholder: '{config.ANTHROPIC_API_KEY}'. "
                "Please set a valid API key."
            )

    def test_model_name_is_set(self):
        """Verify model name is configured"""
        assert config.ANTHROPIC_MODEL, "ANTHROPIC_MODEL should be set"
        assert len(config.ANTHROPIC_MODEL) > 0, "ANTHROPIC_MODEL should not be empty"

    def test_chroma_path_exists_or_can_be_created(self):
        """Verify ChromaDB path is valid"""
        chroma_path = config.CHROMA_PATH

        # Check if it's an absolute path or relative
        if not os.path.isabs(chroma_path):
            # Convert to absolute path relative to backend directory
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        # Check if directory exists or parent directory is writable
        if os.path.exists(chroma_path):
            assert os.path.isdir(chroma_path), f"CHROMA_PATH exists but is not a directory: {chroma_path}"
        else:
            parent_dir = os.path.dirname(chroma_path)
            if parent_dir and not os.path.exists(parent_dir):
                pytest.skip(f"Parent directory for CHROMA_PATH doesn't exist: {parent_dir}")

    def test_embedding_model_is_set(self):
        """Verify embedding model is configured"""
        assert config.EMBEDDING_MODEL, "EMBEDDING_MODEL should be set"
        assert config.EMBEDDING_MODEL == "all-MiniLM-L6-v2", \
            f"Expected embedding model 'all-MiniLM-L6-v2', got '{config.EMBEDDING_MODEL}'"

    def test_chunk_settings_are_valid(self):
        """Verify chunk settings are reasonable"""
        assert config.CHUNK_SIZE > 0, "CHUNK_SIZE should be positive"
        assert config.CHUNK_OVERLAP >= 0, "CHUNK_OVERLAP should be non-negative"
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE, \
            "CHUNK_OVERLAP should be less than CHUNK_SIZE"

    def test_max_results_is_valid(self):
        """Verify max results setting is reasonable"""
        assert config.MAX_RESULTS > 0, "MAX_RESULTS should be positive"
        assert config.MAX_RESULTS <= 100, "MAX_RESULTS seems too high (>100)"

    def test_max_history_is_valid(self):
        """Verify max history setting is reasonable"""
        assert config.MAX_HISTORY >= 0, "MAX_HISTORY should be non-negative"


class TestChromaDBConnectivity:
    """Test ChromaDB connectivity"""

    def test_chromadb_can_be_initialized(self):
        """Test that ChromaDB can be initialized with config settings"""
        try:
            import chromadb
            from chromadb.config import Settings

            # Use a temporary test path
            test_path = "/tmp/test_chroma_db_connectivity"

            client = chromadb.PersistentClient(
                path=test_path,
                settings=Settings(anonymized_telemetry=False)
            )

            # Try to create a collection
            collection = client.get_or_create_collection(name="test_collection")
            assert collection is not None

            # Cleanup
            client.delete_collection("test_collection")

        except Exception as e:
            pytest.fail(f"Failed to initialize ChromaDB: {e}")


class TestEmbeddingModel:
    """Test embedding model availability"""

    def test_embedding_model_can_load(self):
        """Test that the configured embedding model can be loaded"""
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(config.EMBEDDING_MODEL)

            # Test a simple embedding
            embedding = model.encode("test sentence")

            assert embedding is not None
            assert len(embedding) > 0

        except Exception as e:
            pytest.fail(f"Failed to load embedding model '{config.EMBEDDING_MODEL}': {e}")
