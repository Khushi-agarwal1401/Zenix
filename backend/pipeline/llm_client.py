import os

class LLMClient:
    """
    A client for running the local lightweight LLM (Flan-T5).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.generator = None
        print("Initializing LLMClient to use local model.")
        self._load_local_model()

    def _load_local_model(self):
        if self.generator is not None:
            return
        try:
            print("Loading local LLM (google/flan-t5-base)...")
            from transformers import pipeline
            device = -1 
            self.generator = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                max_length=512,
                device=device
            )
            print("Local LLM loaded successfully.")
        except Exception as e:
            print(f"Failed to load local LLM: {e}")

    def generate(self, prompt: str) -> str:
        """
        Generates text based on the prompt using the local Flan-T5 model.
        """
        try:
            if self.generator is None:
                self._load_local_model()
            if self.generator is not None:
                results = self.generator(prompt)
                if results and len(results) > 0:
                    return results[0]['generated_text']
            return ""
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return ""
