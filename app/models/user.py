# Copyright © 2026 Network Logic Limited. All rights reserved.
# Separate user auth model to keep concerns clean

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class UserAccount(Base):
    """Full user account — auth + profile + credit management."""
    __tablename__ = "user_accounts"

    id:               Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:            Mapped[str]       = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password:  Mapped[str]       = mapped_column(String(255), nullable=False)
    display_name:     Mapped[str]       = mapped_column(String(100), nullable=False)
    avatar_url:       Mapped[str | None]= mapped_column(String(500), nullable=True)
    phone:            Mapped[str | None]= mapped_column(String(30), nullable=True)

    # Account type
    account_type:     Mapped[str]       = mapped_column(String(20), default="individual")  # individual|team_member|team_owner|admin
    tier:             Mapped[str]       = mapped_column(String(20), default="free")         # free|starter|team|growth|enterprise

    # Team
    team_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    team_role:        Mapped[str | None]       = mapped_column(String(20), nullable=True)  # owner|admin|member

    # Credits
    credit_balance:   Mapped[int]  = mapped_column(Integer, default=50)
    credits_used_month: Mapped[int]= mapped_column(Integer, default=0)
    credits_used_total: Mapped[int]= mapped_column(Integer, default=0)

    # Auth state
    email_verified:   Mapped[bool]      = mapped_column(Boolean, default=False)
    is_active:        Mapped[bool]      = mapped_column(Boolean, default=True)
    is_admin:         Mapped[bool]      = mapped_column(Boolean, default=False)
    classified_mode:  Mapped[bool]      = mapped_column(Boolean, default=False)

    # Billing
    billing_name:     Mapped[str | None]= mapped_column(String(255), nullable=True)
    billing_address:  Mapped[str | None]= mapped_column(Text, nullable=True)
    billing_vat:      Mapped[str | None]= mapped_column(String(50), nullable=True)
    company_name:     Mapped[str | None]= mapped_column(String(255), nullable=True)

    # Timestamps
    created_at:       Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow)
    last_login:       Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_active:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    team:             Mapped["Team | None"] = relationship("Team", back_populates="members")
    invoices:         Mapped[list["Invoice"]] = relationship("Invoice", back_populates="user")
    credit_txns:      Mapped[list["CreditTxn"]] = relationship("CreditTxn", back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id:                Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:              Mapped[str]       = mapped_column(String(255), nullable=False)
    slug:              Mapped[str]       = mapped_column(String(100), unique=True, nullable=False)
    description:       Mapped[str | None]= mapped_column(Text, nullable=True)
    owner_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tier:              Mapped[str]       = mapped_column(String(20), default="team")
    shared_credit_pool:Mapped[int]       = mapped_column(Integer, default=1000)
    credits_used_month:Mapped[int]       = mapped_column(Integer, default=0)
    classified_mode:   Mapped[bool]      = mapped_column(Boolean, default=False)
    max_members:       Mapped[int]       = mapped_column(Integer, default=10)
    created_at:        Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["UserAccount"]] = relationship("UserAccount", back_populates="team")
    invites: Mapped[list["TeamInvite"]]  = relationship("TeamInvite", back_populates="team")


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    email:      Mapped[str]       = mapped_column(String(255), nullable=False)
    role:       Mapped[str]       = mapped_column(String(20), default="member")
    token:      Mapped[str]       = mapped_column(String(255), unique=True, nullable=False)
    accepted:   Mapped[bool]      = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime]  = mapped_column(DateTime, nullable=False)

    team: Mapped["Team"] = relationship("Team", back_populates="invites")


class CreditTxn(Base):
    __tablename__ = "credit_transactions"

    id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False)
    team_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    amount:          Mapped[int]            = mapped_column(Integer, nullable=False)   # +add / -spend
    txn_type:        Mapped[str]            = mapped_column(String(30), nullable=False) # signup|topup|generation|refund|monthly_reset
    description:     Mapped[str | None]     = mapped_column(String(255), nullable=True)
    generation_type: Mapped[str | None]     = mapped_column(String(50), nullable=True)
    layer_used:      Mapped[str | None]     = mapped_column(String(10), nullable=True)
    balance_after:   Mapped[int]            = mapped_column(Integer, nullable=False)
    invoice_id:      Mapped[uuid.UUID | None]= mapped_column(UUID(as_uuid=True), nullable=True)
    created_at:      Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserAccount"] = relationship("UserAccount", back_populates="credit_txns")


class Invoice(Base):
    __tablename__ = "invoices"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number:  Mapped[str]       = mapped_column(String(50), unique=True, nullable=False)
    user_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False)
    team_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Billing details snapshot
    billing_name:    Mapped[str]        = mapped_column(String(255), nullable=False)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_vat:     Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name:    Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Line items
    description:     Mapped[str]        = mapped_column(String(500), nullable=False)
    credits_purchased: Mapped[int]      = mapped_column(Integer, nullable=False)
    amount_net:      Mapped[int]        = mapped_column(Integer, nullable=False)   # pence
    vat_rate:        Mapped[int]        = mapped_column(Integer, default=20)       # percent
    vat_amount:      Mapped[int]        = mapped_column(Integer, nullable=False)   # pence
    amount_gross:    Mapped[int]        = mapped_column(Integer, nullable=False)   # pence

    status:          Mapped[str]        = mapped_column(String(20), default="paid")
    payment_method:  Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_date:    Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    created_at:      Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserAccount"] = relationship("UserAccount", back_populates="invoices")
