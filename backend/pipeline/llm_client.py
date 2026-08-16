import os
import json
import urllib.request
import urllib.error

def _load_env():
    """Helper to load .env variables from project root if not already in environment."""
    for path in [".env", "../.env", "../../.env", os.path.join(os.path.dirname(__file__), "../../.env")]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            os.environ.setdefault(key.strip(), val.strip())
                break
            except Exception as e:
                print(f"Error loading {path}: {e}")

class LLMClient:
    """
    A client for running external LLMs (e.g., Claude, OpenAI, custom API gateways)
    with fallback to a local lightweight LLM (Flan-T5).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        _load_env()
        self.api_key = os.getenv("API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("MODEL") or os.getenv("MODEL_NAME")
        self.base_url = os.getenv("BASE_URL") or os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
        self.generator = None

        if self.api_key and self.model:
            print(f"Configured external LLM model: {self.model} with API key starting with {self.api_key[:6]}...")
            print("Skipping immediate load of local fallback model for faster startup.")
        else:
            print("No external model/key configured in .env. Will load local model.")
            self._load_local_model()

    def _load_local_model(self):
        if self.generator is not None:
            return
        try:
            print("Loading local fallback LLM (google/flan-t5-base)...")
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

    def _generate_via_api(self, prompt: str) -> str:
        """Attempts to generate text using the configured API (Anthropic or OpenAI compatible)."""
        # 1. Try Anthropic Python SDK if installed and model looks like Claude
        if "claude" in str(self.model).lower():
            try:
                import anthropic
                client_kwargs = {"api_key": self.api_key}
                if os.getenv("BASE_URL") or os.getenv("ANTHROPIC_BASE_URL"):
                    client_kwargs["base_url"] = self.base_url
                client = anthropic.Anthropic(**client_kwargs)
                response = client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                if response.content and len(response.content) > 0:
                    return response.content[0].text
            except ImportError:
                pass # Fallback to direct HTTP request
            except Exception as e:
                print(f"Anthropic SDK call failed: {e}. Trying direct HTTP request...")

        # 2. Try direct HTTP request to Anthropic /v1/messages endpoint
        try:
            url = self.base_url.rstrip("/")
            if not url.endswith("/v1/messages") and not url.endswith("/v1/chat/completions"):
                if "claude" in str(self.model).lower():
                    url += "/v1/messages"
                else:
                    url += "/v1/chat/completions"

            headers = {
                "Content-Type": "application/json"
            }
            if "messages" in url or "claude" in str(self.model).lower():
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
                payload = {
                    "model": self.model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}]
                }
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                }

            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if "content" in resp_data and isinstance(resp_data["content"], list):
                    return resp_data["content"][0].get("text", "")
                elif "choices" in resp_data and isinstance(resp_data["choices"], list):
                    return resp_data["choices"][0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"Direct API HTTP request failed: {e}")

        return ""

    def generate(self, prompt: str) -> str:
        """
        Generates text based on the prompt. Uses external API if configured,
        falling back to local Flan-T5 model only if no API key is set.
        """
        if self.api_key and self.model:
            api_res = self._generate_via_api(prompt)
            if api_res and api_res.strip():
                return api_res.strip()
            # API key configured but call failed (e.g. 401) — return helpful message
            # instead of hanging waiting for the local model to download/load
            return (
                "⚠️ API Error: The configured API key returned an error (likely 401 Unauthorized). "
                "Please check your API key in the `.env` file. "
                "Zenix needs a valid Anthropic API key (format: sk-ant-api03-...) to respond."
            )

        # No API key configured — use local model
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

