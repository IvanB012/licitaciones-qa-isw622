"""Modelos SQLAlchemy: TODAS las tablas del contrato §2.

Dinero: enteros en céntimos (CRC). Fechas: UTC aware (ver UTCDateTime). No hay borrado en cascada.
Los created_at no tienen default: los asigna el service con Clock.now() (REQ-007 desempate).
"""
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.rules.constants import (
    APPROVAL_LEVELS,
    RATE_SOURCES,
    ROLES,
    STATUS_BORRADOR,
    TENDER_STATUSES,
)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class UTCDateTime(TypeDecorator):
    """Guarda UTC (sin tz en SQLite) y devuelve siempre datetime aware en UTC. Rechaza datetimes naive."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime sin zona horaria: usar UTC aware (Clock.now())")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in_list("role", ROLES), name="ck_users_role"),
        # UNIQUE sin distinguir mayúsculas (contrato §2: "UNIQUE (casefold)")
        Index("uq_users_username_lower", text("lower(username)"), unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    offers: Mapped[list["Offer"]] = relationship(back_populates="provider", passive_deletes="all")


class Tender(Base):
    __tablename__ = "tenders"
    __table_args__ = (
        CheckConstraint("budget_cents > 0", name="ck_tenders_budget_positive"),
        CheckConstraint(_in_list("status", TENDER_STATUSES), name="ck_tenders_status"),
        CheckConstraint("length(trim(title)) > 0", name="ck_tenders_title_not_blank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    code_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closes_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=STATUS_BORRADOR, server_default=STATUS_BORRADOR
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    offers: Mapped[list["Offer"]] = relationship(back_populates="tender", passive_deletes="all")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("tender_id", "provider_id", name="uq_offers_tender_provider"),  # REQ-006
        CheckConstraint("amount_cents > 0", name="ck_offers_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    tender: Mapped[Tender] = relationship(back_populates="offers")
    provider: Mapped[Provider] = relationship(back_populates="offers")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate_x10000 > 0", name="ck_exchange_rates_rate_positive"),
        CheckConstraint(_in_list("source", RATE_SOURCES), name="ck_exchange_rates_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_x10000: Mapped[int] = mapped_column(Integer, nullable=False)  # CRC por USD x 10 000 (500,00 -> 5 000 000)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class ApprovalRange(Base):
    __tablename__ = "approval_ranges"
    __table_args__ = (
        CheckConstraint(_in_list("level", APPROVAL_LEVELS), name="ck_approval_ranges_level"),
        CheckConstraint("min_cents >= 1", name="ck_approval_ranges_min"),
        CheckConstraint("max_cents IS NULL OR max_cents > min_cents", name="ck_approval_ranges_max"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    min_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)  # inclusivo
    max_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # exclusivo; NULL = sin tope
