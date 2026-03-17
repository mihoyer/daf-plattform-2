"""
Datenbankmodell für DaF Sprachdiagnostik v2.
SQLite (async) – läuft neben der alten Plattform auf demselben Droplet.
"""
import json
import secrets
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


# ── Engine & Session ─────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Enums ────────────────────────────────────────────────────────────────────

class SessionStatus(str, PyEnum):
    offen = "offen"
    laufend = "laufend"
    abgeschlossen = "abgeschlossen"
    fehler = "fehler"


class ModulTyp(str, PyEnum):
    m1_lueckentext = "m1_lueckentext"
    m2_lesen = "m2_lesen"
    m3_hoerverstehen = "m3_hoerverstehen"
    m4_vorlesen = "m4_vorlesen"
    m5_sprechen = "m5_sprechen"
    m6_schreiben = "m6_schreiben"


class ModulStatus(str, PyEnum):
    ausstehend = "ausstehend"
    laufend = "laufend"
    abgeschlossen = "abgeschlossen"
    fehler = "fehler"
    uebersprungen = "uebersprungen"


# ── ORM-Modelle ──────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class TestSession(Base):
    """Anonyme Test-Session."""
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(String(20), nullable=False, default=SessionStatus.offen)
    grob_niveau: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)   # z.B. "A2.1"
    gesamt_niveau: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gesamt_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Skill-Scores als JSON: {"1_1": {"richtig": 3, "gesamt": 4, "prozent": 75}, ...}
    skill_scores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kandidat_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    abgeschlossen_am: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    module: Mapped[list["ModulErgebnis"]] = relationship(
        "ModulErgebnis", back_populates="session", cascade="all, delete-orphan"
    )

    def get_skill_scores(self) -> dict:
        if self.skill_scores_json:
            return json.loads(self.skill_scores_json)
        return {}

    def set_skill_scores(self, data: dict):
        self.skill_scores_json = json.dumps(data, ensure_ascii=False)

    def get_aktives_modul(self) -> Optional["ModulErgebnis"]:
        for m in self.module:
            if m.status == ModulStatus.laufend:
                return m
        return None

    def get_naechstes_modul(self) -> Optional["ModulErgebnis"]:
        for m in sorted(self.module, key=lambda x: x.reihenfolge):
            if m.status == ModulStatus.ausstehend:
                return m
        return None

    def alle_abgeschlossen(self) -> bool:
        return all(
            m.status in (ModulStatus.abgeschlossen, ModulStatus.uebersprungen, ModulStatus.fehler)
            for m in self.module
        )


class ModulErgebnis(Base):
    """Ergebnis eines einzelnen Test-Moduls."""
    __tablename__ = "modul_ergebnisse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_sessions.id"), nullable=False)
    modul: Mapped[str] = mapped_column(String(30), nullable=False)
    reihenfolge: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ModulStatus.ausstehend)
    schwierigkeitsgrad: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    roh_antworten_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ki_analyse_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cefr_niveau: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gesamt_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    audio_pfad: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    abgeschlossen_am: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["TestSession"] = relationship("TestSession", back_populates="module")

    def get_roh_antworten(self) -> dict:
        if self.roh_antworten_json:
            return json.loads(self.roh_antworten_json)
        return {}

    def set_roh_antworten(self, data: dict):
        self.roh_antworten_json = json.dumps(data, ensure_ascii=False)

    def get_ki_analyse(self) -> dict:
        if self.ki_analyse_json:
            return json.loads(self.ki_analyse_json)
        return {}

    def set_ki_analyse(self, data: dict):
        self.ki_analyse_json = json.dumps(data, ensure_ascii=False)


class KandidatenCode(Base):
    """Zugangscodes für Testgruppen."""
    __tablename__ = "kandidaten_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    max_nutzungen: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    genutzt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aktiv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notiz: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def ist_gueltig(self) -> bool:
        return self.aktiv and self.genutzt < self.max_nutzungen
