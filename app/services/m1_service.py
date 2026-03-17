"""
M1-Service: Progressiver Lückentext.

Ablauf:
1. lade_text()    → Zufälligen Text aus dem Pool wählen, HTML aufbereiten
2. werte_aus()    → Antworten auswerten, Skill-Scores berechnen
3. generiere_empfehlungen() → Kursempfehlungen basierend auf Skill-Scores
"""
from typing import Optional

from app.services.lueckentext_parser import (
    waehle_zufaelligen_text,
    konvertiere_zu_html_luecken,
    berechne_skill_scores,
)
from app.services.skill_mapping import SCHRITTE_MODULE, get_modul_info

# Schwellenwert für "bestanden" (in Prozent)
SCHWELLE_BEHERRSCHT = 70
SCHWELLE_DEFIZIT = 50


def lade_text() -> Optional[dict]:
    """
    Wählt einen zufälligen Lückentext und bereitet ihn für das Frontend auf.
    Gibt ein Dict mit HTML-Text, Metadaten und Lösungsschlüssel zurück.
    """
    text_data = waehle_zufaelligen_text()
    if not text_data:
        return None

    html_text = konvertiere_zu_html_luecken(
        text_data["schueler_text_roh"],
        text_data["loesungen"]
    )

    return {
        "titel": text_data["titel"],
        "html_text": html_text,
        "anzahl_luecken": text_data["anzahl_luecken"],
        "datei_id": text_data["datei_id"],
        # Lösungen werden NICHT ans Frontend gesendet
        "_loesungen": text_data["loesungen"],
    }


def werte_aus(loesungen: list[dict], antworten: dict[str, str]) -> dict:
    """
    Wertet die Antworten aus und berechnet das Skill-Profil.

    Args:
        loesungen: Lösungsliste aus lade_text()["_loesungen"]
        antworten: {"1": "bin", "2": "arbeite", ...}

    Returns:
        Vollständiges Auswertungs-Dict mit Skill-Scores und Empfehlungen
    """
    ergebnis = berechne_skill_scores(loesungen, antworten)
    ergebnis["empfehlungen"] = generiere_empfehlungen(ergebnis["modul_scores"])
    ergebnis["staerken"] = identifiziere_staerken(ergebnis["modul_scores"])
    ergebnis["defizite"] = identifiziere_defizite(ergebnis["modul_scores"])
    return ergebnis


def generiere_empfehlungen(modul_scores: dict) -> list[dict]:
    """
    Generiert konkrete Kursmodul-Empfehlungen basierend auf den Skill-Scores.
    Nur Module mit Score < SCHWELLE_DEFIZIT und mindestens 1 Lücke werden empfohlen.
    """
    empfehlungen = []

    # Reihenfolge: von A1.1 bis A2.2 (aufsteigend)
    modul_reihenfolge = ["1_1", "1_2", "1_3", "2_1", "2_2", "2_3",
                          "3_1", "3_2", "3_3", "4_1", "4_2", "4_3"]

    for modul_id in modul_reihenfolge:
        if modul_id not in modul_scores:
            continue
        score_data = modul_scores[modul_id]
        if score_data["gesamt"] == 0:
            continue

        modul_info = get_modul_info(modul_id)
        if not modul_info:
            continue

        prozent = score_data["prozent"]
        if prozent < SCHWELLE_DEFIZIT:
            prioritaet = "hoch"
        elif prozent < SCHWELLE_BEHERRSCHT:
            prioritaet = "mittel"
        else:
            continue  # Modul beherrscht, keine Empfehlung

        empfehlungen.append({
            "modul_id": modul_id,
            "titel": modul_info["titel"],
            "band": modul_info["band"],
            "modul_nr": modul_info["modul"],
            "niveau": modul_info["niveau"],
            "lektionen": modul_info["lektionen"],
            "kurzbeschreibung": modul_info["kurzbeschreibung"],
            "score_prozent": prozent,
            "prioritaet": prioritaet,
        })

    return empfehlungen


def identifiziere_staerken(modul_scores: dict) -> list[dict]:
    """Gibt Module zurück, die mit >= SCHWELLE_BEHERRSCHT% korrekt gelöst wurden."""
    staerken = []
    for modul_id, score_data in modul_scores.items():
        if score_data["gesamt"] == 0:
            continue
        if score_data["prozent"] >= SCHWELLE_BEHERRSCHT:
            modul_info = get_modul_info(modul_id)
            if modul_info:
                staerken.append({
                    "modul_id": modul_id,
                    "titel": modul_info.get("titel", modul_id),
                    "niveau": modul_info.get("niveau", ""),
                    "score_prozent": score_data["prozent"],
                })
    return sorted(staerken, key=lambda x: x["score_prozent"], reverse=True)


def identifiziere_defizite(modul_scores: dict) -> list[dict]:
    """Gibt Module zurück, die mit < SCHWELLE_DEFIZIT% gelöst wurden."""
    defizite = []
    for modul_id, score_data in modul_scores.items():
        if score_data["gesamt"] == 0:
            continue
        if score_data["prozent"] < SCHWELLE_DEFIZIT:
            modul_info = get_modul_info(modul_id)
            if modul_info:
                defizite.append({
                    "modul_id": modul_id,
                    "titel": modul_info.get("titel", modul_id),
                    "niveau": modul_info.get("niveau", ""),
                    "score_prozent": score_data["prozent"],
                })
    return sorted(defizite, key=lambda x: x["score_prozent"])
