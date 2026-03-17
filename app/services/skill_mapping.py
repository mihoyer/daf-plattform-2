"""
Skill-Mapping: Ordnet Grammatikfokus-Angaben aus den Lückentexten
den 12 Modulen von Hueber Schritte plus Neu (Bände 1-4) zu.

Modul-IDs:
  1_1: Band 1, Modul 1 – Basis-Satzbau & Alltagskommunikation
  1_2: Band 1, Modul 2 – Artikel, Nomen & Personalpronomen
  1_3: Band 1, Modul 3 – Verben im Präsens & trennbare Verben
  2_1: Band 2, Modul 1 – Akkusativ & Satzklammer
  2_2: Band 2, Modul 2 – Perfekt – über Vergangenes sprechen
  2_3: Band 2, Modul 3 – Lokale & temporale Präpositionen
  3_1: Band 3, Modul 1 – Dativ & Verben mit Dativ
  3_2: Band 3, Modul 2 – Nebensätze (dass, weil, wenn, ob)
  3_3: Band 3, Modul 3 – Perfekt komplett & Präteritum von sein/haben
  4_1: Band 4, Modul 1 – Relativsätze
  4_2: Band 4, Modul 2 – Konjunktiv II & höfliche Kommunikation
  4_3: Band 4, Modul 3 – Infinitiv mit zu & indirekte Fragen
"""

