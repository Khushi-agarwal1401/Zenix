from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import threading
import uuid
import json
import logging

app = FastAPI()

# ── Pipeline state ────────────────────────────────────────────────────────────
rag_engine = None
task_router = None
verification_layer = None
_pipeline_lock = threading.Lock()
_pipeline_ready = False

def _init_pipeline_sync():
    """Synchronously initialize the heavy pipeline (runs in background thread)."""
    global rag_engine, task_router, verification_layer, _pipeline_ready
    with _pipeline_lock:
        if _pipeline_ready:
            return
        print("Background: Initializing RAG Engine and Pipeline...")
        try:
            from rag_engine import RAGEngine
            from pipeline.router import TaskRouter
            from pipeline.verification import VerificationLayer
            rag_engine = RAGEngine()
            task_router = TaskRouter(rag_engine)
            verification_layer = VerificationLayer()
            _pipeline_ready = True
            print("Background: Pipeline initialized successfully.")
        except Exception as e:
            print(f"Background: Failed to initialize pipeline: {e}")

@app.on_event("startup")
async def startup_event():
    """Pre-warm the pipeline in a background thread so the first request is fast."""
    t = threading.Thread(target=_init_pipeline_sync, daemon=True)
    t.start()

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    persona: str

class FeedbackRequest(BaseModel):
    request_id: str
    feedback: str  # "up" or "down"

# ── Logging ───────────────────────────────────────────────────────────────────
def log_interaction(query: str, retrieved_results: list, persona: str, request_id: str):
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "query": query,
            "persona": persona,
            "retrieved_context": [r['content'] for r in retrieved_results] if retrieved_results else []
        }
        with open("data/training_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to log interaction: {e}")

# ── Direct LLM fallback (fast path when pipeline not ready) ───────────────────
def _direct_llm_response(message: str, persona: str) -> str:
    """Call LLMClient directly, bypassing the heavy RAG pipeline."""
    try:
        from pipeline.llm_client import LLMClient
        client = LLMClient()
        persona_prefix = (
            "You are Zenix, a friendly Indian AI assistant. Respond in a warm, desi style. "
            if persona == "desi"
            else "You are Zenix, a formal and professional Indian AI assistant. "
        )
        prompt = f"{persona_prefix}\nUser: {message}\nZenix:"
        response = client.generate(prompt)
        return response if response and response.strip() else "Main abhi taiyaar ho raha hoon, thoda intezaar karo! (System warming up…)"
    except Exception as e:
        print(f"Direct LLM error: {e}")
        return "System is warming up. Please try again in a moment."

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    try:
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "feedback": request.feedback
        }
        with open("data/feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
        return {"status": "success"}
    except Exception as e:
        print(f"Failed to log feedback: {e}")
        return {"status": "error"}

@app.get("/status")
async def status_endpoint():
    return {"pipeline_ready": _pipeline_ready, "status": "ok"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    request_id = str(uuid.uuid4())
    message = request.message
    persona = request.persona

    context = {
        "request_id": request_id,
        "persona": persona,
        "metadata": {}
    }

    # Fast path: if pipeline not ready yet, use direct LLM call
    if not _pipeline_ready:
        print(f"Pipeline not ready — using direct LLM for: {message[:60]}")
        response_text = await asyncio.get_event_loop().run_in_executor(
            None, _direct_llm_response, message, persona
        )
        return {"response": response_text, "request_id": request_id}

    try:
        # Full pipeline path
        result = await task_router.route_and_process(message, context)
        final_result = await verification_layer.process(result, context)

        retrieved_results = context.get("retrieved_results", [])
        log_interaction(
            query=message,
            retrieved_results=retrieved_results,
            persona=persona,
            request_id=request_id
        )

        return {"response": final_result.get("response", "Error generating response"), "request_id": request_id}

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        # Fallback to direct LLM on pipeline error
        response_text = await asyncio.get_event_loop().run_in_executor(
            None, _direct_llm_response, message, persona
        )
        return {"response": response_text, "request_id": request_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
