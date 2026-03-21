"""FastAPI server for wandi-agent — Instagram Reels content generator."""

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import agent
import airtable_client as at
import config
import ollama_client as ollama
import quota as quota_module
import session_store
import supabase_client
import user_resolver
import video_picker
from renderer import get_renderer, RenderRequest, JobStatus, BrandConfig
from renderer.brand import resolve_brand_for_render


# ── Constants ────────────────────────────────────────────────────────────────

_AWARENESS_STAGE_MAP = {
    "Unaware": 1,
    "Problem-Aware": 3,
    "Solution-Aware": 5,
}


def _build_segments(request: RenderRequest) -> list[dict[str, Any]]:
    """Convert a RenderRequest to a segments list for the Remotion service.

    When the request already has segments, returns them as camelCase dicts.
    When using legacy hook_text/body_text, auto-converts to 2 segments
    by splitting the duration in half.
    """
    if request.segments is not None:
        return [
            {
                "text": s.text,
                "startSeconds": s.start_seconds,
                "endSeconds": s.end_seconds,
                "animationStyle": s.animation_style,
                "role": s.role,
            }
            for s in request.segments
        ]

    # Legacy mode: auto-convert hook_text/body_text to segments.
    # Use 15 as placeholder for segment timing — Remotion will detect
    # the actual video duration via ffprobe and rescale segments.
    duration = request.duration_in_seconds or 15

    # Hook-only reel: single segment spanning full duration
    if not request.body_text:
        return [
            {
                "text": request.hook_text or "",
                "startSeconds": 0.0,
                "endSeconds": float(duration),
                "animationStyle": request.animation_style,
                "role": "hook",
            },
        ]

    # Hook + text reel: hook gets 40%, body gets 60%
    # (hooks are short and punchy, body text needs more screen time)
    hook_end = duration * 0.4
    return [
        {
            "text": request.hook_text or "",
            "startSeconds": 0.0,
            "endSeconds": hook_end,
            "animationStyle": request.animation_style,
            "role": "hook",
        },
        {
            "text": request.body_text or "",
            "startSeconds": hook_end,
            "endSeconds": float(duration),
            "animationStyle": request.animation_style,
            "role": "body",
        },
    ]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Render job state ──────────────────────────────────────────────────────────

# In-memory job store and background task set (single-process, no GC risk)
_render_jobs: dict[str, dict[str, Any]] = {}
_background_tasks: set = set()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("wandi-agent starting up...")
    # Check Ollama connectivity
    if await ollama.check_health():
        logger.info("Ollama is reachable")
    else:
        logger.warning("Ollama is NOT reachable — generation will fail")

    # Check Remotion service
    renderer = get_renderer()
    if await renderer.health_check():
        logger.info("Remotion service is reachable")
    else:
        logger.warning("Remotion service is NOT reachable - renders will fail")

    yield
    logger.info("wandi-agent shutting down...")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="wandi-agent",
    description="AI agent for generating Instagram Reels content",
    version="1.1.0",
    lifespan=lifespan,
)

# Allow CORS for Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    client_id: str = Field(..., description="Airtable record ID of the client (recXXX)")
    batch_type: str = Field(
        ...,
        description="Content batch type: חשיפה / מכירה / מעורב",
    )
    quantity: int = Field(default=10, ge=1, le=30, description="Number of reels to generate")
    content_mix: dict[str, float] = Field(
        default_factory=lambda: {"niche": 1.0},
        description='Content category mix ratio, e.g. {"niche": 0.6, "personal brand": 0.4}',
    )


