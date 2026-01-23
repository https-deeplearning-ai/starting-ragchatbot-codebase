"""Tests to validate configuration settings and catch misconfigurations"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import config


class TestConfigValidation:
    """Test that configuration values are valid"""

    def test_max_results_is_positive(self):
        """CRITICAL: MAX_RESULTS must be > 0 for search to work

        This test will FAIL with current config (MAX_RESULTS=0).
        The bug is in config.py line 21.
        """
        assert config.MAX_RESULTS > 0, (
            f"BUG FOUND: MAX_RESULTS is {config.MAX_RESULTS}, but must be > 0. "
            "Setting MAX_RESULTS=0 causes all searches to return empty results! "
            "Fix: Change MAX_RESULTS: int = 0 to MAX_RESULTS: int = 5 in config.py"
        )

    def test_max_results_is_reasonable(self):
        """MAX_RESULTS should be a reasonable value (1-20)"""
        assert (
            1 <= config.MAX_RESULTS <= 20
        ), f"MAX_RESULTS={config.MAX_RESULTS} is outside reasonable range 1-20"

    def test_chunk_size_is_positive(self):
        """CHUNK_SIZE must be > 0"""
        assert config.CHUNK_SIZE > 0, "CHUNK_SIZE must be positive"

    def test_chunk_overlap_less_than_size(self):
        """CHUNK_OVERLAP must be less than CHUNK_SIZE"""
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE, (
            f"CHUNK_OVERLAP ({config.CHUNK_OVERLAP}) must be less than "
            f"CHUNK_SIZE ({config.CHUNK_SIZE})"
        )

    def test_anthropic_api_key_is_string(self):
        """ANTHROPIC_API_KEY should be a string"""
        assert isinstance(config.ANTHROPIC_API_KEY, str)

    def test_chroma_path_is_set(self):
        """CHROMA_PATH must be set"""
        assert config.CHROMA_PATH, "CHROMA_PATH must be set"
        assert len(config.CHROMA_PATH) > 0


class TestConfigDefaults:
    """Test that default values match expected values"""

    def test_default_max_results_should_be_5(self):
        """The expected default for MAX_RESULTS is 5

        This test documents the expected value and will FAIL
        because the current default is incorrectly set to 0.
        """
        expected = 5
        assert config.MAX_RESULTS == expected, (
            f"MAX_RESULTS should default to {expected}, got {config.MAX_RESULTS}. "
            "Fix config.py line 21: change 'MAX_RESULTS: int = 0' to 'MAX_RESULTS: int = 5'"
        )

    def test_default_chunk_size(self):
        """CHUNK_SIZE should default to 800"""
        assert config.CHUNK_SIZE == 800

    def test_default_chunk_overlap(self):
        """CHUNK_OVERLAP should default to 100"""
        assert config.CHUNK_OVERLAP == 100
