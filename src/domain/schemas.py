"""Pydantic domain contracts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.domain.enums import LeadStatus


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TenantRead(DomainModel):
    id: UUID
    name: str
    slug: str
    status: str


class LeadCreate(DomainModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    source: str = Field(default="manual", max_length=100)
    owner_id: UUID | None = None


class LeadRead(DomainModel):
    id: UUID
    tenant_id: UUID
    first_name: str
    last_name: str
    email: str
    company: str | None
    industry: str | None
    source: str
    status: LeadStatus
    qualification_score: int
    created_at: datetime


class LeadUpdate(DomainModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    owner_id: UUID | None = None
    status: str | None = None
    qualification_score: int | None = Field(default=None, ge=0, le=100)
    next_follow_up_at: datetime | None = None


class LeadFilters(DomainModel):
    query: str = ""
    source: str | None = None
    industry: str | None = None
    company: str | None = None
    owner_id: str | None = None
    status: str | None = None
    min_score: int = Field(default=0, ge=0, le=100)
    max_score: int = Field(default=100, ge=0, le=100)
    created_from: date | None = None
    created_to: date | None = None
    next_follow_up_from: date | None = None
    next_follow_up_to: date | None = None
    sort: str = "created_at"
    direction: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
