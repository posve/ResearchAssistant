import pytest
from unittest.mock import MagicMock
from llm import LLMManager

def test_ask_raises_error_if_model_not_loaded():
    manager = LLMManager()
    with pytest.raises(RuntimeError, match="Model is not loaded. Call load_model\\(\\) first."):
        manager.ask("What is the meaning of life?", [])

def test_ask_formats_prompt_and_calls_llm():
    manager = LLMManager()
    mock_llm = MagicMock()
    mock_llm.return_value = {
        'choices': [{'text': '  Mock response text.  '}]
    }
    manager.llm = mock_llm

    question = "What is the capital of France?"
    contexts = [
        {"filename": "doc1.txt", "text": "Paris is the capital of France."},
        {"filename": "doc2.txt", "text": "France is a country in Europe."}
    ]

    response = manager.ask(question, contexts)

    assert response == "Mock response text."

    # Check that the LLM was called with the correct prompt
    mock_llm.assert_called_once()
    args, kwargs = mock_llm.call_args
    prompt = args[0]

    # Verify parts of the prompt
    assert "You are a helpful research assistant." in prompt
    assert "[Source 1: doc1.txt]" in prompt
    assert "Paris is the capital of France." in prompt
    assert "[Source 2: doc2.txt]" in prompt
    assert "France is a country in Europe." in prompt
    assert "What is the capital of France?" in prompt
    assert prompt.endswith("<|user|>\nWhat is the capital of France?</s>\n<|assistant|>\n")

    # Check that kwargs are passed properly
    assert kwargs.get("max_tokens") == 512
    assert kwargs.get("stop") == ["</s>", "<|user|>"]
    assert kwargs.get("echo") is False
    assert kwargs.get("temperature") == 0.3

def test_ask_with_empty_contexts():
    manager = LLMManager()
    mock_llm = MagicMock()
    mock_llm.return_value = {
        'choices': [{'text': 'I don\'t know based on the provided documents.'}]
    }
    manager.llm = mock_llm

    question = "Who wrote Hamlet?"
    contexts = []

    response = manager.ask(question, contexts)

    assert response == "I don't know based on the provided documents."

    mock_llm.assert_called_once()
    args, kwargs = mock_llm.call_args
    prompt = args[0]

    # The context part should be empty, but prompt should still be formatted
    assert "Context:\n</s>" in prompt
    assert "<|user|>\nWho wrote Hamlet?</s>" in prompt
