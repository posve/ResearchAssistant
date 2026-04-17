import unittest
from unittest.mock import MagicMock
import sys

# Mocking dependencies that are not installed in the environment
mock_hf = MagicMock()
sys.modules['huggingface_hub'] = mock_hf

mock_llama = MagicMock()
sys.modules['llama_cpp'] = mock_llama

from llm import LLMManager

class TestLLMManager(unittest.TestCase):
    def test_ask_without_load_model_raises_runtime_error(self):
        """Test that LLMManager.ask() raises RuntimeError if the model is not loaded."""
        manager = LLMManager()

        # Define some dummy context
        contexts = [
            {"filename": "source1.pdf", "text": "This is some context text."}
        ]

        # Assert that RuntimeError is raised with the expected message
        with self.assertRaises(RuntimeError) as cm:
            manager.ask("What is the context?", contexts)

        self.assertEqual(str(cm.exception), "Model is not loaded. Call load_model() first.")

if __name__ == '__main__':
    unittest.main()
