"""Kandidaten-Router: Zugang über personalisierten Code."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services import session_service

router = APIRouter()


@router.get("/k/{code}")
async def kandidat_start(code: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Einstiegspunkt für Kandidaten via QR-Code.
    Validiert den Code und erstellt eine neue Session.
    """
    # Admin-Code: unbegrenzt
    if code == "ADMIN-MASTER-V2":
        sess = await session_service.erstelle_session(db, kandidat_code=code)
        return RedirectResponse(url=f"/test/{sess.token}", status_code=302)

    kc = await session_service.validiere_kandidaten_code(db, code)
    if not kc:
        return HTMLResponse(
            content="""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px">
            <h2>⚠️ Ungültiger Code</h2>
            <p>Dieser Code ist nicht gültig oder wurde bereits zu oft verwendet.</p>
            <p>Bitte wenden Sie sich an Ihre Kursleiterin / Ihren Kursleiter.</p>
            </body></html>
            """,
            status_code=400,
        )

    kc.genutzt += 1
    await db.commit()

    sess = await session_service.erstelle_session(db, kandidat_code=code)
    return RedirectResponse(url=f"/test/{sess.token}", status_code=302)
