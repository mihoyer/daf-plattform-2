"""
Haupt-Router: Alle API-Endpunkte der DaF-Plattform v2.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import (
    ModulErgebnis, ModulStatus, ModulTyp, SessionStatus, TestSession, get_db,
)
from app.services import m1_service, openai_service, session_service

router = APIRouter()

UPLOAD_DIR = "/tmp/daf_v2_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _get_modul(sess: TestSession, modul_typ: ModulTyp) -> Optional[ModulErgebnis]:
    for m in sess.module:
        if m.modul == modul_typ.value:
            return m
    return None


# ── Session ──────────────────────────────────────────────────────────────────

@router.post("/api/session/erstelle")
async def erstelle_session(
    kandidat_code: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Erstellt eine neue Test-Session."""
    # Kandidatencode validieren (optional)
    if kandidat_code:
        kc = await session_service.validiere_kandidaten_code(db, kandidat_code)
        if not kc:
            raise HTTPException(status_code=400, detail="Ungültiger oder bereits verwendeter Code.")
        kc.genutzt += 1
        await db.commit()

    sess = await session_service.erstelle_session(db, kandidat_code or None)
    return {"token": sess.token}


@router.get("/api/session/{token}/status")
async def session_status(token: str, db: AsyncSession = Depends(get_db)):
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")
    return {
        "token": sess.token,
        "status": sess.status,
        "grob_niveau": sess.grob_niveau,
        "module": [
            {"modul": m.modul, "status": m.status, "reihenfolge": m.reihenfolge}
            for m in sorted(sess.module, key=lambda x: x.reihenfolge)
        ],
    }


# ── M1: Progressiver Lückentext ──────────────────────────────────────────────

@router.get("/api/m1/{token}/text")
async def m1_text(token: str, db: AsyncSession = Depends(get_db)):
    """Lädt einen zufälligen Lückentext für M1."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    modul = _get_modul(sess, ModulTyp.m1_lueckentext)
    if not modul:
        raise HTTPException(status_code=404, detail="M1 nicht gefunden.")

    # Text laden
    text_data = m1_service.lade_text()
    if not text_data:
        raise HTTPException(status_code=500, detail="Kein Lückentext verfügbar.")

    # Lösungen im Modul speichern (nicht ans Frontend)
    modul.set_roh_antworten({
        "datei_id": text_data["datei_id"],
        "loesungen": text_data["_loesungen"],
        "antworten": {},
    })
    modul.status = ModulStatus.laufend
    await db.commit()

    return {
        "titel": text_data["titel"],
        "html_text": text_data["html_text"],
        "anzahl_luecken": text_data["anzahl_luecken"],
    }


@router.post("/api/m1/{token}/submit")
async def m1_submit(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Wertet die Antworten des Lückentexts aus.
    Body: {"antworten": {"1": "bin", "2": "arbeite", ...}}
    """
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    modul = _get_modul(sess, ModulTyp.m1_lueckentext)
    if not modul:
        raise HTTPException(status_code=404, detail="M1 nicht gefunden.")

    body = await request.json()
    antworten = body.get("antworten", {})

    cached = modul.get_roh_antworten()
    loesungen = cached.get("loesungen", [])

    if not loesungen:
        raise HTTPException(status_code=400, detail="Keine Lösungen gespeichert.")

    # Auswertung
    auswertung = m1_service.werte_aus(loesungen, antworten)

    # Ergebnisse speichern
    modul.set_ki_analyse(auswertung)
    modul.gesamt_score = auswertung["gesamt_prozent"]
    modul.cefr_niveau = auswertung["grob_niveau"]
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)

    # Skill-Scores in der Session speichern
    sess.grob_niveau = auswertung["grob_niveau"]
    sess.set_skill_scores(auswertung["modul_scores"])

    await db.commit()

    return {
        "gesamt_score": auswertung["gesamt_prozent"],
        "grob_niveau": auswertung["grob_niveau"],
        "modul_scores": auswertung["modul_scores"],
        "staerken": auswertung["staerken"],
        "defizite": auswertung["defizite"],
        "empfehlungen": auswertung["empfehlungen"],
        "details": auswertung["details"],
    }