class GenerateAsyncRequest(BaseModel):
    """Request model for async generation with callback."""
    client_id: str = Field(..., description="Airtable record ID of the client (recXXX)")
    batch_type: str = Field(
        ...,
        description="Content batch type: חשיפה / מכירה / מעורב",
    )
    quantity: int = Field(default=7, ge=1, le=30, description="Number of reels to generate")
    callback_url: str = Field(..., description="URL to POST results to when done")
    user_id: str = Field(..., description="Supabase user UUID")
    connection_id: str = Field(default="", description="Supabase meta_connection UUID")
    webhook_secret: str = Field(default="", description="Shared secret for callback auth")
    folders: dict[str, str] = Field(
        default_factory=dict,
        description="Map of folder_id → display name for video selection",
    )
    content_sources: list[str] = Field(
        default_factory=list,
        description="Data sources to fetch: hooks, viral_pool, rtm_events, style_examples, insights. Empty = all.",
    )
    content_mix: dict[str, float] = Field(
        default_factory=lambda: {"niche": 1.0},
        description='Content category mix ratio, e.g. {"niche": 0.6, "personal brand": 0.4}',
    )


class GenerateResponse(BaseModel):
    success: bool
    client_name: str | None = None
    batch_type: str | None = None
    distribution: dict[str, int] | None = None
    reels: list[dict[str, Any]] = []
    count: int = 0
    saved_count: int = 0
    errors: list[str] | None = None


# ── Background task ──────────────────────────────────────────────────────────