# Vollständige Modul-Metadaten
SCHRITTE_MODULE = {
    "1_1": {
        "band": 1, "modul": 1,
        "titel": "Basis-Satzbau & Alltagskommunikation",
        "niveau": "A1.1",
        "lektionen": "1–3",
        "skills": ["Verb auf Position 2", "W-Fragen", "Ja/Nein-Fragen", "Imperativ (Sie-Form)"],
        "kurzbeschreibung": "Grundlegende Satzstrukturen und erste kommunikative Alltagssituationen.",
    },
    "1_2": {
        "band": 1, "modul": 2,
        "titel": "Artikel, Nomen & Personalpronomen",
        "niveau": "A1.1",
        "lektionen": "2–4",
        "skills": ["Bestimmter/unbestimmter Artikel (Nominativ)", "Pluralformen", "Personalpronomen", "Possessivartikel (mein/dein)"],
        "kurzbeschreibung": "Nominalformen sicher verwenden, Personen ansprechen und Objekte benennen.",
    },
    "1_3": {
        "band": 1, "modul": 3,
        "titel": "Verben im Präsens & trennbare Verben",
        "niveau": "A1.1",
        "lektionen": "4–6",
        "skills": ["Präsens regelmäßiger Verben", "sein/haben", "trennbare Verben (Grundprinzip)"],
        "kurzbeschreibung": "Alltägliche Handlungen und Tagesabläufe beschreiben.",
    },
    "2_1": {
        "band": 2, "modul": 1,
        "titel": "Akkusativ & Satzklammer",
        "niveau": "A1.2",
        "lektionen": "7–9",
        "skills": ["Akkusativartikel", "Modalverben + Infinitiv", "Satzklammer im Perfekt"],
        "kurzbeschreibung": "Vollständige Sätze mit Objekten und Modalverben bilden.",
    },
    "2_2": {
        "band": 2, "modul": 2,
        "titel": "Perfekt – über Vergangenes sprechen",
        "niveau": "A1.2",
        "lektionen": "9–11",
        "skills": ["Perfekt mit haben/sein", "Partizip II regelmäßig", "Partizip II unregelmäßig", "trennbare/untrennbare Verben im Perfekt"],
        "kurzbeschreibung": "Über Erlebnisse, Erfahrungen und vergangene Ereignisse sprechen.",
    },
    "2_3": {
        "band": 2, "modul": 3,
        "titel": "Lokale & temporale Präpositionen",
        "niveau": "A1.2",
        "lektionen": "7, 8, 12",
        "skills": ["in/an/auf (Wohin? Akkusativ)", "Zeitangaben (am/um/im)", "Wegbeschreibungen"],
        "kurzbeschreibung": "Orte, Bewegungen und Zeiten präzise ausdrücken.",
    },
    "3_1": {
        "band": 3, "modul": 1,
        "titel": "Dativ & Verben mit Dativ",
        "niveau": "A2.1",
        "lektionen": "13–15",
        "skills": ["Dativartikel", "Dativpronomen", "Dativverben (helfen, gefallen, …)", "Reflexivpronomen (Akkusativ)"],
        "kurzbeschreibung": "Komplexere Satzstrukturen mit zwei Objekten bilden und Feedback geben.",
    },
    "3_2": {
        "band": 3, "modul": 2,
        "titel": "Nebensätze – Gründe, Bedingungen, Informationen",
        "niveau": "A2.1",
        "lektionen": "14–17",
        "skills": ["Nebensatz mit dass", "Nebensatz mit weil", "Nebensatz mit wenn", "Nebensatz mit ob", "Nebensatzwortstellung"],
        "kurzbeschreibung": "Gründe, Bedingungen und indirekte Aussagen formulieren.",
    },
    "3_3": {
        "band": 3, "modul": 3,
        "titel": "Perfekt komplett & Präteritum von sein/haben",
        "niveau": "A2.1",
        "lektionen": "13, 14, 16",
        "skills": ["Perfekt unregelmäßiger Verben", "Präteritum sein", "Präteritum haben", "Präteritum Modalverben"],
        "kurzbeschreibung": "Über Biografie und Erfahrungen sprechen, Vergangenheitsformen sicher nutzen.",
    },
    "4_1": {
        "band": 4, "modul": 1,
        "titel": "Relativsätze – präzise beschreiben",
        "niveau": "A2.2",
        "lektionen": "18–20",
        "skills": ["Relativpronomen Nominativ/Akkusativ", "Relativpronomen Dativ", "Relativsätze zur Beschreibung"],
        "kurzbeschreibung": "Personen, Dinge und Orte präzise beschreiben.",
    },
    "4_2": {
        "band": 4, "modul": 2,
        "titel": "Konjunktiv II & höfliche Kommunikation",
        "niveau": "A2.2",
        "lektionen": "21–23",
        "skills": ["Konjunktiv II (würde + Infinitiv)", "Konjunktiv II (wäre)", "Konjunktiv II (hätte)", "höfliche Bitten und Wünsche"],
        "kurzbeschreibung": "Professionelle und soziale Kommunikationssituationen bewältigen.",
    },
    "4_3": {
        "band": 4, "modul": 3,
        "titel": "Infinitiv mit zu & indirekte Fragen",
        "niveau": "A2.2",
        "lektionen": "22–24",
        "skills": ["Infinitiv mit zu (um…zu / ohne…zu)", "indirekte Fragen", "komplexe Satzklammern"],
        "kurzbeschreibung": "Absichten, Ziele und komplexe Informationen ausdrücken.",
    },
}