# ── M2: Leseverstehen (adaptiv) ──────────────────────────────────────────────

@router.get("/api/m2/{token}/text")
async def m2_text(token: str, db: AsyncSession = Depends(get_db)):
    """Generiert einen Lesetext passend zum Niveau aus M1."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    modul = _get_modul(sess, ModulTyp.m2_lesen)
    if not modul:
        raise HTTPException(status_code=404, detail="M2 nicht gefunden.")

    # Niveau aus M1 übernehmen
    niveau = sess.grob_niveau or "A2"
    # Vereinfachen für GPT: A1.1 → A1, A2.2 → A2
    niveau_kurz = niveau[:2] if len(niveau) > 2 else niveau

    # Thema basierend auf Defiziten wählen
    skill_scores = sess.get_skill_scores()
    thema = ""

    lesetext = await openai_service.generiere_lesetext(niveau_kurz, thema)

    modul.set_roh_antworten({"lesetext": lesetext, "niveau": niveau_kurz})
    modul.status = ModulStatus.laufend
    modul.schwierigkeitsgrad = niveau_kurz
    await db.commit()

    return lesetext


@router.post("/api/m2/{token}/submit")
async def m2_submit(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Wertet die Antworten des Leseverstehens aus."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    modul = _get_modul(sess, ModulTyp.m2_lesen)
    if not modul:
        raise HTTPException(status_code=404, detail="M2 nicht gefunden.")

    body = await request.json()
    antworten = body.get("antworten", {})  # {"0": 2, "1": 0, "2": 3}

    cached = modul.get_roh_antworten()
    lesetext = cached.get("lesetext", {})
    fragen = lesetext.get("fragen", [])

    richtig = 0
    for i, frage in enumerate(fragen):
        gewaehlt = antworten.get(str(i), -1)
        if gewaehlt == frage.get("korrekt", -99):
            richtig += 1

    score = round((richtig / len(fragen)) * 100) if fragen else 0

    modul.gesamt_score = score
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)
    await db.commit()

    return {"score": score, "richtig": richtig, "gesamt": len(fragen)}


# ── M3: Hörverstehen ─────────────────────────────────────────────────────────

@router.get("/api/m3/{token}/audio")
async def m3_audio(token: str, db: AsyncSession = Depends(get_db)):
    """Generiert einen Hörtext und TTS-Audio für M3."""
    from fastapi.responses import FileResponse
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    modul = _get_modul(sess, ModulTyp.m3_hoerverstehen)
    if not modul:
        raise HTTPException(status_code=404, detail="M3 nicht gefunden.")

    niveau = sess.grob_niveau or "A2"
    niveau_kurz = niveau[:2] if len(niveau) > 2 else niveau

    # Hörtext generieren
    hoertext_data = await openai_service.generiere_lesetext(niveau_kurz, "")

    # TTS generieren
    audio_pfad = os.path.join(UPLOAD_DIR, f"m3_{token}.mp3")
    await openai_service.generiere_tts(hoertext_data.get("text", ""), audio_pfad)

    modul.set_roh_antworten({"hoertext": hoertext_data, "niveau": niveau_kurz})
    modul.audio_pfad = audio_pfad
    modul.status = ModulStatus.laufend
    modul.schwierigkeitsgrad = niveau_kurz
    await db.commit()

    return {
        "fragen": hoertext_data.get("fragen", []),
        "titel": hoertext_data.get("titel", ""),
        "audio_url": f"/api/m3/{token}/audio-datei",
    }


@router.get("/api/m3/{token}/audio-datei")
async def m3_audio_datei(token: str, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import FileResponse
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)
    modul = _get_modul(sess, ModulTyp.m3_hoerverstehen)
    if not modul or not modul.audio_pfad or not os.path.exists(modul.audio_pfad):
        raise HTTPException(status_code=404, detail="Audio nicht gefunden.")
    return FileResponse(modul.audio_pfad, media_type="audio/mpeg")


@router.post("/api/m3/{token}/submit")
async def m3_submit(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)
    modul = _get_modul(sess, ModulTyp.m3_hoerverstehen)
    if not modul:
        raise HTTPException(status_code=404)

    body = await request.json()
    antworten = body.get("antworten", {})

    cached = modul.get_roh_antworten()
    fragen = cached.get("hoertext", {}).get("fragen", [])

    richtig = sum(1 for i, f in enumerate(fragen) if antworten.get(str(i), -1) == f.get("korrekt", -99))
    score = round((richtig / len(fragen)) * 100) if fragen else 0

    modul.gesamt_score = score
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)
    await db.commit()

    return {"score": score, "richtig": richtig, "gesamt": len(fragen)}


# ── M4: Vorlesen ─────────────────────────────────────────────────────────────

@router.get("/api/m4/{token}/text")
async def m4_text(token: str, db: AsyncSession = Depends(get_db)):
    """Gibt einen Vorlesetext passend zum Niveau zurück."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m4_vorlesen)
    if not modul:
        raise HTTPException(status_code=404)

    niveau = sess.grob_niveau or "A2"
    niveau_kurz = niveau[:2] if len(niveau) > 2 else niveau

    texte = {
        "A1": "Ich heiße Anna. Ich wohne in Berlin. Ich arbeite als Lehrerin. Jeden Morgen trinke ich Kaffee.",
        "A2": "Gestern bin ich in die Stadt gefahren. Ich habe Freunde getroffen und wir haben zusammen gegessen. Das Wetter war schön.",
        "B1": "Obwohl es gestern geregnet hat, sind wir spazieren gegangen. Wir haben einen schönen Park gefunden, in dem viele Kinder gespielt haben.",
        "B2": "Die Digitalisierung verändert unsere Arbeitswelt grundlegend. Viele Berufe, die heute noch existieren, werden in zehn Jahren nicht mehr gefragt sein.",
    }

    text = texte.get(niveau_kurz, texte["A2"])
    modul.set_roh_antworten({"text": text, "niveau": niveau_kurz})
    modul.status = ModulStatus.laufend
    modul.schwierigkeitsgrad = niveau_kurz
    await db.commit()

    return {"text": text, "niveau": niveau_kurz}


