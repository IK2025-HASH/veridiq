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

BATCH_TYPES = {
    "TEST_CASES",
    "BDD_SCENARIOS",
    "NEGATIVE_TEST_CASES",
    "EXPLORATORY_CHARTER",
}

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

GENERATION_ICONS = {
    "TEST_CASES":           "✅",
    "BDD_SCENARIOS":        "\U0001f952",
    "NEGATIVE_TEST_CASES":  "❌",
    "TEST_PLAN":            "\U0001f4cb",
    "DEFECT_REPORT":        "\U0001f41b",
    "EXPLORATORY_CHARTER":  "\U0001f50d",
    "AC_REVIEW":            "\U0001f50e",
    "REGRESSION_IMPACT":    "\U0001f504",
}


async def _get_client() -> tuple[anthropic.AsyncAnthropic, str]:
    """Return an Anthropic client and model name, reading config from DB first."""
    from app.core import settings_service
    api_key = await settings_service.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY
    model = await settings_service.get("anthropic_model") or settings.ANTHROPIC_MODEL
    return anthropic.AsyncAnthropic(api_key=api_key), model


def build_prompt(
    generation_type: str,
    user_input: str,
    quantity: int = 1,
    issue_context: dict | None = None,
) -> tuple[str, str]:
    knowledge = knowledge_store.get_relevant_chunks(generation_type, user_input)
    system_role = SYSTEM_ROLES.get(generation_type, "You are a professional software tester.")

    if knowledge:
        system_prompt = f"""{system_role}

--- TESTING KNOWLEDGE CONTEXT ---
The following professional testing knowledge informs your generation. Apply it naturally.

{knowledge}
--- END KNOWLEDGE CONTEXT ---"""
    else:
        system_prompt = system_role

    context_block = ""
    if issue_context:
        context_block = f"""
JIRA ISSUE CONTEXT:
Issue Key: {issue_context.get('key', 'N/A')}
Summary: {issue_context.get('summary', 'N/A')}
Description: {issue_context.get('description', 'N/A')}
Acceptance Criteria: {issue_context.get('acceptance_criteria', 'N/A')}

"""

    instructions_template = GENERATION_INSTRUCTIONS.get(generation_type, "")
    instructions = instructions_template.replace("{n}", str(quantity))
    for i in range(1, quantity + 1):
        instructions = instructions.replace(f"{{{i}}}", str(i))

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
    client, model = await _get_client()
    if not client.api_key:
        yield "\n\n**Error:** Anthropic API key not configured. Visit /admin/settings to add your key."
        return

    system_prompt, user_message = build_prompt(
        generation_type, user_input, quantity, issue_context
    )

    try:
        async with client.messages.stream(
            model=model,
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
    client, model = await _get_client()
    system_prompt, user_message = build_prompt(
        generation_type, user_input, quantity, issue_context
    )

    start = time.monotonic()
    response = await client.messages.create(
        model=model,
        max_tokens=settings.MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    full_text = response.content[0].text if response.content else ""
    return full_text, duration_ms
