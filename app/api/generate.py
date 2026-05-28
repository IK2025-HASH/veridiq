# Copyright © 2026 Network Logic Limited. All rights reserved.

import uuid
import time
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.ai_engine import (
    stream_generation,
    generate_full,
    GENERATION_LABELS,
    GENERATION_ICONS,
    BATCH_TYPES,
)
from app.schemas.generate import GenerateRequest, GenerateResponse
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/generate/stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_DAY}/day")
async def generate_stream(request: Request, body: GenerateRequest):
    """
    Stream AI generation output via Server-Sent Events.
    Client receives tokens as they arrive.
    """
    async def event_generator():
        try:
            async for chunk in stream_generation(
                generation_type=body.generation_type,
                user_input=body.input_text,
                quantity=body.quantity,
            ):
                # SSE format: data: <content>\n\n
                # Escape newlines within chunk for SSE
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"

            # Signal completion
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: [ERROR] Generation failed. Please try again.\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_DAY}/day")
async def generate(request: Request, body: GenerateRequest):
    """
    Non-streaming generation endpoint.
    Returns complete output as JSON.
    """
    job_id = str(uuid.uuid4())

    content, duration_ms = await generate_full(
        generation_type=body.generation_type,
        user_input=body.input_text,
        quantity=body.quantity,
    )

    return GenerateResponse(
        job_id=job_id,
        generation_type=body.generation_type,
        content=content,
        duration_ms=duration_ms,
    )


@router.get("/generation-types")
async def get_generation_types():
    """Return all available generation types with metadata for the UI."""
    types = []
    for key, label in GENERATION_LABELS.items():
        types.append({
            "key": key,
            "label": label,
            "icon": GENERATION_ICONS.get(key, "🔧"),
            "supports_quantity": key in BATCH_TYPES,
        })
    return {"types": types}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Verid-iq", "version": settings.VERSION}
