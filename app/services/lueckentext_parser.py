"""
Lückentext-Parser: Liest die Lehrer-Markdown-Dateien und extrahiert
- den Schülertext (mit Lücken als _____)
- die Lösungstabelle mit Skill-Mapping
"""
import os
import re
import random
from pathlib import Path
from typing import Optional

from app.services.skill_mapping import grammatik_zu_modul_id, SCHRITTE_MODULE

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "lueckentexte"


def lade_alle_texte() -> list[dict]:
    """Lädt alle verfügbaren Lückentexte aus dem data-Verzeichnis."""
    texte = []
    lehrer_dateien = sorted(DATA_DIR.glob("*_lehrer.md"))

    for lehrer_datei in lehrer_dateien:
        # Schüler-Datei ableiten
        schueler_name = lehrer_datei.name.replace("_lehrer.md", "_schueler.md")
        schueler_datei = DATA_DIR / schueler_name

        if not schueler_datei.exists():
            continue

        text_data = parse_lehrer_datei(lehrer_datei)
        schueler_text = parse_schueler_datei(schueler_datei)

        if text_data and schueler_text:
            text_data["schueler_text_roh"] = schueler_text
            text_data["datei_id"] = lehrer_datei.stem.replace("_lehrer", "")
            texte.append(text_data)

    return texte


def parse_lehrer_datei(pfad: Path) -> Optional[dict]:
    """Parst eine Lehrer-Markdown-Datei und extrahiert Titel + Lösungstabelle."""
    try:
        inhalt = pfad.read_text(encoding="utf-8")
    except Exception:
        return None

    # Titel extrahieren
    titel_match = re.search(r"^#\s+(.+?)(?:\s*–.*)?$", inhalt, re.MULTILINE)
    titel = titel_match.group(1).strip() if titel_match else pfad.stem

    # Lösungstabelle parsen
    loesungen = []
    tabellen_zeilen = re.findall(r"^\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
                                  inhalt, re.MULTILINE)

    for zeile in tabellen_zeilen:
        nr, loesung, niveau, grammatik, quelle = zeile
        modul_id = grammatik_zu_modul_id(grammatik.strip(), niveau.strip())
        loesungen.append({
            "nr": int(nr),
            "loesung": loesung.strip(),
            "niveau": niveau.strip(),
            "grammatik": grammatik.strip(),
            "quelle": quelle.strip(),
            "modul_id": modul_id,
        })

    if not loesungen:
        return None

    return {
        "titel": titel,
        "loesungen": loesungen,
        "anzahl_luecken": len(loesungen),
    }


def parse_schueler_datei(pfad: Path) -> Optional[str]:
    """Liest den Schülertext aus der Markdown-Datei."""
    try:
        inhalt = pfad.read_text(encoding="utf-8")
        # Alles nach dem ersten --- (Trennlinie) nehmen
        teile = inhalt.split("---", 1)
        if len(teile) > 1:
            return teile[1].strip()
        # Fallback: alles nach dem Titel
        zeilen = inhalt.split("\n")
        text_zeilen = [z for z in zeilen if not z.startswith("#") and not z.startswith("**Aufgabe")]
        return "\n".join(text_zeilen).strip()
    except Exception:
        return None


def konvertiere_zu_html_luecken(schueler_text: str, loesungen: list[dict]) -> str:
    """
    Konvertiert den Schülertext in HTML mit Input-Feldern für jede Lücke.
    Die Lücken sind als X____ⁿ⁾ markiert (Anfangsbuchstabe + Unterstriche + hochgestellte Nummer).
    """
    html = schueler_text

    # Hochgestellte Ziffern → normale Ziffern
    HOCHGESTELLT = {"¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
                    "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁰": "0"}

    def ersetze_luecke(match):
        volltext = match.group(0)

        # Anfangsbuchstabe: erstes Zeichen
        anfang = volltext[0]

        # Nummer: alles nach dem letzten Unterstrich, ⁾ entfernen
        # Format: X___...___ⁿ⁾ (Buchstabe + Unterstriche + Zahl + ⁾)
        nr_teil = re.sub(r'^[a-zA-ZäöüÄÖÜ]_+', '', volltext).rstrip('⁾)')
        for h, n in HOCHGESTELLT.items():
            nr_teil = nr_teil.replace(h, n)
        try:
            nr = int(nr_teil)
        except ValueError:
            return volltext

        return (
            f'<span class="luecke-wrapper">'
            f'<input type="text" class="luecke-input" data-nr="{nr}" '
            f'placeholder="{anfang}___" maxlength="30" autocomplete="off" spellcheck="false">'
            f'</span>'
        )

    # Pattern: Buchstabe + 1+ Unterstriche + hochgestellte/normale Zahl(en) + ⁾
    pattern = r'[a-zA-Z\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc]_+[\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2070\d]+\u207e?'
    html = re.sub(pattern, ersetze_luecke, html)

    # Zeilenumbrüche in <br> konvertieren
    html = html.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html = f"<p>{html}</p>"

    return html