@router.post("/api/m4/{token}/submit")
async def m4_submit(
    token: str,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Nimmt die Audioaufnahme entgegen und analysiert die Aussprache."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m4_vorlesen)
    if not modul:
        raise HTTPException(status_code=404)

    # Audio speichern
    suffix = ".mp4" if "mp4" in (audio.content_type or "") else ".webm"
    audio_pfad = os.path.join(UPLOAD_DIR, f"m4_{token}{suffix}")
    with open(audio_pfad, "wb") as f:
        f.write(await audio.read())

    # Transkribieren
    try:
        transkription = await openai_service.transkribiere_audio(audio_pfad)
    except Exception:
        transkription = ""

    cached = modul.get_roh_antworten()
    original_text = cached.get("text", "")

    # Einfacher Score: Wortübereinstimmung
    original_woerter = set(original_text.lower().split())
    transkription_woerter = set(transkription.lower().split())
    uebereinstimmung = len(original_woerter & transkription_woerter)
    score = round((uebereinstimmung / len(original_woerter)) * 100) if original_woerter else 0

    modul.set_ki_analyse({"transkription": transkription, "score": score})
    modul.gesamt_score = score
    modul.audio_pfad = audio_pfad
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)
    await db.commit()

    if settings.delete_audio_after_analysis:
        try:
            os.remove(audio_pfad)
        except Exception:
            pass

    return {"score": score, "transkription": transkription}


# ── M5: Freies Sprechen ──────────────────────────────────────────────────────

