# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq — 3-Layer AI Resolution Engine
#
# Layer 1: User context  (0 credits — no Anthropic call)
# Layer 2: Platform knowledge (1 credit — no Anthropic call)
# Layer 3: Anthropic AI  (3–10 credits — external call)

import logging
import re
from dataclasses import dataclass
from app.core.knowledge import knowledge_store
from app.core.ai_engine import build_prompt, stream_generation, generate_full

logger = logging.getLogger(__name__)

# Credit costs per generation type at Layer 3
CREDIT_COSTS = {
    "DEFECT_REPORT":        3,
    "AC_REVIEW":            3,
    "EXPLORATORY_CHARTER":  3,
    "REGRESSION_IMPACT":    4,
    "TEST_CASES":           4,
    "BDD_SCENARIOS":        4,
    "NEGATIVE_TEST_CASES":  4,
    "TEST_PLAN":            6,
}

BATCH_EXTRA_CREDIT = 2   # per artifact beyond the first
LAYER2_CREDIT_COST  = 1
LAYER1_CREDIT_COST  = 0

# Confidence threshold to answer from Layer 2 without calling Anthropic
LAYER2_CONFIDENCE_THRESHOLD = 0.65

# Simple list of identifying terms to strip before Layer 2 storage
STRIP_PATTERNS = [
    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',          # Proper names (FirstName LastName)
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
    r'https?://\S+',                            # URLs
    r'\b\d{10,}\b',                             # Phone numbers / long IDs
]


@dataclass
class ResolutionResult:
    content: str
    layer_used: str          # layer1 | layer2 | layer3
    credits_charged: int
    confidence: float


class LayerResolver:
    """
    Resolves a generation request through the 3-layer hierarchy.
    Tries to answer from the cheapest layer first.
    """

    def __init__(self):
        self._platform_patterns: dict[str, list[dict]] = {}

    def load_platform_patterns(self, patterns: list[dict]):
        """Load platform knowledge patterns from database into memory."""
        self._platform_patterns = {}
        for p in patterns:
            gen_type = p.get("generation_type", "")
            if gen_type not in self._platform_patterns:
                self._platform_patterns[gen_type] = []
            self._platform_patterns[gen_type].append(p)
        logger.info(f"Platform patterns loaded: {sum(len(v) for v in self._platform_patterns.values())} patterns")

    def _layer1_lookup(
        self,
        generation_type: str,
        user_input: str,
        user_context: list[dict],
    ) -> tuple[str | None, float]:
        """
        Check Layer 1 user context for a relevant prior artifact.
        Returns (content, confidence) — content is None if no hit.
        """
        if not user_context:
            return None, 0.0

        input_words = set(user_input.lower().split())
        best_score = 0.0
        best_pattern = None

        for ctx in user_context:
            if ctx.get("generation_type") != generation_type:
                continue
            if ctx.get("is_classified"):
                continue
            summary = ctx.get("feature_summary", "") or ""
            pattern = ctx.get("artifact_pattern", "") or ""
            summary_words = set(summary.lower().split())
            overlap = len(input_words & summary_words) / max(len(input_words), 1)
            if overlap > best_score:
                best_score = overlap
                best_pattern = pattern

        return (best_pattern, best_score) if best_score > 0.75 else (None, best_score)

    def _layer2_lookup(
        self,
        generation_type: str,
        user_input: str,
    ) -> tuple[str | None, float]:
        """
        Check Layer 2 platform knowledge for a relevant pattern.
        Returns (content, confidence) — content is None if no hit.
        """
        patterns = self._platform_patterns.get(generation_type, [])
        if not patterns:
            return None, 0.0

        input_words = set(user_input.lower().split())
        best_score = 0.0
        best_content = None

        for p in patterns:
            keywords = set((p.get("keywords") or "").lower().split(","))
            pattern_words = set(p.get("pattern_text", "").lower().split())
            all_words = keywords | pattern_words
            overlap = len(input_words & all_words) / max(len(input_words), 1)
            quality = p.get("quality_score", 0.5)
            score = overlap * quality

            if score > best_score:
                best_score = score
                best_content = p.get("pattern_text")

        return (best_content, best_score) if best_score >= LAYER2_CONFIDENCE_THRESHOLD else (None, best_score)

    def calculate_credits(self, generation_type: str, quantity: int, layer: str) -> int:
        if layer == "layer1":
            return LAYER1_CREDIT_COST
        if layer == "layer2":
            return LAYER2_CREDIT_COST
        base = CREDIT_COSTS.get(generation_type, 4)
        extra = max(0, quantity - 1) * BATCH_EXTRA_CREDIT
        return base + extra

    async def resolve(
        self,
        generation_type: str,
        user_input: str,
        quantity: int = 1,
        user_context: list[dict] | None = None,
        issue_context: dict | None = None,
        force_layer3: bool = False,
    ) -> ResolutionResult:
        """
        Attempt Layer 1 → Layer 2 → Layer 3 in order.
        Returns the first satisfactory result.
        """
        user_context = user_context or []

        # ── Layer 1 ──────────────────────────────────────────
        if not force_layer3 and user_context:
            content, confidence = self._layer1_lookup(generation_type, user_input, user_context)
            if content:
                credits = self.calculate_credits(generation_type, quantity, "layer1")
                logger.info(f"Layer 1 hit | type={generation_type} | confidence={confidence:.2f}")
                return ResolutionResult(
                    content=content,
                    layer_used="layer1",
                    credits_charged=credits,
                    confidence=confidence,
                )

        # ── Layer 2 ──────────────────────────────────────────
        if not force_layer3:
            content, confidence = self._layer2_lookup(generation_type, user_input)
            if content:
                credits = self.calculate_credits(generation_type, quantity, "layer2")
                logger.info(f"Layer 2 hit | type={generation_type} | confidence={confidence:.2f}")
                return ResolutionResult(
                    content=content,
                    layer_used="layer2",
                    credits_charged=credits,
                    confidence=confidence,
                )

        # ── Layer 3 — Anthropic ───────────────────────────────
        logger.info(f"Layer 3 call | type={generation_type} | qty={quantity}")
        content, duration_ms = await generate_full(
            generation_type=generation_type,
            user_input=user_input,
            quantity=quantity,
            issue_context=issue_context,
        )
        credits = self.calculate_credits(generation_type, quantity, "layer3")

        return ResolutionResult(
            content=content,
            layer_used="layer3",
            credits_charged=credits,
            confidence=1.0,
        )

    def anonymise(self, text: str) -> str:
        """Strip identifying information before storing in Layer 2."""
        result = text
        for pattern in STRIP_PATTERNS:
            result = re.sub(pattern, "[REDACTED]", result)
        return result

    def extract_pattern(self, content: str, generation_type: str) -> dict:
        """
        Extract a reusable structural pattern from a generated artifact.
        Strips sensitive content, preserves structure.
        Returns a dict suitable for PlatformKnowledge insertion.
        """
        anonymised = self.anonymise(content)
        # Extract keywords — meaningful words longer than 4 chars
        words = re.findall(r'\b[a-z]{5,}\b', anonymised.lower())
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        keywords = ",".join(sorted(freq, key=freq.get, reverse=True)[:20])

        return {
            "generation_type": generation_type,
            "pattern_text": anonymised[:2000],  # cap at 2000 chars
            "keywords": keywords,
            "quality_score": 0.7,
            "source": "interaction",
        }


# Singleton
layer_resolver = LayerResolver()
