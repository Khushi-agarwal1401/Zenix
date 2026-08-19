from fastapi import FastAPI, Request, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime
import asyncio
import threading
import uuid
import json
from typing import List, Dict, AsyncGenerator

from pipeline.cache import response_cache
from pipeline.rate_limiter import rate_limiter
from pipeline.session_store import session_store
from pipeline.input_guard import guard_input
from pipeline.logger import setup_logging, get_logger
from pipeline.summarizer import conversation_summarizer

app = FastAPI()

# ── Structured Logging ───────────────────────────────────────────────────────
log_level = "INFO"
setup_logging(level=log_level)
log = get_logger("api")

# ── Pipeline state ────────────────────────────────────────────────────────────
rag_engine = None
task_router = None
verification_layer = None
_pipeline_lock = threading.Lock()
_pipeline_ready = False

# ── Conversation History (delegated to session_store) ────────────────────────
MAX_HISTORY_MESSAGES = 20
# In-memory cache for fast access; session_store is the source of truth
conversation_cache: Dict[str, List[Dict[str, str]]] = {}


def _init_pipeline_sync():
    """Synchronously initialize the heavy pipeline (runs in background thread)."""
    global rag_engine, task_router, verification_layer, _pipeline_ready
    with _pipeline_lock:
        if _pipeline_ready:
            return
        log.info("Background: Initializing RAG Engine and Pipeline...")
        try:
            from rag_engine import RAGEngine
            from pipeline.router import TaskRouter
            from pipeline.verification import VerificationLayer
            rag_engine = RAGEngine()
            task_router = TaskRouter(rag_engine)
            verification_layer = VerificationLayer()
            _pipeline_ready = True
            log.info("Background: Pipeline initialized successfully.")
        except Exception as e:
            log.error(f"Background: Failed to initialize pipeline: {e}")


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
    session_id: str = ""  # Optional session ID for conversation continuity


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
            "retrieved_context": [r['content'] for r in retrieved_results] if retrieved_results else [],
        }
        import os
        os.makedirs("data", exist_ok=True)
        with open("data/training_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        log.info("Interaction logged", extra={"extra_data": {"request_id": request_id, "persona": persona}})
    except Exception as e:
        log.error(f"Failed to log interaction: {e}")


# ── Direct LLM fallback (fast path when pipeline not ready) ───────────────────
def _direct_llm_response(message: str, persona: str, history: List[Dict] = None) -> str:
    """Call LLMClient directly, bypassing the heavy RAG pipeline."""
    try:
        from pipeline.llm_client import LLMClient
        from pipeline.system_prompt import get_system_prompt

        client = LLMClient()
        system_prompt = get_system_prompt(persona)

        # Build chat history for the LLM
        chat_history = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    chat_history.append({"role": role, "content": content})

        response = client.generate(
            prompt=message,
            system_prompt=system_prompt,
            history=chat_history,
        )

        return response if response and response.strip() else (
            "Main abhi taiyaar ho raha hoon, thoda intezaar karo! (System warming up…)"
            if persona == "desi"
            else "System is warming up. Please try again in a moment."
        )
    except Exception as e:
        print(f"Direct LLM error: {e}")
        return "System is warming up. Please try again in a moment."


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    try:
        import os
        os.makedirs("data", exist_ok=True)
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "feedback": request.feedback,
        }
        with open("data/feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
        log.info(f"Feedback received: {request.feedback} for {request.request_id[:8]}")
        return {"status": "success"}
    except Exception as e:
        log.error(f"Failed to log feedback: {e}")
        return {"status": "error"}


@app.get("/status")
async def status_endpoint():
    return {
        "pipeline_ready": _pipeline_ready,
        "status": "ok",
        "cache": response_cache.stats(),
        "rate_limiter": rate_limiter.stats(),
    }


@app.post("/voice/transcribe")
async def voice_transcribe_endpoint(
    audio: UploadFile = File(...),
    language: str = Form("hi"),
):
    """Server-side STT endpoint — transcribes audio to text."""
    try:
        from pipeline.speech import speech_service

        audio_data = await audio.read()
        result = speech_service.transcribe_audio(
            audio_data,
            language=language,
            format=audio.filename.rsplit(".", 1)[-1] if audio.filename else "webm",
        )
        return result
    except ImportError:
        return JSONResponse(
            status_code=501,
            content={"error": "Speech recognition not installed. Install: pip install openai-whisper"},
        )
    except Exception as e:
        log.error(f"Voice transcribe error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Transcription failed: {str(e)}"},
        )


