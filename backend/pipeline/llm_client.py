import os
import json
import urllib.request
import urllib.error


class LLMClient:
    """
    LLM Client supporting multiple backends:
    1. OpenAI-compatible API (preferred — requires OPENAI_API_KEY or LLM_API_KEY env var)
    2. Local Flan-T5 (fallback when no API key is set)

    Set LLM_BACKEND env var to force a backend:
      - "openai"  → use OpenAI-compatible API
      - "local"   → force local Flan-T5
      - unset     → auto-detect (API if key exists, else local)

    Set LLM_MODEL to override the default model name.
    Set LLM_API_BASE to override the API base URL (for local servers like Ollama, LM Studio, etc.).
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._api_client = None
        self._local_generator = None
        self._backend = None  # "openai" or "local"
        self._system_prompt = None

        # Determine backend preference
        backend_pref = os.environ.get("LLM_BACKEND", "").lower()
        has_api_key = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"))

        if backend_pref == "openai" or (not backend_pref and has_api_key):
            self._backend = "openai"
            self._init_openai_client()
        else:
            self._backend = "local"
            self._load_local_model()

    def _init_openai_client(self):
        """Initialize OpenAI-compatible API client (using urllib to avoid extra deps)."""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        base_url = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1").rstrip("/")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

        self._api_key = api_key
        self._api_base = base_url
        self._api_model = model

        print(f"LLMClient: Using OpenAI-compatible API ({base_url}) with model '{model}'")

    def _load_local_model(self):
        """Load local Flan-T5 as fallback."""
        if self._local_generator is not None:
            return
        try:
            model_name = os.environ.get("LLM_MODEL", "google/flan-t5-base")
            print(f"LLMClient: Loading local model ({model_name})...")
            from transformers import pipeline
            self._local_generator = pipeline(
                "text2text-generation",
                model=model_name,
                max_length=512,
                device=-1,
            )
            print("LLMClient: Local model loaded successfully.")
        except Exception as e:
            print(f"LLMClient: Failed to load local model: {e}")

    # ── System Prompt ─────────────────────────────────────────────────────────

    def set_system_prompt(self, prompt: str):
        """Set the system prompt used for all subsequent generate() calls."""
        self._system_prompt = prompt

    def get_system_prompt(self) -> str | None:
        return self._system_prompt

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text given a prompt.

        Args:
            prompt: The user message / instruction.
            system_prompt: Override system prompt for this call.
            history: Optional conversation history [{"role": "user"|"assistant", "content": "..."}]
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
        """
        sys_prompt = system_prompt or self._system_prompt

        if self._backend == "openai":
            return self._generate_openai(prompt, sys_prompt, history, temperature, max_tokens)
        else:
            return self._generate_local(prompt, sys_prompt)

    # ── OpenAI-compatible API ─────────────────────────────────────────────────

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: str | None,
        history: list[dict] | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self._api_base}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": self._api_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return content.strip() if content else ""
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"LLMClient: API error {e.code}: {body[:300]}")
            # Fallback to local if available
            if self._local_generator:
                print("LLMClient: Falling back to local model.")
                return self._generate_local(prompt, system_prompt)
            return ""
        except Exception as e:
            print(f"LLMClient: API request failed: {e}")
            if self._local_generator:
                print("LLMClient: Falling back to local model.")
                return self._generate_local(prompt, system_prompt)
            return ""

    # ── Local Flan-T5 ────────────────────────────────────────────────────────

    def _generate_local(self, prompt: str, system_prompt: str | None) -> str:
        try:
            if self._local_generator is None:
                self._load_local_model()
            if self._local_generator is None:
                return ""

            # Prepend system prompt if available (Flan-T5 handles instruction prefixes well)
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"

            results = self._local_generator(full_prompt)
            if results and len(results) > 0:
                return results[0]["generated_text"].strip()
            return ""
        except Exception as e:
            print(f"LLMClient: Local generation error: {e}")
            return ""