# Mapping: Grammatikfokus-Schlüsselwörter → Modul-ID
# Reihenfolge ist wichtig: spezifischere Begriffe zuerst
GRAMMATIK_ZU_MODUL = [
    # Band 4
    ("infinitiv mit zu", "4_3"),
    ("um … zu", "4_3"),
    ("um...zu", "4_3"),
    ("ohne … zu", "4_3"),
    ("indirekte frage", "4_3"),
    ("satzklammer", "4_3"),
    ("konjunktiv ii (würde)", "4_2"),
    ("konjunktiv ii (wäre)", "4_2"),
    ("konjunktiv ii (hätte)", "4_2"),
    ("konjunktiv ii", "4_2"),
    ("würde", "4_2"),
    ("wäre", "4_2"),
    ("hätte", "4_2"),
    ("relativsatz im dativ", "4_1"),
    ("relativpronomen dativ", "4_1"),
    ("relativsatz", "4_1"),
    ("relativpronomen", "4_1"),
    # Band 3
    ("präteritum modalverben", "3_3"),
    ("präteritum starke verben", "3_3"),
    ("präteritum sein", "3_3"),
    ("präteritum haben", "3_3"),
    ("präteritum", "3_3"),
    ("passiv präteritum", "3_3"),
    ("nebensatz mit dass", "3_2"),
    ("nebensatz mit weil", "3_2"),
    ("nebensatz mit wenn", "3_2"),
    ("nebensatz mit ob", "3_2"),
    ("nebensätze mit dass", "3_2"),
    ("nebensätze mit weil", "3_2"),
    ("nebensätze mit wenn", "3_2"),
    ("nebensätze mit ob", "3_2"),
    ("kausalsatz", "3_2"),
    ("konditionalsatz", "3_2"),
    ("obwohl", "3_2"),
    ("dativverben", "3_1"),
    ("dativartikel", "3_1"),
    ("dativpronomen", "3_1"),
    ("reflexivpronomen", "3_1"),
    ("sich wenden", "3_1"),
    # Band 2
    ("partizip ii trennbar", "2_2"),
    ("partizip ii unregelmäßig", "2_2"),
    ("partizip ii regelmäßig", "2_2"),
    ("partizip ii", "2_2"),
    ("perfekt mit haben", "2_2"),
    ("perfekt mit sein", "2_2"),
    ("perfekt", "2_2"),
    ("akkusativartikel", "2_1"),
    ("akkusativ", "2_1"),
    ("modalverb im präteritum", "3_3"),  # Modalverb Präteritum → Band 3
    ("modalverb", "2_1"),
    ("wechselpräpositionen", "2_3"),
    ("lokale präpositionen", "2_3"),
    ("temporale präpositionen", "2_3"),
    ("präpositionen", "2_3"),
    # Band 1
    ("präsens trennbarer verben", "1_3"),
    ("präsens regelmäßiger verben", "1_3"),
    ("präsens unregelmäßiger verben", "1_3"),
    ("trennbare verben", "1_3"),
    ("präsens", "1_3"),
    ("personalpronomen", "1_2"),
    ("possessivartikel", "1_2"),
    ("artikel", "1_2"),
    ("nomen", "1_2"),
    ("plural", "1_2"),
    ("satzbau", "1_1"),
    ("w-frage", "1_1"),
    ("imperativ", "1_1"),
]

# Höhere Niveaus (B1, B2) → eigene Kategorie, nicht in Schritte-Modulen
B_NIVEAU_MODULE = {
    "B1": {
        "id": "b1",
        "titel": "B1-Strukturen (Goethe B1)",
        "niveau": "B1",
        "kurzbeschreibung": "Passiv, komplexe Relativsätze, Präteritum narrativ.",
    },
    "B2": {
        "id": "b2",
        "titel": "B2-Strukturen (telc B2)",
        "niveau": "B2",
        "kurzbeschreibung": "Nominalisierungen, Partizipialattribute, abstrakte Nomen.",
    },
}


def grammatik_zu_modul_id(grammatik_fokus: str, niveau: str) -> str:
    """
    Ordnet einen Grammatikfokus-String einem Schritte-Modul zu.
    Gibt die Modul-ID zurück (z.B. '2_2') oder 'b1'/'b2' für höhere Niveaus.
    """
    if niveau in ("B1", "B2", "C1", "C2"):
        return niveau.lower()

    fokus_lower = grammatik_fokus.lower()
    for schluessel, modul_id in GRAMMATIK_ZU_MODUL:
        if schluessel in fokus_lower:
            return modul_id

    # Fallback basierend auf Niveau
    niveau_fallback = {
        "A1.1": "1_3",
        "A1.2": "2_2",
        "A2.1": "3_2",
        "A2.2": "4_2",
    }
    return niveau_fallback.get(niveau, "1_3")


def get_modul_info(modul_id: str) -> dict:
    """Gibt die Metadaten zu einem Modul zurück."""
    if modul_id in SCHRITTE_MODULE:
        return SCHRITTE_MODULE[modul_id]
    if modul_id in ("b1", "b2"):
        niveau = modul_id.upper()
        return B_NIVEAU_MODULE.get(niveau, {})
    return {}