async def _run_generation_and_callback(request: GenerateAsyncRequest):
    """Background task: generate reels and POST results to callback URL."""
    batch_id = str(uuid.uuid4())
    try:
        logger.info(
            f"[async] Starting generation: client={request.client_id}, "
            f"type={request.batch_type}, qty={request.quantity}, batch={batch_id}"
        )

        # Run the generation pipeline (fetches client + magnets internally)
        result = await agent.generate_reels(
            client_id=request.client_id,
            batch_type=request.batch_type,
            quantity=request.quantity,
            folders=request.folders,
            content_sources=request.content_sources or None,
            content_mix=request.content_mix,
        )

        # Map reels to content_projects format
        projects = []
        for reel in result.get("reels", []):
            projects.append({
                "caption": reel.get("caption", ""),
                "video_text": reel.get("text_on_video") or "",
                "hook": reel.get("hook") or "",
                "hook_type": reel.get("hook_type", ""),
                "awareness_stage": reel.get("awareness_stage", ""),
                "content_goal": {
                    "חשיפה": "exposure",
                    "מכירה": "sales",
                    "מעורב": "mixed",
                }.get(reel.get("content_type", ""), "exposure"),
                "magnet_name": reel.get("magnet_name", ""),
                "airtable_record_id": reel.get("record_id", ""),
                "client_airtable_id": request.client_id,
                "client_name": result.get("client_name", ""),
                "batch_id": batch_id,
                "folder_id": reel.get("folder_id"),
                "source_video_url": None,
                "render_error": None,
                "status": "draft",
            })

        # ── Video picking + rendering ────────────────────────────────
        if request.folders:
            reels_data = result.get("reels", [])
            video_urls = video_picker.pick_videos_for_reels(
                request.user_id, request.folders, reels_data
            )

            # Assign source_video_url to projects
            for i, url in enumerate(video_urls):
                if i < len(projects):
                    projects[i]["source_video_url"] = url

            # Fetch client record once for brand config (used by all renders)
            client_record = await at.get_client(request.client_id)

            # Render each reel that has a source video and record_id.
            # Remotion processes renders serially, so with N reels the last one
            # may wait up to N * ~3min before it even starts. Scale the poll
            # timeout accordingly: base 10min + 3min per reel in the batch.
            num_reels = len([p for p in projects if p.get("source_video_url") and p.get("airtable_record_id")])
            # With parallel rendering (MAX_CONCURRENT_RENDERS=2), renders overlap.
            # Base 10min + ~3min per concurrent "wave" of renders.
            max_poll_attempts = 120 + (max(1, (num_reels + 1) // 2) * 36)

            async def _render_one(idx: int, project: dict) -> None:
                source_url = project.get("source_video_url")
                record_id = project.get("airtable_record_id")
                if not source_url or not record_id:
                    return

                try:
                    render_req = RenderRequest(
                        source_video_url=source_url,
                        hook_text=project.get("hook") or "",
                        body_text=project.get("video_text") or "",
                        record_id=record_id,
                        client_id=request.client_id,
                        awareness_stage=_AWARENESS_STAGE_MAP.get(
                            project.get("awareness_stage", ""), None
                        ),
                    )

                    logger.info(
                        f"[Render] Reel {idx}: duration_in_seconds={render_req.duration_in_seconds}, "
                        f"source_url={source_url[:100]}..."
                    )

                    renderer = get_renderer()
                    brand_config = at.extract_brand_config(client_record)
                    resolved_brand = resolve_brand_for_render(
                        brand_config, render_req.awareness_stage
                    )
                    segments = _build_segments(render_req)

                    remotion_job_id = await renderer.render(
                        render_req, resolved_brand=resolved_brand, segments=segments
                    )

                    # Poll until done
                    for attempt in range(max_poll_attempts):
                        status = await renderer.get_status(remotion_job_id)
                        if status.state == "completed":
                            break
                        elif status.state == "failed":
                            raise RuntimeError(f"Render failed: {status.error}")
                        wait = min(2 + attempt, 5)
                        await asyncio.sleep(wait)
                    else:
                        raise RuntimeError("Render timed out")

                    # Download + upload
                    tmp_path = f"/tmp/{record_id}-{remotion_job_id}.mp4"
                    await renderer.download_file(remotion_job_id, tmp_path)

                    destination = f"{record_id}/{remotion_job_id}.mp4"
                    video_url = await supabase_client.upload_video(tmp_path, destination)

                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

                    # Mark as rendered once video is in Supabase (before Airtable update)
                    project["source_video_url"] = video_url
                    project["status"] = "draft"
                    logger.info(f"[async] Rendered reel {idx}: {video_url}")

                    # Airtable attachment update — separate try-except so a failure
                    # here does not mark the entire render as failed.
                    try:
                        await at.update_content_queue_video_attachment(record_id, video_url)
                    except Exception as e:
                        logger.error(
                            f"[async] Airtable attachment update failed for reel {idx}: {e}"
                        )

                except Exception as e:
                    logger.error(f"[async] Render failed for reel {idx}: {e}")
                    project["render_error"] = str(e)
                    project["status"] = "draft"

            await asyncio.gather(
                *[_render_one(i, p) for i, p in enumerate(projects)]
            )

        logger.info(
            f"[async] Generation complete: {len(projects)} reels, "
            f"sending to callback {request.callback_url}"
        )

        # POST to callback with retry
        callback_payload = {
            "user_id": request.user_id,
            "connection_id": request.connection_id,
            "batch_id": batch_id,
            "projects": projects,
        }

        headers = {"Content-Type": "application/json"}
        if request.webhook_secret:
            headers["X-Webhook-Secret"] = request.webhook_secret

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        request.callback_url,
                        json=callback_payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    logger.info(
                        f"[async] Callback success (attempt {attempt + 1}): "
                        f"{resp.status_code}"
                    )
                    return
            except Exception as e:
                last_error = e
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    f"[async] Callback attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)

        logger.error(f"[async] All callback attempts failed: {last_error}")

    except Exception as e:
        logger.exception(f"[async] Generation failed for batch {batch_id}: {e}")

        # Try to notify callback about the failure
        try:
            error_payload = {
                "user_id": request.user_id,
                "connection_id": request.connection_id,
                "batch_id": batch_id,
                "projects": [],
                "error": str(e),
            }
            headers = {"Content-Type": "application/json"}
            if request.webhook_secret:
                headers["X-Webhook-Secret"] = request.webhook_secret

            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    request.callback_url,
                    json=error_payload,
                    headers=headers,
                )
        except Exception:
            logger.exception("[async] Failed to send error callback")


# ── Render background tasks ───────────────────────────────────────────────────

async def _send_render_callback(callback_url: str, job_data: dict):
    """POST job result to callback URL with 3-attempt retry and exponential backoff."""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(callback_url, json=job_data)
                resp.raise_for_status()
                return
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(
                f"Render callback attempt {attempt + 1} failed: {e}, retrying in {wait}s"
            )
            await asyncio.sleep(wait)
    logger.error(f"All render callback attempts failed for {callback_url}")


async def _run_render(job_id: str, request: RenderRequest):
    """Background task: submit to Remotion, poll until done, download file."""
    renderer = get_renderer()
    MAX_POLL_ATTEMPTS = 120  # 120 * up-to-5s = 10 min max
    try:
        # Fetch brand config from Airtable when client_id is present.
        # Falls back to all-defaults BrandConfig for backward compatibility.
        if request.client_id:
            client_record = await at.get_client(request.client_id)
            brand_config = at.extract_brand_config(client_record)
        else:
            brand_config = BrandConfig()
        resolved_brand = resolve_brand_for_render(brand_config, request.awareness_stage)

        # Build segments for Remotion payload (from request.segments or auto-converted)
        segments = _build_segments(request)

        # Submit to Remotion service
        remotion_job_id = await renderer.render(request, resolved_brand=resolved_brand, segments=segments)
        _render_jobs[job_id]["status"] = "rendering"
        _render_jobs[job_id]["remotion_job_id"] = remotion_job_id

        # Poll until done or timed out
        for attempt in range(MAX_POLL_ATTEMPTS):
            status = await renderer.get_status(remotion_job_id)
            _render_jobs[job_id]["progress"] = status.progress
            if status.state == "completed":
                break
            elif status.state == "failed":
                raise RuntimeError(f"Remotion render failed: {status.error}")
            wait = min(2 + attempt, 5)
            await asyncio.sleep(wait)
        else:
            _render_jobs[job_id]["status"] = "timed_out"
            _render_jobs[job_id]["error"] = "Render timed out after max poll attempts"
            logger.error(f"Render job {job_id} timed out (remotion: {remotion_job_id})")
            return

        # Download rendered file from Remotion service
        _render_jobs[job_id]["status"] = "downloading"
        tmp_path = f"/tmp/{job_id}-rendered.mp4"
        await renderer.download_file(remotion_job_id, tmp_path)

        # Upload to Supabase Storage
        _render_jobs[job_id]["status"] = "uploading"
        destination = f"{request.record_id}/{job_id}.mp4"
        video_url = await supabase_client.upload_video(tmp_path, destination)

        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        # Mark completed with Supabase public URL (not local path)
        _render_jobs[job_id]["status"] = "completed"
        _render_jobs[job_id]["progress"] = 1.0
        _render_jobs[job_id]["video_url"] = video_url
        logger.info(f"Render job {job_id} completed: {video_url}")

        # Airtable attachment update — separate try-except so a failure
        # here does not mark the entire render as failed.
        try:
            await at.update_content_queue_video_attachment(request.record_id, video_url)
        except Exception as e:
            logger.error(f"Airtable attachment update failed for job {job_id}: {e}")

        # Notify callback if provided
        if request.callback_url:
            await _send_render_callback(request.callback_url, _render_jobs[job_id])

    except Exception as e:
        logger.exception(f"Render job {job_id} failed: {e}")
        _render_jobs[job_id]["status"] = "failed"
        _render_jobs[job_id]["error"] = str(e)
        if request.callback_url:
            try:
                await _send_render_callback(request.callback_url, _render_jobs[job_id])
            except Exception:
                logger.exception(f"Failed to send error callback for {job_id}")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    ollama_ok = await ollama.check_health()
    return {
        "status": "ok",
        "ollama": "connected" if ollama_ok else "disconnected",
        "model": config.OLLAMA_MODEL,
    }


@app.get("/models")
async def list_models():
    try:
        models = await ollama.list_models()
        return {"models": [m.get("name", m.get("model", "unknown")) for m in models]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Ollama: {e}")


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Synchronous generation — blocks until complete."""
    logger.info(
        f"Generate request: client={request.client_id}, "
        f"type={request.batch_type}, qty={request.quantity}"
    )
    try:
        result = await agent.generate_reels(
            client_id=request.client_id,
            batch_type=request.batch_type,
            quantity=request.quantity,
            content_mix=request.content_mix,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


@app.post("/render", status_code=202)
async def submit_render(request: RenderRequest):
    """Accept a render job, return immediately with job_id, kick off background task."""
    job_id = str(uuid.uuid4())
    _render_jobs[job_id] = {
        "job_id": job_id,
        "status": "accepted",
        "record_id": request.record_id,
        "progress": 0.0,
        "video_url": None,
        "error": None,
    }
    task = asyncio.create_task(_run_render(job_id, request))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"job_id": job_id, "status": "accepted"}


@app.get("/render-status/{job_id}")
async def get_render_status(job_id: str):
    """Return current state of a render job, or 404 if not found."""
    job = _render_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/generate-async", status_code=202)
async def generate_async(request: GenerateAsyncRequest):
    """Async generation — returns immediately, POSTs results to callback_url."""
    logger.info(
        f"Async generate request: client={request.client_id}, "
        f"type={request.batch_type}, qty={request.quantity}, "
        f"callback={request.callback_url}"
    )

    # Validate batch_type
    valid_types = {"חשיפה", "מכירה", "מעורב"}
    if request.batch_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid batch_type '{request.batch_type}'. Must be one of: {valid_types}",
        )

    # Start background task and return immediately
    asyncio.create_task(_run_generation_and_callback(request))
    return {
        "status": "accepted",
        "message": "Content generation started. Results will be sent to callback URL.",
    }


# ── Auth middleware ──────────────────────────────────────────────────────────


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """Validate Supabase JWT from Authorization header.

    Returns {"user_id": str, "email": str}.
    Raises 401 if token is invalid or missing.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    user_info = await user_resolver.validate_supabase_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_info


# ── Agent endpoints ──────────────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    """Request model for the agentic chat endpoint."""
    message: str = Field(..., description="User message in natural language (Hebrew)")
    session_id: str | None = Field(default=None, description="Session ID to continue an existing conversation")
    # client_id is auto-resolved from auth token — no longer required in request


class AgentChatResponse(BaseModel):
    """Response from the agent."""
    session_id: str
    response: str
    steps: int
    tools_used: list[str] = []
    total_duration_ms: int = 0
    error: bool = False


@app.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Agentic chat — the LLM decides what tools to call.

    Requires Authorization: Bearer <supabase_token> header.
    The agent will:
    1. Resolve the user's client profile from their email
    2. Understand the request
    3. Pick the right tools (fetch data, generate content, etc.)
    4. Execute them autonomously
    5. Return a response with results
    """
    import agent_engine

    user_id = current_user["user_id"]
    user_email = current_user.get("email")

    # Check quota before processing
    quota_status = await quota_module.check_quota(user_id)
    if not quota_status.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "חרגת ממכסת ההודעות היומית",
                "plan": quota_status.plan,
                "messages_used": quota_status.messages_used,
                "messages_limit": quota_status.messages_limit,
                "reset_time": quota_status.reset_time,
            },
        )

    # Resolve client_id from user's email
    client_id = await user_resolver.resolve_client_id(user_id, user_email)
    if not client_id:
        raise HTTPException(
            status_code=404,
            detail="לא נמצא פרופיל לקוחה מקושר לחשבון שלך. פני לתמיכה.",
        )

    logger.info(
        f"[Agent Chat] user={user_id}, client={client_id}, "
        f"message={request.message[:100]}..., session={request.session_id}"
    )

    session = await agent_engine.get_or_create_session(
        user_id=user_id,
        client_id=client_id,
        session_id=request.session_id,
    )

    try:
        result = await agent_engine.run_agent(
            user_message=request.message,
            client_id=client_id,
            session=session,
        )

        # Consume quota after successful response
        await quota_module.consume_message(user_id)

        return AgentChatResponse(
            session_id=result.session_id,
            response=result.response,
            steps=result.steps,
            tools_used=[tc.tool_name for tc in result.tool_calls],
            total_duration_ms=result.total_duration_ms,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Agent Chat] Failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")


@app.get("/agent/sessions")
async def list_agent_sessions(current_user: dict = Depends(get_current_user)):
    """List the user's chat sessions for sidebar display."""
    user_id = current_user["user_id"]
    sessions = await session_store.list_sessions(user_id)
    return {"sessions": sessions}


@app.get("/agent/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get full message history for a session."""
    # Verify session belongs to user
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await session_store.get_messages(session_id)
    return {"session_id": session_id, "messages": messages}


@app.get("/agent/quota")
async def get_agent_quota(current_user: dict = Depends(get_current_user)):
    """Get current quota status for the authenticated user."""
    user_id = current_user["user_id"]
    return await quota_module.get_quota_status(user_id)


@app.get("/agent/session/{session_id}")
async def get_agent_session(session_id: str):
    """Get the current state of an agent session (legacy endpoint)."""
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session_store.get_messages(session_id)
    return {
        "session_id": session["id"],
        "client_id": session.get("client_id", ""),
        "message_count": len(messages),
        "status": session.get("status", "active"),
    }


# ── Admin endpoints ──────────────────────────────────────────────────────────


@app.post("/admin/reset-mapping")
async def reset_client_mapping(current_user: dict = Depends(get_current_user)):
    """Reset the cached client mapping for the current user.

    Forces re-resolution from Airtable on next request.
    Useful when a user was mapped to the wrong client.
    """
    user_id = current_user["user_id"]
    success = await user_resolver.invalidate_client_mapping(user_id)
    if success:
        return {"status": "ok", "message": "מיפוי אופס. בהודעה הבאה הלקוחה תזוהה מחדש."}
    raise HTTPException(status_code=500, detail="Failed to reset mapping")


@app.get("/admin/my-mapping")
async def get_my_mapping(current_user: dict = Depends(get_current_user)):
    """Show which Airtable client the current user is mapped to."""
    user_id = current_user["user_id"]
    client_id = await user_resolver.resolve_client_id(
        user_id, current_user.get("email")
    )
    if client_id:
        try:
            client_record = await at.get_client(client_id)
            client_name = client_record.get("fields", {}).get("Client Name", "unknown")
        except Exception:
            client_name = "unknown"
        return {
            "user_id": user_id,
            "email": current_user.get("email"),
            "client_id": client_id,
            "client_name": client_name,
        }
    return {
        "user_id": user_id,
        "email": current_user.get("email"),
        "client_id": None,
        "client_name": None,
        "message": "לא נמצא מיפוי ללקוחה",
    }


# ── Video endpoints ──────────────────────────────────────────────────────────

class PickVideoRequest(BaseModel):
    user_id: str = Field(..., description="Supabase user UUID")


@app.post("/pick-video")
async def pick_video(request: PickVideoRequest):
    """Pick a random source video from the user's raw-media library."""
    url = supabase_client.pick_random_source_video(request.user_id)
    return {"video_url": url}


# ── Startup validation ────────────────────────────────────────────────────────

_REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
    "OLLAMA_BASE_URL",
]


def _validate_env():
    """Check that all required env vars are set and non-empty. Exit if any missing."""
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v, "").strip()]
    if missing:
        print(
            f"FATAL: Missing required environment variables: {', '.join(missing)}\n"
            "Set them in .env or export before starting wandi-agent.",
            file=sys.stderr,
        )
        sys.exit(1)


_validate_env()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL,
        reload=True,
    )