@router.get("/api/m5/{token}/aufgabe")
async def m5_aufgabe(token: str, db: AsyncSession = Depends(get_db)):
    """Gibt eine Sprechaufgabe passend zu den Defiziten aus M1 zurück."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m5_sprechen)
    if not modul:
        raise HTTPException(status_code=404)

    # Defizite aus M1 laden
    skill_scores = sess.get_skill_scores()
    defizite = [
        {"modul_id": mid, "titel": info.get("titel", mid)}
        for mid, data in skill_scores.items()
        if data.get("prozent", 100) < 50
        for info in [__import__("app.services.skill_mapping", fromlist=["get_modul_info"]).get_modul_info(mid)]
        if info
    ]

    # Aufgabe basierend auf Defiziten wählen
    aufgaben = {
        "2_2": "Erzählen Sie von Ihrem letzten Wochenende. Was haben Sie gemacht? Wo sind Sie gewesen?",
        "3_2": "Warum lernen Sie Deutsch? Erklären Sie Ihre Gründe und Ziele.",
        "3_1": "Beschreiben Sie eine Person, die Ihnen wichtig ist. Was gefällt Ihnen an dieser Person?",
        "4_2": "Was würden Sie tun, wenn Sie eine Woche frei hätten? Beschreiben Sie Ihre Wünsche.",
        "4_1": "Beschreiben Sie Ihre Traumwohnung. Was für eine Wohnung suchen Sie?",
    }

    aufgabe = "Erzählen Sie etwas über sich selbst: Woher kommen Sie, was machen Sie und warum lernen Sie Deutsch?"
    for defizit in defizite:
        mid = defizit["modul_id"]
        if mid in aufgaben:
            aufgabe = aufgaben[mid]
            break

    modul.set_roh_antworten({"aufgabe": aufgabe, "defizite": defizite})
    modul.status = ModulStatus.laufend
    await db.commit()

    return {"aufgabe": aufgabe}


@router.post("/api/m5/{token}/submit")
async def m5_submit(
    token: str,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Analysiert die Sprachproduktion in M5."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m5_sprechen)
    if not modul:
        raise HTTPException(status_code=404)

    suffix = ".mp4" if "mp4" in (audio.content_type or "") else ".webm"
    audio_pfad = os.path.join(UPLOAD_DIR, f"m5_{token}{suffix}")
    with open(audio_pfad, "wb") as f:
        f.write(await audio.read())

    try:
        transkription = await openai_service.transkribiere_audio(audio_pfad)
    except Exception:
        transkription = ""

    cached = modul.get_roh_antworten()
    aufgabe = cached.get("aufgabe", "")
    defizite = cached.get("defizite", [])

    # KI-Analyse mit Fokus auf Defizite
    try:
        analyse = await openai_service.analysiere_sprache(transkription, aufgabe, defizite, "m5")
    except Exception:
        analyse = {"gesamt_score": 50, "cefr_niveau": sess.grob_niveau or "A2", "kommentar": "Analyse nicht verfügbar."}

    modul.set_ki_analyse({**analyse, "transkription": transkription})
    modul.gesamt_score = analyse.get("gesamt_score", 50)
    modul.cefr_niveau = analyse.get("cefr_niveau", sess.grob_niveau)
    modul.audio_pfad = audio_pfad
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)
    await db.commit()

    if settings.delete_audio_after_analysis:
        try:
            os.remove(audio_pfad)
        except Exception:
            pass

    return {"score": modul.gesamt_score, "niveau": modul.cefr_niveau, "analyse": analyse}


# ── M6: Schreiben ─────────────────────────────────────────────────────────────

@router.get("/api/m6/{token}/aufgabe")
async def m6_aufgabe(token: str, db: AsyncSession = Depends(get_db)):
    """Gibt eine Schreibaufgabe passend zu den Defiziten zurück."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m6_schreiben)
    if not modul:
        raise HTTPException(status_code=404)

    skill_scores = sess.get_skill_scores()
    defizite = [
        mid for mid, data in skill_scores.items()
        if data.get("prozent", 100) < 50
    ]

    aufgaben = {
        "2_2": "Schreiben Sie eine kurze E-Mail an einen Freund und berichten Sie, was Sie letztes Wochenende gemacht haben (80-100 Wörter).",
        "3_2": "Schreiben Sie einen kurzen Text: Warum lernen Sie Deutsch? Nennen Sie mindestens zwei Gründe und erklären Sie diese (80-100 Wörter).",
        "4_2": "Schreiben Sie eine höfliche E-Mail an Ihren Kursleiter und bitten Sie um einen Termin für ein Gespräch (60-80 Wörter).",
        "3_1": "Schreiben Sie über eine Person, die Ihnen wichtig ist. Beschreiben Sie, wer diese Person ist und was Sie an ihr mögen (80-100 Wörter).",
    }

    aufgabe = "Schreiben Sie einen kurzen Text über sich selbst: Wer sind Sie, was machen Sie und warum lernen Sie Deutsch? (80-100 Wörter)"
    for mid in defizite:
        if mid in aufgaben:
            aufgabe = aufgaben[mid]
            break

    modul.set_roh_antworten({"aufgabe": aufgabe, "defizite": defizite})
    modul.status = ModulStatus.laufend
    await db.commit()

    return {"aufgabe": aufgabe}