@app.post("/voice/synthesize")
async def voice_synthesize_endpoint(
    text: str = Form(...),
    language: str = Form("hi"),
):
    """Server-side TTS endpoint — converts text to speech audio."""
    try:
        from pipeline.speech import speech_service
        from fastapi.responses import Response

        result = speech_service.synthesize_speech(text, language=language)

        if result.get("error"):
            return JSONResponse(status_code=500, content={"error": result["error"]})

        media_type = f"audio/{result['format']}"
        return Response(
            content=result["audio_data"],
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="zenix_speech.{result["format"]}"',
            },
        )
    except ImportError:
        return JSONResponse(
            status_code=501,
            content={"error": "TTS not installed. Install: pip install gTTS pyttsx3"},
        )
    except Exception as e:
        log.error(f"Voice synthesize error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Synthesis failed: {str(e)}"},
        )


@app.get("/voice/languages")
async def voice_languages_endpoint():
    """Return supported speech languages."""
    from pipeline.speech import INDIAN_LANGUAGES
    return {"languages": INDIAN_LANGUAGES}


@app.post("/cache/clear")
async def cache_clear_endpoint():
    """Clear the response cache."""
    response_cache.clear()
    return {"status": "Cache cleared"}


@app.get("/cache/stats")
async def cache_stats_endpoint():
    """Return cache statistics."""
    return response_cache.stats()


@app.get("/rate-limit/stats")
async def rate_limit_stats_endpoint():
    """Return rate limiter statistics."""
    cleaned = rate_limiter.cleanup_stale()
    stats = rate_limiter.stats()
    stats["cleaned_stale_sessions"] = cleaned
    return stats


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    request_id = str(uuid.uuid4())
    persona = request.persona
    session_id = request.session_id or request_id

    # Input sanitization and guard
    sanitized_message, is_blocked, block_reason = guard_input(request.message)
    if is_blocked:
        log.warning(f"Input blocked: {block_reason} (session={session_id[:8]})")
        blocked_msg = (
            "I'm sorry, I can't process that request. Let's talk about something else!"
            if persona == "desi"
            else "Your request has been blocked for safety reasons. Please rephrase."
        )
        return {"response": blocked_msg, "request_id": request_id, "session_id": session_id}

    message = sanitized_message

    # Rate limiting
    rate_check = rate_limiter.check(session_id)
    if not rate_check["allowed"]:
        retry_msg = (
            f"You're sending messages too fast. Please wait {rate_check['retry_after']:.1f} seconds."
            if persona == "sarkari"
            else f"Arre yaar, slow down! Thoda ruk jao ({rate_check['retry_after']:.1f}s)."
        )
        return JSONResponse(
            status_code=429,
            content={
                "response": retry_msg,
                "request_id": request_id,
                "session_id": session_id,
                "rate_limited": True,
                "retry_after": rate_check["retry_after"],
            },
        )

    # Load history from persistent store (with in-memory cache)
    if session_id not in conversation_cache:
        conversation_cache[session_id] = session_store.get_history(session_id)
    history = conversation_cache.get(session_id, [])
    is_first_message = len(history) == 0
    cached_response = None if is_first_message else response_cache.get(message, persona)

    if cached_response:
        response_text = cached_response
    else:
        context = {
            "request_id": request_id,
            "persona": persona,
            "session_id": session_id,
            "metadata": {},
            "history": history,
        }

        if not _pipeline_ready:
            log.info(f"Pipeline not ready — using direct LLM for: {message[:60]}")
            response_text = await asyncio.get_event_loop().run_in_executor(
                None, _direct_llm_response, message, persona, history
            )
        else:
            try:
                result = await task_router.route_and_process(message, context)
                final_result = await verification_layer.process(result, context)

                retrieved_results = context.get("retrieved_results", [])
                log_interaction(
                    query=message,
                    retrieved_results=retrieved_results,
                    persona=persona,
                    request_id=request_id,
                )

                response_text = final_result.get("response", "Error generating response")

            except Exception as e:
                log.error(f"Error in chat endpoint: {e}")
                response_text = await asyncio.get_event_loop().run_in_executor(
                    None, _direct_llm_response, message, persona, history
                )

    # Cache the response
    response_cache.set(message, persona, response_text)

    # Persist to session store
    session_store.add_message(session_id, "user", message)
    session_store.add_message(session_id, "assistant", response_text)
    conversation_cache[session_id] = session_store.get_history(session_id)

    # Summarize old history if getting too long
    cached = conversation_cache.get(session_id, [])
    if conversation_summarizer.should_summarize(cached, MAX_HISTORY_MESSAGES * 2):
        compressed = await conversation_summarizer.summarize_and_compress(
            cached, MAX_HISTORY_MESSAGES * 2, persona
        )
        session_store.replace_history(session_id, compressed)
        conversation_cache[session_id] = compressed
        log.info(f"Conversation summarized for session {session_id[:8]}...")

    return {
        "response": response_text,
        "request_id": request_id,
        "session_id": session_id,
    }


