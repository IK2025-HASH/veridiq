# Copyright © 2026 Network Logic Limited. All rights reserved.
# Verid-iq Knowledge Engine — loads and serves the 6 testing knowledge volumes

from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Maps each generation type to the most relevant knowledge volumes
VOLUME_MAP = {
    "TEST_CASES":           ["vol1_testing_standards", "vol2_test_design_techniques"],
    "BDD_SCENARIOS":        ["vol3_bdd_gherkin", "vol2_test_design_techniques"],
    "NEGATIVE_TEST_CASES":  ["vol2_test_design_techniques", "vol1_testing_standards"],
    "TEST_PLAN":            ["vol4_test_management", "vol1_testing_standards"],
    "DEFECT_REPORT":        ["vol1_testing_standards"],
    "EXPLORATORY_CHARTER":  ["vol1_testing_standards", "vol4_test_management"],
    "AC_REVIEW":            ["vol1_testing_standards", "vol2_test_design_techniques"],
    "REGRESSION_IMPACT":    ["vol4_test_management", "vol1_testing_standards"],
}


class KnowledgeStore:
    """
    Loads the 6 Verid-iq knowledge volumes at startup and serves
    relevant chunks to the AI generation engine per request.
    """

    def __init__(self):
        self.chunks: dict[str, list[str]] = {}
        self._loaded = False

    def load(self, knowledge_dir: Path = None):
        dir_path = knowledge_dir or settings.KNOWLEDGE_DIR
        if not dir_path.exists():
            logger.warning(f"Knowledge directory not found: {dir_path}")
            return

        loaded_count = 0
        for vol_file in sorted(dir_path.glob("*.md")):
            text = vol_file.read_text(encoding="utf-8")
            chunks = self._chunk_text(text)
            self.chunks[vol_file.stem] = chunks
            loaded_count += 1
            logger.info(f"Loaded {vol_file.stem}: {len(chunks)} chunks")

        self._loaded = True
        logger.info(f"Knowledge store ready: {loaded_count} volumes, "
                    f"{sum(len(c) for c in self.chunks.values())} total chunks")

    def _chunk_text(self, text: str) -> list[str]:
        """Split markdown text into meaningful chunks by paragraph/section."""
        chunks = []
        # Split on double newline (paragraph boundaries)
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            # Only keep chunks with meaningful content (>80 chars)
            if len(para) > 80:
                chunks.append(para)
        return chunks

    def get_relevant_chunks(
        self,
        generation_type: str,
        user_input: str,
        max_chunks: int = 6
    ) -> str:
        """
        Return the most relevant knowledge chunks for a generation call.
        Uses keyword overlap scoring between user input and chunk content.
        """
        if not self._loaded or not self.chunks:
            return ""

        relevant_volumes = VOLUME_MAP.get(generation_type, list(self.chunks.keys()))

        # Gather all chunks from relevant volumes
        candidate_chunks = []
        for vol_name in relevant_volumes:
            candidate_chunks.extend(self.chunks.get(vol_name, []))

        if not candidate_chunks:
            return ""

        # Score chunks by keyword overlap with user input
        input_words = set(user_input.lower().split())
        # Remove common stop words from scoring
        stop_words = {"the", "a", "an", "is", "in", "on", "at", "to", "for",
                      "of", "and", "or", "with", "as", "by", "from", "that"}
        input_words -= stop_words

        scored = []
        for chunk in candidate_chunks:
            chunk_words = set(chunk.lower().split()) - stop_words
            overlap = len(input_words & chunk_words)
            scored.append((chunk, overlap))

        # Sort by relevance, take top N
        scored.sort(key=lambda x: x[1], reverse=True)
        top_chunks = [chunk for chunk, _ in scored[:max_chunks]]

        return "\n\n---\n\n".join(top_chunks)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def volume_names(self) -> list[str]:
        return list(self.chunks.keys())


# Singleton instance — loaded once at app startup
knowledge_store = KnowledgeStore()
