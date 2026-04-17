from huggingface_hub import hf_hub_download
from llama_cpp import Llama

class LLMManager:
    def __init__(self, model_repo="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF", model_file="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"):
        self.model_repo = model_repo
        self.model_file = model_file
        self.llm = None
        self.system_prompt = """You are a helpful research assistant. Answer the user's question ONLY using the context provided below. If the answer is not in the context, say "I don't know based on the provided documents." Always cite the filename of the context you used."""

    def load_model(self, progress_callback=None):
        """Downloads the model if it doesn't exist locally, then loads it."""
        if progress_callback:
            progress_callback("Checking for local LLM model...")
            
        model_path = hf_hub_download(
            repo_id=self.model_repo, 
            filename=self.model_file, 
            cache_dir="./models"
        )
        
        if progress_callback:
            progress_callback(f"Loading model into memory...")
            
        # Load the model with llama.cpp
        # Using a small context window (2048) and offloading to CPU for maximum compatibility
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            verbose=False
        )
        
        if progress_callback:
            progress_callback("LLM Ready!")
            
        return True

    def ask(self, question, contexts):
        """Builds a prompt from the retrieved contexts and streams the response."""
        if not self.llm:
            raise RuntimeError("Model is not loaded. Call load_model() first.")
            
        # Combine the context chunks
        context_str = ""
        for i, ctx in enumerate(contexts):
            context_str += f"[Source {i+1}: {ctx['filename']}]\n{ctx['text']}\n\n"
            
        # Format for TinyLlama Chat template
        prompt = f"""<|system|>
{self.system_prompt}
Context:
{context_str}</s>
<|user|>
{question}</s>
<|assistant|>
"""
        
        # Generate the response
        output = self.llm(
            prompt,
            max_tokens=512,
            stop=["</s>", "<|user|>"],
            echo=False,
            temperature=0.3
        )
        
        return output['choices'][0]['text'].strip()