"""OpenAI-Service für DaF-Plattform v2."""
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def transkribiere_audio(audio_pfad: str) -> str:
    """Transkribiert eine Audiodatei mit Whisper."""
    with open(audio_pfad, "rb") as f:
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",
        )
    return result.text


async def analysiere_sprache(
    transkription: str,
    aufgabe: str,
    skill_defizite: list[dict],
    modul: str,
) -> dict:
    """
    Analysiert eine Sprachproduktion (M5/M6) gezielt auf die Skill-Defizite aus M1.
    """
    defizit_liste = ", ".join([d["titel"] for d in skill_defizite[:5]]) if skill_defizite else "keine spezifischen Defizite"

    prompt = f"""Du bist DaF-Prüfer. Analysiere folgende Sprachproduktion eines Deutschlernenden.

Aufgabe: {aufgabe}
Transkription: {transkription}

Bekannte Defizite aus dem Lückentext-Test: {defizit_liste}

Prüfe GEZIELT, ob diese Strukturen korrekt verwendet werden.
Gib deine Analyse als JSON zurück:
{{
  "gesamt_score": 0-100,
  "cefr_niveau": "A1/A2/B1/B2",
  "staerken": ["...", "..."],
  "fehler": ["...", "..."],
  "defizit_bestaetigt": {{"modul_id": true/false}},
  "kommentar": "kurze Gesamteinschätzung"
}}"""

    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Du bist ein erfahrener DaF-Prüfer. Antworte nur mit JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=600,
    )
    import json
    return json.loads(response.choices[0].message.content)


async def generiere_lesetext(niveau: str, thema: str) -> dict:
    """Generiert einen Lesetext für M2 auf dem angegebenen Niveau."""
    import json, random

    themen_pool = {
        "A1": ["Alltag", "Familie", "Wohnen", "Einkaufen", "Freizeit"],
        "A2": ["Arbeit", "Reisen", "Gesundheit", "Nachbarschaft", "Kochen"],
        "B1": ["Umwelt", "Digitalisierung", "Bildung", "Integration", "Sport"],
        "B2": ["Gesellschaft", "Wirtschaft", "Kultur", "Wissenschaft", "Politik"],
    }

    if not thema:
        pool = themen_pool.get(niveau[:2], themen_pool["A2"])
        thema = random.choice(pool)

    prompt = f"""Erstelle einen kurzen deutschen Lesetext (150-200 Wörter) auf Niveau {niveau} zum Thema "{thema}".
Danach erstelle 3 Verständnisfragen mit je 4 Antwortoptionen (A-D), wobei genau eine korrekt ist.

Antworte NUR mit JSON:
{{
  "titel": "...",
  "text": "...",
  "fragen": [
    {{
      "frage": "...",
      "optionen": ["A: ...", "B: ...", "C: ...", "D: ..."],
      "korrekt": 0
    }}
  ]
}}"""

    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Du bist DaF-Prüfungsautor. Antworte nur mit JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=1000,
    )
    return json.loads(response.choices[0].message.content)


async def generiere_tts(text: str, ausgabe_pfad: str) -> bool:
    """Generiert TTS-Audio für M3."""
    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        with open(ausgabe_pfad, "wb") as f:
            f.write(response.content)
        return True
    except Exception:
        return False
