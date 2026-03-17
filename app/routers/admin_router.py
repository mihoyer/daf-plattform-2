"""Admin-Router für DaF-Plattform v2."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import KandidatenCode, TestSession, get_db

router = APIRouter(prefix="/admin")

ADMIN_SESSION_KEY = "daf_v2_admin"


def _check_admin(request: Request):
    if request.session.get(ADMIN_SESSION_KEY) != "ok":
        raise HTTPException(status_code=401, detail="Nicht autorisiert.")


@router.post("/api/login")
async def admin_login(
    request: Request,
    passwort: str = Form(...),
):
    if passwort == settings.admin_password:
        request.session[ADMIN_SESSION_KEY] = "ok"
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Falsches Passwort.")


@router.get("/api/sessions")
async def alle_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    _check_admin(request)
    result = await db.execute(
        select(TestSession)
        .options(selectinload(TestSession.module))
        .order_by(TestSession.erstellt_am.desc())
        .limit(100)
    )
    sessions = result.scalars().all()
    return [
        {
            "token": s.token,
            "status": s.status,
            "grob_niveau": s.grob_niveau,
            "kandidat_code": s.kandidat_code,
            "erstellt_am": s.erstellt_am.isoformat() if s.erstellt_am else None,
            "module_abgeschlossen": sum(1 for m in s.module if m.status == "abgeschlossen"),
            "module_gesamt": len(s.module),
        }
        for s in sessions
    ]


@router.get("/api/session/{token}")
async def session_detail(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    _check_admin(request)
    from app.services.session_service import lade_session
    sess = await lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    module_details = []
    for m in sorted(sess.module, key=lambda x: x.reihenfolge):
        module_details.append({
            "modul": m.modul,
            "status": m.status,
            "score": m.gesamt_score,
            "niveau": m.cefr_niveau,
            "ki_analyse": m.get_ki_analyse(),
        })

    return {
        "token": sess.token,
        "status": sess.status,
        "grob_niveau": sess.grob_niveau,
        "skill_scores": sess.get_skill_scores(),
        "kandidat_code": sess.kandidat_code,
        "erstellt_am": sess.erstellt_am.isoformat() if sess.erstellt_am else None,
        "module": module_details,
    }


@router.post("/api/codes/erstelle")
async def erstelle_codes(
    request: Request,
    anzahl: int = Form(20),
    max_nutzungen: int = Form(2),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    codes = []
    for i in range(anzahl):
        code = f"TG-{i+1:02d}-{secrets.token_hex(2).upper()}"
        kc = KandidatenCode(code=code, max_nutzungen=max_nutzungen)
        db.add(kc)
        codes.append(code)
    await db.commit()
    return {"codes": codes}


@router.get("/api/codes")
async def liste_codes(request: Request, db: AsyncSession = Depends(get_db)):
    _check_admin(request)
    result = await db.execute(select(KandidatenCode).order_by(KandidatenCode.erstellt_am.desc()))
    codes = result.scalars().all()
    return [
        {
            "code": c.code,
            "genutzt": c.genutzt,
            "max_nutzungen": c.max_nutzungen,
            "aktiv": c.aktiv,
        }
        for c in codes
    ]