def waehle_zufaelligen_text() -> Optional[dict]:
    """Wählt einen zufälligen Lückentext aus dem Pool."""
    texte = lade_alle_texte()
    if not texte:
        return None
    return random.choice(texte)


def berechne_skill_scores(loesungen: list[dict], antworten: dict[str, str]) -> dict:
    """
    Berechnet den Score pro Schritte-Modul basierend auf den Antworten.

    Args:
        loesungen: Liste der Lösungsobjekte aus der Lehrerdatei
        antworten: Dict mit {"1": "bin", "2": "arbeite", ...}

    Returns:
        Dict mit Modul-Scores, Gesamt-Score und Niveau-Einschätzung
    """
    modul_richtig = {}
    modul_gesamt = {}
    gesamt_richtig = 0
    details = []

    for loesung in loesungen:
        nr = str(loesung["nr"])
        modul_id = loesung["modul_id"]
        korrekte_antwort = loesung["loesung"].lower().strip()
        eingabe = antworten.get(nr, "").lower().strip()

        # Tolerante Auswertung: Groß-/Kleinschreibung ignorieren
        ist_korrekt = (eingabe == korrekte_antwort)

        # Auch Teilübereinstimmungen akzeptieren (z.B. "geholfen" statt "geholfen.")
        if not ist_korrekt:
            ist_korrekt = (eingabe.rstrip(".,!?") == korrekte_antwort.rstrip(".,!?"))

        if modul_id not in modul_gesamt:
            modul_gesamt[modul_id] = 0
            modul_richtig[modul_id] = 0

        modul_gesamt[modul_id] += 1
        if ist_korrekt:
            modul_richtig[modul_id] += 1
            gesamt_richtig += 1

        details.append({
            "nr": loesung["nr"],
            "eingabe": antworten.get(nr, ""),
            "korrekt": loesung["loesung"],
            "ist_korrekt": ist_korrekt,
            "niveau": loesung["niveau"],
            "grammatik": loesung["grammatik"],
            "modul_id": modul_id,
        })

    # Prozentuale Scores pro Modul
    modul_scores = {}
    for modul_id in modul_gesamt:
        gesamt = modul_gesamt[modul_id]
        richtig = modul_richtig.get(modul_id, 0)
        modul_scores[modul_id] = {
            "richtig": richtig,
            "gesamt": gesamt,
            "prozent": round((richtig / gesamt) * 100) if gesamt > 0 else 0,
        }

    # Gesamt-Score
    gesamt_luecken = len(loesungen)
    gesamt_prozent = round((gesamt_richtig / gesamt_luecken) * 100) if gesamt_luecken > 0 else 0

    # Niveau-Einschätzung basierend auf Schritte-Modulen
    grob_niveau = _schaetze_niveau(modul_scores)

    return {
        "modul_scores": modul_scores,
        "gesamt_richtig": gesamt_richtig,
        "gesamt_luecken": gesamt_luecken,
        "gesamt_prozent": gesamt_prozent,
        "grob_niveau": grob_niveau,
        "details": details,
    }


def _schaetze_niveau(modul_scores: dict) -> str:
    """
    Schätzt das Sprachniveau basierend auf den Modul-Scores.
    Logik: Höchstes Modul mit >= 60% Richtigkeit.
    """
    # Reihenfolge der Module von hoch nach niedrig
    modul_reihenfolge = ["b2", "b1", "4_3", "4_2", "4_1", "3_3", "3_2", "3_1",
                          "2_3", "2_2", "2_1", "1_3", "1_2", "1_1"]

    niveau_mapping = {
        "b2": "B2", "b1": "B1",
        "4_3": "A2.2", "4_2": "A2.2", "4_1": "A2.2",
        "3_3": "A2.1", "3_2": "A2.1", "3_1": "A2.1",
        "2_3": "A1.2", "2_2": "A1.2", "2_1": "A1.2",
        "1_3": "A1.1", "1_2": "A1.1", "1_1": "A1.1",
    }

    for modul_id in modul_reihenfolge:
        if modul_id in modul_scores:
            if modul_scores[modul_id]["prozent"] >= 60:
                return niveau_mapping.get(modul_id, "A1.1")

    return "A1.1"
