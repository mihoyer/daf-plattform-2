"""Session-Verwaltung für DaF-Plattform v2."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    KandidatenCode, ModulErgebnis, ModulStatus, ModulTyp,
    SessionStatus, TestSession,
)

# Alle Module in der neuen Reihenfolge
ALLE_MODULE = [
    ModulTyp.m1_lueckentext,
    ModulTyp.m2_lesen,
    ModulTyp.m3_hoerverstehen,
    ModulTyp.m4_vorlesen,
    ModulTyp.m5_sprechen,
    ModulTyp.m6_schreiben,
]


async def erstelle_session(db: AsyncSession, kandidat_code: Optional[str] = None) -> TestSession:
    """Erstellt eine neue Test-Session mit allen 6 Modulen."""
    token = secrets.token_urlsafe(32)
    sess = TestSession(
        token=token,
        status=SessionStatus.laufend,
        kandidat_code=kandidat_code,
    )
    db.add(sess)
    await db.flush()

    for i, modul_typ in enumerate(ALLE_MODULE):
        modul = ModulErgebnis(
            session_id=sess.id,
            modul=modul_typ.value,
            reihenfolge=i,
            status=ModulStatus.ausstehend,
        )
        db.add(modul)

    await db.commit()
    await db.refresh(sess)
    return sess


async def lade_session(db: AsyncSession, token: str) -> Optional[TestSession]:
    """Lädt eine Session mit allen Modulen."""
    result = await db.execute(
        select(TestSession)
        .options(selectinload(TestSession.module))
        .where(TestSession.token == token)
    )
    return result.scalar_one_or_none()


async def validiere_kandidaten_code(db: AsyncSession, code: str) -> Optional[KandidatenCode]:
    """Prüft ob ein Kandidatencode gültig ist."""
    result = await db.execute(
        select(KandidatenCode).where(KandidatenCode.code == code)
    )
    kc = result.scalar_one_or_none()
    if kc and kc.ist_gueltig():
        return kc
    return None
