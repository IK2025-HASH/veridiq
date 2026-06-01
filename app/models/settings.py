# Copyright © 2026 Network Logic Limited. All rights reserved.
# Uses String(36) for the PK so this table works on both SQLite and PostgreSQL.

from sqlalchemy import Column, String, Text, DateTime
import uuid
from datetime import datetime
from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
