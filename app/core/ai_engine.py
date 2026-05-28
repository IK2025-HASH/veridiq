# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — AI Generation Engine

import time
import logging
from typing import AsyncGenerator
import anthropic

from app.config import settings
from app.core.knowledge import knowledge_store
from app.core.prompt_templates import SYSTEM_ROLES, GENERATION_INSTRUCTIONS

logger = logging.getLogger(__name__)

# Generation types that support n= quantity
BATCH_TYPES = {
    "TEST_CASES",
    "BDD_SCENARIOS",
    "NEGATIVE_TEST_CASES",
    "EXPLORATORY_CHARTER",
}

# Human-readable labels for the UI
GENERATION_LABELS = {
    "TEST_CASES":           "Test Cases",
    "BDD_SCENARIOS":        "BDD Scenarios",
    "NEGATIVE_TEST_CASES":  "Negative Test Cases",
    "TEST_PLAN":            "Test Plan Summary",
    "DEFECT_REPORT":        "Defect Report",
    "EXPLORATORY_CHARTER":  "Exploratory Charter",
    "AC_REVIEW":            "Acceptance Criteria Review",
    "REGRESSION_IMPACT":    "Regression Impact Analysis",
}

# Icons for the UI (emoji — no external dependency)
GENERATION_ICONS = {
    "TEST_CASES":           "✅",
    "BDD_SCENARIOS":        "🥒",
    "NEGATIVE_TEST_CASES":  "❌",
    "TEST_PLAN":            "📋",
    "DEFECT_REPORT":        "🐛",
    "EXPLORATORY_CHARTER":  "🔍",
    "AC_REVIEW":            "🔎",
    "REGRESSION_IMPACT":    "🔄",
}


def build_prompt(
    generation_type: str,
    user_input: str,
    quantity: int = 1,
    issue_context: dict | None = None,
) -> tuple[str, str]:
    """
    Assemble the system prompt and user message for a generation call.
    Returns (system_prompt, user_message).
    """
    # Layer 0 — Knowledge chunks
    knowledge = knowledge_store.get_relevant_chunks(generation_type, user_input)

    # Layer 1 — System role
    system_role = SYSTEM_ROLES.get(generation_type, "You are a professional software tester.")

    # Build system prompt
    if knowledge:
        system_prompt = f"""{system_role}

--- TESTING KNOWLEDGE CONTEXT ---
The following professional testing knowledge informs your generation. Apply it naturally.

{knowledge}
--- END KNOWLEDGE CONTEXT ---"""
    else:
        system_prompt = system_role

    # Layer 2 — Issue context (Jira Connect, future)
    context_block = ""
    if issue_context:
        context_block = f"""
JIRA ISSUE CONTEXT:
Issue Key: {issue_context.get('key', 'N/A')}
Summary: {issue_context.get('summary', 'N/A')}
Description: {issue_context.get('description', 'N/A')}
Acceptance Criteria: {issue_context.get('acceptance_criteria', 'N/A')}

"""

    # Layer 3 — Generation instructions
    instructions_template = GENERATION_INSTRUCTIONS.get(generation_type, "")
    n_label = str(quantity)

    # Replace placeholders
    instructions = instructions_template.replace("{n}", n_label)
    for i in range(1, quantity + 1):
        instructions = instructions.replace(f"{{{i}}}", str(i))

    # Build final user message
    user_message = f"""{context_block}USER INPUT:
{user_input}

INSTRUCTIONS:
{instructions}"""

    return system_prompt, user_message


async def stream_generation(
    generation_type: str,
    user_input: str,
    quantity: int = 1,
    issue_context: dict | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream AI generation output token by token.
    Yields text chunks as they arrive from Anthropic.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_prompt, user_message = build_prompt(
        generation_type, user_input, quantity, issue_context
    )

    try:
        async with client.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    except anthropic.APIConnectionError as e:
        logger.error(f"Anthropic connection error: {e}")
        yield "\n\n**Error:** Connection to AI service failed. Please try again."
    except anthropic.RateLimitError:
        logger.error("Anthropic rate limit hit")
        yield "\n\n**Error:** Service is busy. Please try again in a moment."
    except anthropic.APIStatusError as e:
        logger.error(f"Anthropic API error {e.status_code}: {e.message}")
        yield f"\n\n**Error:** AI service error ({e.status_code}). Please try again."


async def generate_full(
    generation_type: str,
    user_input: str,
    quantity: int = 1,
    issue_context: dict | None = None,
) -> tuple[str, int]:
    """
    Generate a complete (non-streaming) response.
    Returns (full_text, duration_ms).
    """
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_prompt, user_message = build_prompt(
        generation_type, user_input, quantity, issue_context
    )

    start = time.monotonic()

    response = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    full_text = response.content[0].text if response.content else ""

    return full_text, duration_ms
