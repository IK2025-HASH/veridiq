# Copyright © 2026 Network Logic Limited. All rights reserved.

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from pathlib import Path

# Override settings before import
import os
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"

from app.main import app
from app.core.knowledge import KnowledgeStore
from app.core.ai_engine import build_prompt, GENERATION_LABELS, BATCH_TYPES

client = TestClient(app)


# ── Knowledge Store Tests ─────────────────────────────────────────────────────

def test_knowledge_store_loads_volumes(tmp_path):
    store = KnowledgeStore()
    vol = tmp_path / "vol1_test.md"
    vol.write_text("# Testing Standards\n\nEquivalence partitioning divides inputs into partitions.\n\nBoundary value analysis tests at the edges of valid ranges.\n\nTest cases should have clear expected results.")
    store.load(tmp_path)
    assert store.is_loaded
    assert "vol1_test" in store.volume_names

def test_knowledge_store_returns_chunks(tmp_path):
    store = KnowledgeStore()
    vol = tmp_path / "vol1_testing_standards.md"
    vol.write_text("# Testing\n\nEquivalence partitioning divides inputs into equivalence classes.\n\nBoundary value analysis tests values at the boundaries of valid ranges.\n\nTest cases require preconditions, steps, and expected results.")
    store.load(tmp_path)
    result = store.get_relevant_chunks("TEST_CASES", "login user story", max_chunks=3)
    assert isinstance(result, str)

def test_knowledge_store_empty_dir(tmp_path):
    store = KnowledgeStore()
    store.load(tmp_path)
    result = store.get_relevant_chunks("TEST_CASES", "any input")
    assert result == ""


# ── Prompt Assembly Tests ─────────────────────────────────────────────────────

def test_build_prompt_returns_tuple():
    system, user = build_prompt("TEST_CASES", "As a user I want to log in", quantity=2)
    assert isinstance(system, str)
    assert isinstance(user, str)
    assert len(system) > 50
    assert "2" in user

def test_build_prompt_all_types():
    for gen_type in GENERATION_LABELS.keys():
        system, user = build_prompt(gen_type, "Test input for validation", quantity=1)
        assert len(system) > 0
        assert len(user) > 0

def test_build_prompt_with_issue_context():
    context = {
        "key": "TEST-101",
        "summary": "User login feature",
        "description": "Users need to log in",
        "acceptance_criteria": "Given valid credentials, redirect to dashboard"
    }
    system, user = build_prompt("TEST_CASES", "login", quantity=1, issue_context=context)
    assert "TEST-101" in user
    assert "User login feature" in user

def test_batch_types_defined():
    assert "TEST_CASES" in BATCH_TYPES
    assert "BDD_SCENARIOS" in BATCH_TYPES
    assert "TEST_PLAN" not in BATCH_TYPES


# ── API Endpoint Tests ────────────────────────────────────────────────────────

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Verid-iq"

def test_generation_types_endpoint():
    response = client.get("/api/generation-types")
    assert response.status_code == 200
    data = response.json()
    assert "types" in data
    assert len(data["types"]) == 8
    keys = [t["key"] for t in data["types"]]
    assert "TEST_CASES" in keys
    assert "BDD_SCENARIOS" in keys

def test_web_index_serves():
    response = client.get("/")
    assert response.status_code == 200
    assert "Verid-iq" in response.text
    assert "Network Logic" in response.text

def test_terms_page_serves():
    response = client.get("/terms")
    assert response.status_code == 200
    assert "Terms of Service" in response.text

def test_privacy_page_serves():
    response = client.get("/privacy")
    assert response.status_code == 200
    assert "Privacy Policy" in response.text

def test_generate_endpoint_validates_input():
    response = client.post("/api/generate", json={
        "generation_type": "TEST_CASES",
        "input_text": "too short",
        "quantity": 1
    })
    assert response.status_code == 422

def test_generate_endpoint_validates_type():
    response = client.post("/api/generate", json={
        "generation_type": "INVALID_TYPE",
        "input_text": "A valid user story with enough content to pass validation",
        "quantity": 1
    })
    assert response.status_code == 422

def test_generate_endpoint_validates_quantity():
    response = client.post("/api/generate", json={
        "generation_type": "TEST_CASES",
        "input_text": "A valid user story with sufficient length for the validator",
        "quantity": 99
    })
    assert response.status_code == 422