@router.post("/api/m6/{token}/submit")
async def m6_submit(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Analysiert den geschriebenen Text."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404)

    modul = _get_modul(sess, ModulTyp.m6_schreiben)
    if not modul:
        raise HTTPException(status_code=404)

    body = await request.json()
    text = body.get("text", "")

    cached = modul.get_roh_antworten()
    aufgabe = cached.get("aufgabe", "")
    defizit_ids = cached.get("defizite", [])

    from app.services.skill_mapping import get_modul_info
    defizite = [{"modul_id": mid, "titel": get_modul_info(mid).get("titel", mid)} for mid in defizit_ids if get_modul_info(mid)]

    try:
        analyse = await openai_service.analysiere_sprache(text, aufgabe, defizite, "m6")
    except Exception:
        analyse = {"gesamt_score": 50, "cefr_niveau": sess.grob_niveau or "A2", "kommentar": "Analyse nicht verfügbar."}

    modul.set_ki_analyse({**analyse, "text": text})
    modul.gesamt_score = analyse.get("gesamt_score", 50)
    modul.cefr_niveau = analyse.get("cefr_niveau", sess.grob_niveau)
    modul.status = ModulStatus.abgeschlossen
    modul.abgeschlossen_am = datetime.now(timezone.utc)

    # Session abschließen
    sess.status = SessionStatus.abgeschlossen
    sess.abgeschlossen_am = datetime.now(timezone.utc)
    await db.commit()

    return {"score": modul.gesamt_score, "niveau": modul.cefr_niveau, "analyse": analyse}


# ── Ergebnis ──────────────────────────────────────────────────────────────────

@router.get("/api/ergebnis/{token}")
async def ergebnis(token: str, db: AsyncSession = Depends(get_db)):
    """Gibt das vollständige Testergebnis zurück."""
    sess = await session_service.lade_session(db, token)
    if not sess:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    # M1-Auswertung laden
    m1_modul = _get_modul(sess, ModulTyp.m1_lueckentext)
    m1_analyse = m1_modul.get_ki_analyse() if m1_modul else {}

    # Modul-Ergebnisse zusammenstellen
    modul_ergebnisse = []
    for m in sorted(sess.module, key=lambda x: x.reihenfolge):
        modul_ergebnisse.append({
            "modul": m.modul,
            "status": m.status,
            "score": m.gesamt_score,
            "niveau": m.cefr_niveau,
        })

    # Gesamtniveau berechnen
    abgeschlossene_scores = [m.gesamt_score for m in sess.module if m.gesamt_score is not None]
    gesamt_score = round(sum(abgeschlossene_scores) / len(abgeschlossene_scores)) if abgeschlossene_scores else 0

    return {
        "token": token,
        "grob_niveau": sess.grob_niveau,
        "gesamt_score": gesamt_score,
        "skill_scores": sess.get_skill_scores(),
        "empfehlungen": m1_analyse.get("empfehlungen", []),
        "staerken": m1_analyse.get("staerken", []),
        "defizite": m1_analyse.get("defizite", []),
        "module": modul_ergebnisse,
    }
