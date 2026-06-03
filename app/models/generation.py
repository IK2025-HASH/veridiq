# Copyright © 2026 Network Logic Limited. All rights reserved.
# Generation-specific models only.
# User, Team, CreditTxn, Invoice live in app/models/user.py.

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserContext(Base):
    """Layer 1 — user-level context. Sensitive details never leave this layer."""
    __tablename__ = "user_context"

    id:              Mapped[uuid.UUID]      = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:         Mapped[uuid.UUID]      = mapped_column(Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False)
    team_id:         Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    generation_type: Mapped[str]            = mapped_column(String(50), nullable=False)
    feature_summary: Mapped[str | None]     = mapped_column(Text, nullable=True)
    artifact_pattern: Mapped[str | None]    = mapped_column(Text, nullable=True)
    is_classified:   Mapped[bool]           = mapped_column(Boolean, default=False)
    created_at:      Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)


class PlatformKnowledge(Base):
    """Layer 2 — anonymised platform knowledge. No PII, no names, no company data."""
    __tablename__ = "platform_knowledge"

    id:               Mapped[uuid.UUID]    = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_type:  Mapped[str]          = mapped_column(String(50), nullable=False, index=True)
    feature_category: Mapped[str | None]   = mapped_column(String(100), nullable=True, index=True)
    pattern_text:     Mapped[str]          = mapped_column(Text, nullable=False)
    quality_score:    Mapped[float]        = mapped_column(Float, default=0.7)
    usage_count:      Mapped[int]          = mapped_column(Integer, default=1)
    keywords:         Mapped[str | None]   = mapped_column(Text, nullable=True)
    source:           Mapped[str]          = mapped_column(String(20), default="interaction")
    created_at:       Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:       Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id:              Mapped[uuid.UUID]       = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:         Mapped[uuid.UUID | None]= mapped_column(Uuid(as_uuid=True), ForeignKey("user_accounts.id"), nullable=True)
    source:          Mapped[str]             = mapped_column(String(20), nullable=False)
    generation_type: Mapped[str]             = mapped_column(String(50), nullable=False)
    jira_issue_key:  Mapped[str | None]      = mapped_column(String(50), nullable=True)
    input_text:      Mapped[str | None]      = mapped_column(Text, nullable=True)
    quantity:        Mapped[int]             = mapped_column(Integer, default=1)
    status:          Mapped[str]             = mapped_column(String(20), default="pending")
    layer_used:      Mapped[str]             = mapped_column(String(10), default="layer3")
    credits_charged: Mapped[int]             = mapped_column(Integer, default=0)
    token_count:     Mapped[int | None]      = mapped_column(Integer, nullable=True)
    duration_ms:     Mapped[int | None]      = mapped_column(Integer, nullable=True)
    ip_address:      Mapped[str | None]      = mapped_column(String(50), nullable=True)
    created_at:      Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id:              Mapped[uuid.UUID]      = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id:          Mapped[uuid.UUID]      = mapped_column(Uuid(as_uuid=True), ForeignKey("generation_jobs.id"), nullable=False)
    artifact_index:  Mapped[int]            = mapped_column(Integer, default=1)
    generation_type: Mapped[str]            = mapped_column(String(50), nullable=False)
    title:           Mapped[str | None]     = mapped_column(String(500), nullable=True)
    content:         Mapped[str | None]     = mapped_column(Text, nullable=True)
    human_approved:  Mapped[bool]           = mapped_column(Boolean, default=False)
    approved_at:     Mapped[datetime | None]= mapped_column(DateTime, nullable=True)
    xray_issue_key:  Mapped[str | None]     = mapped_column(String(50), nullable=True)
    pushed_to_xray:  Mapped[bool]           = mapped_column(Boolean, default=False)
    created_at:      Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="artifacts")