# ── Streaming SSE Endpoint ───────────────────────────────────────────────────

async def _stream_response(
    message: str, persona: str, session_id: str, request_id: str, history: List[Dict]
) -> AsyncGenerator[str, None]:
    """Generator that yields SSE events for streaming responses."""
    context = {
        "request_id": request_id,
        "persona": persona,
        "session_id": session_id,
        "metadata": {},
        "history": history,
    }

    full_response = ""

    try:
        # Try full pipeline first (non-streaming, but we send it as a stream)
        if _pipeline_ready:
            result = await task_router.route_and_process(message, context)
            final_result = await verification_layer.process(result, context)
            full_response = final_result.get("response", "Error generating response")

            retrieved_results = context.get("retrieved_results", [])
            log_interaction(
                query=message,
                retrieved_results=retrieved_results,
                persona=persona,
                request_id=request_id,
            )
        else:
            # Pipeline not ready — use direct LLM
            full_response = await asyncio.get_event_loop().run_in_executor(
                None, _direct_llm_response, message, persona, history
            )
    except Exception as e:
        print(f"Error in streaming endpoint: {e}")
        full_response = await asyncio.get_event_loop().run_in_executor(
            None, _direct_llm_response, message, persona, history
        )

    # Persist to session store
    session_store.add_message(session_id, "user", message)
    session_store.add_message(session_id, "assistant", full_response)
    conversation_cache[session_id] = session_store.get_history(session_id)

    # Stream the response word-by-word for a typewriter effect
    words = full_response.split(" ")
    buffer = ""
    for i, word in enumerate(words):
        buffer += (" " if i > 0 else "") + word
        # Send in small chunks (every 3-5 words) for smooth streaming
        if (i + 1) % 4 == 0 or i == len(words) - 1:
            event_data = json.dumps({
                "type": "token",
                "content": buffer,
                "done": i == len(words) - 1,
            })
            yield f"data: {event_data}\n\n"
            buffer = ""
            await asyncio.sleep(0.03)  # Small delay for typewriter effect

    # Send final done event
    final_event = json.dumps({
        "type": "done",
        "request_id": request_id,
        "session_id": session_id,
        "full_response": full_response,
    })
    yield f"data: {final_event}\n\n"


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """SSE streaming endpoint — returns Server-Sent Events."""
    request_id = str(uuid.uuid4())
    session_id = request.session_id or request_id

    # Input sanitization and guard
    sanitized_message, is_blocked, block_reason = guard_input(request.message)
    if is_blocked:
        log.warning(f"Input blocked (stream): {block_reason} (session={session_id[:8]})")
        blocked_msg = (
            "I'm sorry, I can't process that request. Let's talk about something else!"
            if request.persona == "desi"
            else "Your request has been blocked for safety reasons. Please rephrase."
        )
        async def blocked_stream():
            yield f"data: {{\"type\": \"token\", \"content\": \"{blocked_msg}\", \"done\": true}}\n\n"
        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    if session_id not in conversation_cache:
        conversation_cache[session_id] = session_store.get_history(session_id)
    history = conversation_cache.get(session_id, [])

    return StreamingResponse(
        _stream_response(request.message, request.persona, session_id, request_id, history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# IMAGE / MULTI-MODAL
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/scan")
async def scan_image(file: UploadFile = File(...), task: str = Form("auto")):
    """Scan/OCR a document image."""
    try:
        from pipeline.multimodal import multimodal
        content = await file.read()
        result = multimodal.process_image_bytes(content, filename=file.filename, task=task)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/scan/base64")
async def scan_base64(request: Request):
    """Scan a base64-encoded image."""
    body = await request.json()
    b64 = body.get("image", "")
    task = body.get("task", "auto")
    from pipeline.multimodal import multimodal
    return multimodal.process_base64(b64, task=task)


# ═══════════════════════════════════════════════════════════════════════════
# PROACTIVE SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/suggestions/{session_id}")
async def get_suggestions(session_id: str):
    """Get proactive follow-up suggestions for a session."""
    from pipeline.suggestions import suggestion_engine
    history = session_store.get_history(session_id)
    if not history:
        return {"suggestions": []}
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    last_ai = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
    suggestions = suggestion_engine.analyze_message(last_user, last_ai)
    return {"suggestions": suggestions}


# ═══════════════════════════════════════════════════════════════════════════
# CONVERSATION BRANCHING
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/branches/{session_id}")
async def list_branches(session_id: str):
    from pipeline.branching import branching_store
    return {"branches": branching_store.get_branches(session_id)}


@app.post("/branches/{session_id}/fork")
async def fork_branch(session_id: str, request: Request):
    body = await request.json()
    from_message = body.get("from_message_id", "")
    new_branch = body.get("branch_id", f"branch_{int(datetime.now().timestamp())}")
    from pipeline.branching import branching_store
    success = branching_store.fork_from(session_id, from_message, new_branch)
    return {"success": success, "branch_id": new_branch}


@app.get("/branches/{session_id}/{branch_id}")
async def get_branch(session_id: str, branch_id: str):
    from pipeline.branching import branching_store
    messages = branching_store.get_thread(session_id, branch_id)
    return {"branch_id": branch_id, "messages": messages}


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-USER PROFILES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/profiles")
async def list_profiles():
    from pipeline.profiles import profile_manager
    return {"profiles": profile_manager.list_profiles()}


@app.post("/profiles")
async def create_profile(request: Request):
    body = await request.json()
    from pipeline.profiles import profile_manager
    profile = profile_manager.create_profile(
        name=body.get("name", "User"),
        avatar=body.get("avatar"),
        language=body.get("language", "hi"),
        persona=body.get("persona", "desi"),
        city=body.get("city", ""),
    )
    return profile


@app.post("/profiles/switch")
async def switch_profile(request: Request):
    body = await request.json()
    from pipeline.profiles import profile_manager
    success = profile_manager.switch_profile(body.get("profile_id", ""))
    return {"success": success}


@app.get("/profiles/active")
async def active_profile():
    from pipeline.profiles import profile_manager
    return profile_manager.get_active_profile()


# ═══════════════════════════════════════════════════════════════════════════
# DATA EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/export/{session_id}")
async def export_chat(session_id: str, format: str = "json"):
    from pipeline.branching import branching_store
    if format == "markdown":
        from fastapi.responses import PlainTextResponse
        data = branching_store.export_session(session_id, format="markdown")
        return PlainTextResponse(data, media_type="text/markdown")
    else:
        data = branching_store.export_session(session_id, format="json")
        return json.loads(data)


# ═══════════════════════════════════════════════════════════════════════════
# OFFLINE MODE
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/offline/knowledge")
async def offline_knowledge(topic: str = None):
    from pipeline.offline import offline_cache
    return {"knowledge": offline_cache.get_offline_knowledge(topic)}


@app.get("/offline/cache-stats")
async def cache_stats():
    from pipeline.offline import offline_cache
    return offline_cache.get_cache_stats()


@app.post("/offline/sync")
async def sync_offline(request: Request):
    body = await request.json()
    from pipeline.offline import offline_cache
    success = offline_cache.queue_sync(
        session_id=body.get("session_id", "default"),
        message=body.get("message", ""),
        persona=body.get("persona", "desi"),
    )
    return {"queued": success}


# ═══════════════════════════════════════════════════════════════════════════
# WHATSAPP / TELEGRAM WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/webhook/whatsapp")
async def whatsapp_verify(request: Request):
    """WhatsApp webhook verification."""
    from pipeline.messaging import whatsapp
    params = dict(request.query_params)
    challenge = whatsapp.verify_webhook(
        params.get("hub.mode", ""),
        params.get("hub.verify_token", ""),
        params.get("hub.challenge", ""),
    )
    if challenge:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge)
    return JSONResponse({"error": "verification failed"}, status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp incoming message webhook."""
    from pipeline.messaging import whatsapp, format_for_platform
    body = await request.json()
    result = whatsapp.process_webhook(body)

    if result["status"] == "ok" and result.get("message"):
        # Process through the AI pipeline
        pipeline = _ensure_pipeline()
        if pipeline:
            response = await pipeline.process(result["message"], {"persona": "desi", "platform": "whatsapp"})
            text = format_for_platform(response.get("response", ""), "whatsapp")
            whatsapp.send_message(result["phone"], text)

    return {"status": "ok"}


@app.get("/webhook/telegram")
async def telegram_verify(request: Request):
    """Telegram webhook verification."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("OK")


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Telegram incoming message webhook."""
    from pipeline.messaging import telegram, format_for_platform
    body = await request.json()
    result = telegram.process_update(body)

    if result["status"] == "ok" and result.get("message"):
        chat_id = result["chat_id"]

        # Send typing indicator
        telegram.send_typing(chat_id)

        # Process through AI pipeline
        pipeline = _ensure_pipeline()
        if pipeline:
            response = await pipeline.process(result["message"], {"persona": "desi", "platform": "telegram"})
            text = format_for_platform(response.get("response", ""), "telegram")
            telegram.send_message(chat_id, text)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
