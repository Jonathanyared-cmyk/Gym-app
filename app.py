"""
Gym Log – Apple-Health-Look (Hell/Dunkel), Training & Körperdaten
Start:   streamlit run app.py
Bilder:  Ordner "bilder" neben dieser Datei, z. B. bilder/brustpresse.jpg
Daten:   trainingsdaten.csv, weight_data.csv, einstellungen.json (werden automatisch angelegt)
Braucht: streamlit >= 1.45 (siehe requirements.txt)
"""

import base64
import html
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ===============================================================
# 1) TRAININGSPLAN
#    Annahmen, wo Angaben fehlten: 2 Sätze à 6–8 W, Latzug 45 kg, Seitenheben 6 kg
#    "bildnamen" = weitere Schreibweisen, unter denen das Foto gefunden wird
# ===============================================================
TRAININGSPLAN = [
    {"gruppe": "Gruppe 1", "uebungen": [
        {"name": "Brustpresse", "tag": "A", "saetze": 2, "wdh": "6–8", "kg": 35},
        {"name": "Rudermaschine", "saetze": 2, "wdh": "6–8", "kg": 45},
        {"name": "Schulterpresse", "tag": "A", "saetze": 2, "wdh": "6–8", "kg": 30},
        {"name": "Butterfly", "saetze": 2, "wdh": "6–8", "kg": 30},
        {"name": "Trizepsmaschine", "saetze": 2, "wdh": "6–8", "kg": 50},
    ]},
    {"gruppe": "Gruppe 2", "uebungen": [
        {"name": "Latzug (Medium Wide Grip)", "saetze": 2, "wdh": "6–8", "kg": 45,
         "bildnamen": ["Lastzug (Medium Wide Trip)", "Latzug", "Lastzug"]},
        {"name": "Trizeps am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 20},
        {"name": "Bizepscurls am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 25},
        {"name": "Reverse Curls am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 15,
         "bildnamen": ["Reverse Curls am Kabetlturm"]},
        {"name": "Schulterheben am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 20},
        {"name": "Seitenheben mit Kurzhanteln", "saetze": 3, "wdh": "8–12", "kg": 6,
         "bildnamen": ["Hanteln Seitenheben", "Seitenheben"]},
    ]},
]
ALLE_UEBUNGEN = [dict(uebung, gruppe=block["gruppe"])
                 for block in TRAININGSPLAN for uebung in block["uebungen"]]
UEBUNG_NACH_NAME = {uebung["name"]: uebung for uebung in ALLE_UEBUNGEN}
GRUPPEN = [block["gruppe"] for block in TRAININGSPLAN]

# Aktivitätsfaktor (PAL) für den Kalorien-Gesamtbedarf
AKTIVITAETS_STUFEN = {"Wenig": 1.2, "Leicht": 1.375, "Mittel": 1.55, "Hoch": 1.725}
AKTIVITAETS_TEXT = {
    "Wenig": "Bürojob, kaum Sport", "Leicht": "1–2× Training pro Woche",
    "Mittel": "3–5× Training pro Woche", "Hoch": "6–7× Training pro Woche",
}

# ===============================================================
# 2) DATEIEN
# ===============================================================
APP_ORDNER = Path(__file__).resolve().parent
BILDER_ORDNER = APP_ORDNER / "bilder"
TRAINING_CSV = APP_ORDNER / "trainingsdaten.csv"
GEWICHT_CSV = APP_ORDNER / "weight_data.csv"
EINSTELLUNGEN_DATEI = APP_ORDNER / "einstellungen.json"
TRAINING_SPALTEN = ["Datum", "Uhrzeit", "Gruppe", "Uebung", "Gewicht_kg", "Wiederholungen"]
GEWICHT_SPALTEN = ["Datum", "Uhrzeit", "Gewicht_kg"]
BILD_ENDUNGEN = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}

# Annahmen für den ersten Start – danach merkt sich die App deine Werte
STANDARD_EINSTELLUNGEN = {
    "light_mode": False, "alter": 25, "groesse": 178, "geschlecht": "Männlich", "aktivitaet": "Mittel",
}

st.set_page_config(page_title="Gym Log", page_icon="🏋️", layout="centered",
                   initial_sidebar_state="collapsed")


# ===============================================================
# 3) EINSTELLUNGEN DAUERHAFT MERKEN
# ===============================================================
def einstellungen_laden() -> None:
    gespeichert = {}
    if EINSTELLUNGEN_DATEI.exists():
        try:
            gespeichert = json.loads(EINSTELLUNGEN_DATEI.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            gespeichert = {}
    if gespeichert.get("aktivitaet") not in AKTIVITAETS_STUFEN:   # alte Langnamen abfangen
        gespeichert.pop("aktivitaet", None)
    for schluessel, standardwert in STANDARD_EINSTELLUNGEN.items():
        if schluessel not in st.session_state:
            st.session_state[schluessel] = gespeichert.get(schluessel, standardwert)


def einstellungen_speichern() -> None:
    werte = {schluessel: st.session_state[schluessel] for schluessel in STANDARD_EINSTELLUNGEN}
    try:
        EINSTELLUNGEN_DATEI.write_text(json.dumps(werte, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass   # z. B. schreibgeschützte Cloud – dann gilt die Einstellung nur für diese Sitzung


einstellungen_laden()

# ===============================================================
# 4a) ICONS (SF Symbols aus dem Ordner "bilder")
#     Werden als CSS-Maske genutzt -> färben sich automatisch passend zu Hell/Dunkel.
#     Fehlt eine Datei, springt ein schlichtes Ersatz-Icon ein.
# ===============================================================
ERSATZ_ICONS = {
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<rect x="11" y="4" width="2" height="16" rx="1"/><rect x="4" y="11" width="16" height="2" rx="1"/></svg>',
    "minus": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
             '<rect x="4" y="11" width="16" height="2" rx="1"/></svg>',
    "dumbbell": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                '<rect x="1" y="9" width="2.5" height="6" rx="1"/><rect x="4" y="6.5" width="3.5" height="11" rx="1.2"/>'
                '<rect x="7.5" y="11" width="9" height="2" rx="1"/><rect x="16.5" y="6.5" width="3.5" height="11" rx="1.2"/>'
                '<rect x="20.5" y="9" width="2.5" height="6" rx="1"/></svg>',
}


def icon_ordner():
    """Ordner 'bilder' (oder 'Bilder') neben app.py."""
    if BILDER_ORDNER.is_dir():
        return BILDER_ORDNER
    for ordner in APP_ORDNER.iterdir():
        if ordner.is_dir() and ordner.name.lower() == "bilder":
            return ordner
    return None


@st.cache_data
def icon_als_data_uri(icon_name: str) -> str:
    """Liest bilder/<icon_name>.svg und gibt es als data:-URI für CSS zurück."""
    ordner = icon_ordner()
    svg_text = ERSATZ_ICONS[icon_name]
    if ordner is not None:
        for datei in ordner.iterdir():
            if datei.name.lower() == f"{icon_name}.svg":
                svg_text = datei.read_text(encoding="utf-8")
                break
    return "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode()


ICON_PLUS = icon_als_data_uri("plus")
ICON_MINUS = icon_als_data_uri("minus")
ICON_HANTEL = icon_als_data_uri("dumbbell")


def icon_html(data_uri: str, klasse: str = "icon") -> str:
    """Kleines Icon in der aktuellen Textfarbe (für HTML-Kacheln)."""
    return f'<span class="{klasse}" style="--icon: url(\'{data_uri}\')" aria-hidden="true"></span>'


# ===============================================================
# 4b) DESIGN: Farbpaletten + CSS
# ===============================================================
FARBEN_DUNKEL = {
    "bg": "#000000", "karte": "#1C1C1E", "feld": "#2C2C2E", "linie": "#2C2C2E",
    "segment": "#1C1C1E", "segment_an": "#636366",
    "text": "#FFFFFF", "grau": "#8E8E93", "schatten": "none",
}
FARBEN_HELL = {
    "bg": "#F2F2F7", "karte": "#FFFFFF", "feld": "#F2F2F7", "linie": "#E5E5EA",
    "segment": "#E3E3E8", "segment_an": "#FFFFFF",
    "text": "#000000", "grau": "#6C6C70",
    "schatten": "0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04)",
}
AKZENT = "#FF2D55"
farben = FARBEN_HELL if st.session_state["light_mode"] else FARBEN_DUNKEL

DESIGN_CSS = f"""
<style>
:root {{
    --bg: {farben["bg"]}; --karte: {farben["karte"]}; --feld: {farben["feld"]}; --linie: {farben["linie"]};
    --segment: {farben["segment"]}; --segment-an: {farben["segment_an"]};
    --text: {farben["text"]}; --grau: {farben["grau"]}; --schatten: {farben["schatten"]};
    --akzent: {AKZENT};
}}

/* ---------- Grundgerüst ---------- */
html, body, .stApp, .stApp * {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                 "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}
#MainMenu, header, footer {{ visibility: hidden; height: 0; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stHeader"] {{ display: none !important; }}

.stApp {{ background: var(--bg); }}
.stApp p, .stApp span, .stApp div, .stApp label {{ color: var(--text); }}
.block-container {{ max-width: 520px; padding: 12px 16px 64px !important; }}
[data-testid="stVerticalBlock"] {{ gap: 14px; }}
button {{ touch-action: manipulation; -webkit-tap-highlight-color: transparent; }}

/* ---------- Kopf ---------- */
.datum {{ color: var(--grau) !important; font-size: 13px; font-weight: 600; letter-spacing: .04em;
          text-transform: uppercase; margin: 0; }}
.titel {{ font-size: 34px; font-weight: 700; letter-spacing: -.025em; margin: 0; line-height: 1.15; }}
.abschnitt {{ font-size: 20px; font-weight: 700; letter-spacing: -.01em; margin: 18px 4px 0; }}
[data-testid="stToggle"] label p, [data-testid="stCheckbox"] label p {{
    color: var(--grau) !important; font-size: 14px !important; }}
.st-key-kopfzeile [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; align-items: center; }}
.st-key-kopfzeile [data-testid="stColumn"], .st-key-kopfzeile [data-testid="column"] {{ min-width: 0 !important; }}
.st-key-kopfzeile [data-testid="stColumn"]:last-child {{ flex: 0 0 auto !important; width: auto !important; }}

/* ---------- Karten (Widgets) ---------- */
[class*="st-key-karte"] {{
    background: var(--karte); border-radius: 16px; padding: 20px; box-shadow: var(--schatten);
}}
.karte {{ background: var(--karte); border-radius: 16px; padding: 20px; box-shadow: var(--schatten); }}
.kopf-label {{ color: var(--akzent) !important; font-size: 14px; font-weight: 600; margin: 0; }}
.kopf-name {{ font-size: 22px; font-weight: 700; letter-spacing: -.01em; margin: 2px 0 0; line-height: 1.25; }}
.kopf-ziel {{ color: var(--grau) !important; font-size: 15px; margin: 2px 0 0; }}
.trennlinie {{ height: 1px; background: var(--linie); margin: 2px 0; }}
.feld-label {{ color: var(--grau) !important; font-size: 13px; margin: 0; }}

/* ---------- iOS-Segmented-Control (Reiter, Gruppe, Geschlecht, Aktivität) ---------- */
[data-testid="stButtonGroup"] {{ width: 100%; }}
[data-testid="stButtonGroup"] > div {{ width: 100%; }}
[class*="st-key-segment"] [data-testid="stButtonGroup"] [role="radiogroup"],
[class*="st-key-segment"] [data-testid="stButtonGroup"] > div > div {{
    display: flex !important; width: 100%; flex-wrap: nowrap !important; gap: 0 !important;
    background: var(--segment); border-radius: 10px; padding: 2px;
}}
[class*="st-key-segment"] button {{
    flex: 1 1 0 !important; min-width: 0 !important; height: 36px; border: none !important;
    border-radius: 8px !important; background: transparent !important; box-shadow: none !important;
    transition: background .2s ease;
}}
[class*="st-key-segment"] button p {{ color: var(--text) !important; font-size: 14px !important;
    font-weight: 500 !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
[class*="st-key-segment"] button[kind$="Active"],
[class*="st-key-segment"] button[data-testid$="Active"] {{
    background: var(--segment-an) !important; box-shadow: 0 1px 4px rgba(0,0,0,.15) !important;
}}
[class*="st-key-segment"] button[kind$="Active"] p,
[class*="st-key-segment"] button[data-testid$="Active"] p {{ font-weight: 600 !important; }}

/* ---------- Übungs-Chips (große Daumen-Flächen) ---------- */
.st-key-uebung_auswahl [data-testid="stButtonGroup"] > div > div {{ flex-wrap: wrap !important; gap: 8px !important; }}
.st-key-uebung_auswahl button {{
    min-height: 44px; padding: 0 16px !important; border: none !important; border-radius: 22px !important;
    background: var(--feld) !important; box-shadow: none !important;
}}
.st-key-uebung_auswahl button p {{ color: var(--text) !important; font-size: 15px !important; }}
.st-key-uebung_auswahl button[kind$="Active"],
.st-key-uebung_auswahl button[data-testid$="Active"] {{ background: var(--text) !important; }}
.st-key-uebung_auswahl button[kind$="Active"] p,
.st-key-uebung_auswahl button[data-testid$="Active"] p {{ color: var(--karte) !important; font-weight: 600 !important; }}

/* ---------- Stepper: −  Wert  + (immer in einer Zeile) ---------- */
[class*="st-key-stepper"] [data-testid="stHorizontalBlock"] {{
    display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
    align-items: center !important; justify-content: space-between !important; gap: 12px !important;
}}
[class*="st-key-stepper"] [data-testid="stColumn"],
[class*="st-key-stepper"] [data-testid="column"] {{ min-width: 0 !important; width: auto !important; }}
[class*="st-key-stepper"] [data-testid="stColumn"]:first-child,
[class*="st-key-stepper"] [data-testid="stColumn"]:last-child,
[class*="st-key-stepper"] [data-testid="column"]:first-child,
[class*="st-key-stepper"] [data-testid="column"]:last-child {{ flex: 0 0 56px !important; }}
[class*="st-key-stepper"] [data-testid="stColumn"]:nth-child(2),
[class*="st-key-stepper"] [data-testid="column"]:nth-child(2) {{ flex: 1 1 auto !important; }}
[class*="st-key-stepper"] [data-testid="stElementContainer"],
[class*="st-key-stepper"] .stButton {{ width: auto !important; min-width: 0 !important; }}
[class*="st-key-stepper"] button {{
    position: relative; width: 56px !important; height: 56px !important; min-height: 56px; padding: 0 !important;
    border: none !important; border-radius: 50% !important; background: var(--feld) !important;
    box-shadow: none !important; transition: transform .1s ease;
}}
[class*="st-key-stepper"] button p {{ font-size: 0 !important; }}           /* Text "−"/"+" ausblenden */
[class*="st-key-stepper"] button::before {{                                  /* SF-Symbol einblenden   */
    content: ""; position: absolute; inset: 0; margin: auto; width: 22px; height: 22px;
    background-color: var(--text);
    -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat;
}}
[class*="st-key-minus_"] button {{ --icon: url("{ICON_MINUS}"); }}
[class*="st-key-plus_"] button {{ --icon: url("{ICON_PLUS}"); }}
[class*="st-key-stepper"] button:active {{ transform: scale(.92); }}

/* ---------- Icons in HTML-Kacheln ---------- */
.icon, .icon-gross {{
    display: inline-block; flex: none; width: 1.05em; height: 1.05em; vertical-align: -0.15em;
    background-color: currentColor;
    -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat;
}}
.icon {{ margin-right: 6px; }}
.icon-gross {{ width: 64px; height: 64px; }}

/* Hantel vor "Training" im Reiter */
.st-key-segment_reiter button:first-of-type p::before {{
    content: ""; display: inline-block; width: 1.1em; height: 1.1em; margin-right: 6px; vertical-align: -0.2em;
    background-color: var(--text);
    -webkit-mask: url("{ICON_HANTEL}") center / contain no-repeat; mask: url("{ICON_HANTEL}") center / contain no-repeat;
}}
.stepper-wert {{ text-align: center; line-height: 1.05; }}
.stepper-wert b {{ font-size: 36px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
.stepper-wert small {{ color: var(--grau) !important; font-size: 15px; font-weight: 500; margin-left: 4px; }}
.stepper-wert span {{ display: block; color: var(--grau) !important; font-size: 13px; margin-bottom: 2px; }}

/* ---------- Primär-Button (einziger Akzent) ---------- */
[class*="st-key-speichern"], [class*="st-key-speichern"] > div {{ width: 100% !important; }}
[class*="st-key-speichern"] button {{
    width: 100% !important; height: 54px; border: none !important; border-radius: 14px !important;
    background: var(--akzent) !important; box-shadow: none !important;
    transition: transform .1s ease, opacity .1s ease;
}}
[class*="st-key-speichern"] button p {{ color: #FFFFFF !important; font-size: 17px !important; font-weight: 600 !important; }}
[class*="st-key-speichern"] button:active {{ transform: scale(.97); opacity: .9; }}

/* ---------- Text-Button "Letzten Satz löschen" ---------- */
.st-key-letzten_loeschen button {{ background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 8px 4px !important; min-height: 44px; }}
.st-key-letzten_loeschen button p {{ color: var(--grau) !important; font-size: 15px !important; }}

/* ---------- Regler ---------- */
[data-testid="stSlider"] label p, [data-testid="stWidgetLabel"] p {{ color: var(--grau) !important; font-size: 13px !important; }}
[data-testid="stSlider"] [role="slider"] {{ width: 26px !important; height: 26px !important;
    background: #FFFFFF !important; box-shadow: 0 1px 4px rgba(0,0,0,.3) !important; }}
[data-testid="stSliderThumbValue"], [data-testid="stThumbValue"] {{ color: var(--text) !important; font-weight: 600; }}
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"],
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {{ display: none; }}

/* ---------- Maschinenfoto ---------- */
.foto {{ border-radius: 20px; overflow: hidden; aspect-ratio: 4 / 3; background: var(--karte); box-shadow: var(--schatten); }}
.foto img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.foto-leer {{ height: 100%; display: grid; place-content: center; justify-items: center; gap: 8px;
              color: var(--grau) !important; font-size: 13px; text-align: center; padding: 24px; line-height: 1.5; }}
.foto-leer b {{ color: var(--grau) !important; font-size: 40px; font-weight: 200; }}

/* ---------- Kennzahlen ---------- */
.karte-kopf {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 10px; }}
.karte-label {{ color: var(--akzent) !important; font-size: 14px; font-weight: 600; }}
.karte-zeit {{ color: var(--grau) !important; font-size: 13px; white-space: nowrap; }}
.gross {{ font-size: 40px; font-weight: 600; letter-spacing: -.025em; line-height: 1; font-variant-numeric: tabular-nums; }}
.gross small, .messwert small, .widget-wert small {{ color: var(--grau) !important; font-weight: 500; margin-left: 3px; letter-spacing: 0; }}
.gross small {{ font-size: 17px; }}
.unterzeile {{ color: var(--grau) !important; font-size: 14px; margin-top: 8px; }}
.verlaufslinie {{ width: 100%; height: 56px; display: block; margin-top: 16px; }}
.aufteilung {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border-top: 1px solid var(--linie);
               margin-top: 18px; padding-top: 14px; }}
.aufteilung span {{ display: block; color: var(--grau) !important; font-size: 13px; }}
.aufteilung b {{ font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.formel {{ color: var(--grau) !important; font-size: 12px !important; line-height: 1.6; margin: 14px 0 0;
           font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace !important; }}

.zusammenfassung {{ display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center; }}
.ring {{ width: 76px; height: 76px; border-radius: 50%; display: grid; place-items: center; }}
.ring-innen {{ width: 58px; height: 58px; border-radius: 50%; background: var(--karte); }}
.messwert {{ display: flex; justify-content: space-between; align-items: baseline; padding: 7px 0;
             border-bottom: 1px solid var(--linie); }}
.messwert:last-child {{ border-bottom: none; }}
.messwert span {{ color: var(--grau) !important; font-size: 14px; }}
.messwert b {{ font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.messwert small {{ font-size: 13px; }}

/* ---------- Verlauf als Widgets ---------- */
.widgets {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.widget {{ background: var(--karte); border-radius: 16px; padding: 16px; display: grid; gap: 14px;
           min-width: 0; box-shadow: var(--schatten); }}
.widget-kopf {{ display: flex; justify-content: space-between; gap: 8px; }}
.widget-name {{ font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.widget-zeit {{ color: var(--grau) !important; font-size: 13px; flex: none; }}
.widget-wert {{ font-size: 28px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
.widget-wert small {{ font-size: 14px; }}
.widget-info {{ color: var(--grau) !important; font-size: 13px; }}
.leer {{ background: var(--karte); border-radius: 16px; padding: 28px 20px; text-align: center;
         color: var(--grau) !important; font-size: 15px; line-height: 1.5; box-shadow: var(--schatten); }}

[data-testid="stToast"] {{ background: var(--karte) !important; border-radius: 14px !important; }}
@media (max-width: 360px) {{ .widgets {{ grid-template-columns: 1fr; }} }}
</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)


# ===============================================================
# 5) HILFSFUNKTIONEN
# ===============================================================
def zahl_format(wert: float, nachkommastellen=None) -> str:
    """80.0 -> '80', 82.5 -> '82,5' (oder feste Nachkommastellen)"""
    text = f"{wert:g}" if nachkommastellen is None else f"{wert:.{nachkommastellen}f}"
    return text.replace(".", ",")


def tausender(wert: float) -> str:
    return f"{wert:,.0f}".replace(",", ".")


def jetzt_datum_uhrzeit():
    jetzt = datetime.now()
    return jetzt.strftime("%Y-%m-%d"), jetzt.strftime("%H:%M")


def csv_laden(pfad: Path, spalten: list) -> pd.DataFrame:
    if not pfad.exists():
        return pd.DataFrame(columns=spalten)
    return pd.read_csv(pfad, encoding="utf-8")


def zeile_anhaengen(pfad: Path, zeile: dict) -> None:
    pd.DataFrame([zeile]).to_csv(pfad, mode="a", header=not pfad.exists(), index=False, encoding="utf-8")


# ---------- Bilder ----------
def vergleichs_name(text: str) -> str:
    """'Bizepscurls am Kabelturm' -> 'bizepscurlsamkabelturm' (Umlaute, Leerzeichen, _ und - egal)"""
    text = unicodedata.normalize("NFC", text).lower()
    for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, ersatz)
    return re.sub(r"[^a-z0-9]", "", text)


def beispiel_dateiname(name: str) -> str:
    ohne_klammer = re.sub(r"\(.*?\)", "", name).strip().lower()
    for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        ohne_klammer = ohne_klammer.replace(umlaut, ersatz)
    return re.sub(r"[^a-z0-9]+", "_", ohne_klammer).strip("_") + ".jpg"


def bilder_ordner_finden():
    """Ordner 'bilder' neben app.py – auch als 'Bilder' (Linux/Cloud unterscheidet Groß/Klein)."""
    if BILDER_ORDNER.is_dir():
        return BILDER_ORDNER
    for ordner in APP_ORDNER.iterdir():
        if ordner.is_dir() and ordner.name.lower() == "bilder":
            return ordner
    return None


def bild_pfad_finden(uebung: dict):
    ordner = bilder_ordner_finden()
    if ordner is None:
        return None
    gesuchte = [uebung["name"], re.sub(r"\(.*?\)", "", uebung["name"])] + uebung.get("bildnamen", [])
    gesuchte = {vergleichs_name(name) for name in gesuchte}
    for datei in sorted(ordner.iterdir()):
        if datei.suffix.lower() in BILD_ENDUNGEN and vergleichs_name(datei.stem) in gesuchte:
            return str(datei)
    return None


def foto_fehlt_hinweis(uebung: dict) -> str:
    ordner = bilder_ordner_finden()
    if ordner is None:
        return "Ordner „bilder“ nicht gefunden.<br>Er muss direkt neben app.py liegen."
    anzahl = sum(1 for datei in ordner.iterdir() if datei.suffix.lower() in BILD_ENDUNGEN)
    return f"Kein passendes Foto ({anzahl} Bilder im Ordner).<br>Erwartet: bilder/{beispiel_dateiname(uebung['name'])}"


@st.cache_data
def bild_als_html(pfad: str) -> str:
    datei = Path(pfad)
    daten = base64.b64encode(datei.read_bytes()).decode()
    return f'<img src="data:image/{BILD_ENDUNGEN[datei.suffix.lower()]};base64,{daten}" alt="">'


# ---------- Bausteine der Oberfläche ----------
def segment_control(optionen: list, zustand_key: str, widget_key: str, bei_aenderung=None, **zusatz):
    """iOS-Segmented-Control, das nie 'leer' werden kann (zweites Antippen hebt die Auswahl nicht auf)."""
    st.session_state[widget_key] = st.session_state[zustand_key]

    def uebernehmen():
        neuer_wert = st.session_state[widget_key]
        if neuer_wert is not None:
            st.session_state[zustand_key] = neuer_wert
            if bei_aenderung:
                bei_aenderung()

    with st.container(key=f"segment_{widget_key}"):
        st.segmented_control(widget_key, optionen, key=widget_key, on_change=uebernehmen,
                             label_visibility="collapsed", **zusatz)


def wert_aendern(feld: str, schritt: float, minimum: float, maximum: float, nachkommastellen: int) -> None:
    neuer_wert = st.session_state[feld] + schritt
    st.session_state[feld] = round(min(max(neuer_wert, minimum), maximum), 2)   # 2 Stellen: 37,5 bleibt 37,5


def stepper(feld: str, beschriftung: str, einheit: str, schritt: float,
            minimum: float, maximum: float, nachkommastellen: int = 0) -> None:
    """− Wert + in einer festen Zeile. Die Buttons sind 56 px groß (Daumen-tauglich)."""
    wert = st.session_state[feld]
    wert_text = zahl_format(wert, nachkommastellen) if nachkommastellen else zahl_format(wert)
    with st.container(key=f"stepper_{feld}"):
        spalte_minus, spalte_wert, spalte_plus = st.columns([1, 3, 1], vertical_alignment="center")
        with spalte_minus:
            st.button("−", key=f"minus_{feld}", on_click=wert_aendern,
                      args=(feld, -schritt, minimum, maximum, nachkommastellen))
        with spalte_wert:
            st.markdown(f'<div class="stepper-wert"><span>{beschriftung}</span>'
                        f'<b>{wert_text}</b><small>{einheit}</small></div>', unsafe_allow_html=True)
        with spalte_plus:
            st.button("+", key=f"plus_{feld}", on_click=wert_aendern,
                      args=(feld, schritt, minimum, maximum, nachkommastellen))


def trennlinie() -> None:
    st.markdown('<div class="trennlinie"></div>', unsafe_allow_html=True)


# ===============================================================
# 6) TRAINING: DATEN & LOGIK
# ===============================================================
def heutige_saetze_laden() -> pd.DataFrame:
    alle = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    return alle[alle["Datum"] == datetime.now().strftime("%Y-%m-%d")]


def saetze_erledigt(heute_df: pd.DataFrame, uebung_name: str) -> int:
    return int((heute_df["Uebung"] == uebung_name).sum())


def letztes_gewicht(uebung: dict) -> float:
    alle = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    saetze = alle[alle["Uebung"] == uebung["name"]]
    return float(uebung["kg"]) if saetze.empty else float(saetze["Gewicht_kg"].iloc[-1])


def uebung_waehlen(uebung_name: str) -> None:
    """Setzt Übung, passende Gruppe und Startwerte für Gewicht/Wiederholungen."""
    uebung = UEBUNG_NACH_NAME[uebung_name]
    st.session_state["aktuelle_uebung"] = uebung_name
    st.session_state["gruppe"] = uebung["gruppe"]
    st.session_state["gewicht"] = letztes_gewicht(uebung)
    st.session_state["wiederholungen"] = int(uebung["wdh"].split("–")[0])


def naechste_offene_uebung(heute_df: pd.DataFrame) -> str:
    for uebung in ALLE_UEBUNGEN:
        if saetze_erledigt(heute_df, uebung["name"]) < uebung["saetze"]:
            return uebung["name"]
    return ALLE_UEBUNGEN[0]["name"]


def bei_uebung_angetippt() -> None:
    neue_uebung = st.session_state["uebung_auswahl"]
    if neue_uebung is not None:
        uebung_waehlen(neue_uebung)


def bei_satz_speichern() -> None:
    uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]
    gewicht, wiederholungen = float(st.session_state["gewicht"]), int(st.session_state["wiederholungen"])
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(TRAINING_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gruppe": uebung["gruppe"],
                                   "Uebung": uebung["name"], "Gewicht_kg": gewicht,
                                   "Wiederholungen": wiederholungen})
    st.session_state["meldung"] = f"{uebung['name']} · {zahl_format(gewicht)} kg × {wiederholungen}"
    heute_df = heutige_saetze_laden()
    if saetze_erledigt(heute_df, uebung["name"]) >= uebung["saetze"]:
        uebung_waehlen(naechste_offene_uebung(heute_df))


def bei_letzten_satz_loeschen() -> None:
    alle = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    if not alle.empty:
        alle.iloc[:-1].to_csv(TRAINING_CSV, index=False, encoding="utf-8")
        st.session_state["meldung"] = "Letzter Satz gelöscht"


# ===============================================================
# 7) KÖRPERDATEN: DATEN & KALORIEN
# ===============================================================
def bei_koerpergewicht_speichern() -> None:
    gewicht = round(float(st.session_state["koerpergewicht"]), 1)
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(GEWICHT_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gewicht_kg": gewicht})
    st.session_state["meldung"] = f"Körpergewicht {zahl_format(gewicht, 1)} kg gespeichert"


def kalorienbedarf(gewicht_kg: float, groesse_cm: float, alter_jahre: int,
                   ist_maennlich: bool, aktivitaetsfaktor: float):
    """
    Mifflin-St. Jeor:
      Grundumsatz  = 10 × Gewicht(kg) + 6,25 × Größe(cm) − 5 × Alter(J) + 5    (Männer)
      Grundumsatz  = 10 × Gewicht(kg) + 6,25 × Größe(cm) − 5 × Alter(J) − 161  (Frauen)
      Gesamtbedarf = Grundumsatz × Aktivitätsfaktor
    """
    grundumsatz = 10 * gewicht_kg + 6.25 * groesse_cm - 5 * alter_jahre + (5 if ist_maennlich else -161)
    return grundumsatz, grundumsatz * aktivitaetsfaktor


def verlaufslinie_svg(werte: list) -> str:
    if len(werte) < 2:
        return ""
    kleinster, groesster = min(werte), max(werte)
    spanne = (groesster - kleinster) or 1
    punkte = [(6 + i * 288 / (len(werte) - 1), 50 - (w - kleinster) / spanne * 42) for i, w in enumerate(werte)]
    linie = " ".join(f"{x:.1f},{y:.1f}" for x, y in punkte)
    x_letzter, y_letzter = punkte[-1]
    return (f'<svg class="verlaufslinie" viewBox="0 0 300 56" preserveAspectRatio="none">'
            f'<polyline points="{linie}" fill="none" stroke="{AKZENT}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{x_letzter:.1f}" cy="{y_letzter:.1f}" r="3.5" fill="{AKZENT}"/></svg>')


# ===============================================================
# 8) STARTZUSTAND
# ===============================================================
heute_df = heutige_saetze_laden()
gewichte_df = csv_laden(GEWICHT_CSV, GEWICHT_SPALTEN)

if st.session_state.get("aktuelle_uebung") not in UEBUNG_NACH_NAME:
    uebung_waehlen(naechste_offene_uebung(heute_df))
if "bereich" not in st.session_state:
    st.session_state["bereich"] = "Training"
if "koerpergewicht" not in st.session_state:
    st.session_state["koerpergewicht"] = (float(gewichte_df["Gewicht_kg"].iloc[-1])
                                          if not gewichte_df.empty else 80.0)   # Annahme: 80 kg

if "meldung" in st.session_state:
    st.toast(st.session_state.pop("meldung"))

# ===============================================================
# 9) KOPF: Datum, Hell/Dunkel, Titel, Reiter
# ===============================================================
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
heute = datetime.now()

with st.container(key="kopfzeile"):
    spalte_datum, spalte_modus = st.columns([3, 1], vertical_alignment="center")
    with spalte_datum:
        st.markdown(f'<p class="datum">{WOCHENTAGE[heute.weekday()]}, {heute.day}. '
                    f'{MONATE[heute.month - 1]}</p>', unsafe_allow_html=True)
    with spalte_modus:
        st.toggle("Hell", key="light_mode", on_change=einstellungen_speichern)

st.markdown(f'<p class="titel">{st.session_state["bereich"]}</p>', unsafe_allow_html=True)
segment_control(["Training", "Körperdaten"], "bereich", "reiter")

# ===============================================================
# 10) REITER: TRAINING
# ===============================================================
if st.session_state["bereich"] == "Training":
    aktuelle_uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]

    # Foto der Maschine
    bild_pfad = bild_pfad_finden(aktuelle_uebung)
    if bild_pfad:
        st.markdown(f'<div class="foto">{bild_als_html(bild_pfad)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="foto"><div class="foto-leer">{icon_html(ICON_HANTEL, "icon-gross")}'
                    f'{foto_fehlt_hinweis(aktuelle_uebung)}</div></div>', unsafe_allow_html=True)

    # Übung wählen
    with st.container(key="karte_auswahl"):
        segment_control(GRUPPEN, "gruppe", "gruppen_auswahl")
        uebungen_der_gruppe = [u["name"] for u in ALLE_UEBUNGEN if u["gruppe"] == st.session_state["gruppe"]]
        st.session_state["uebung_auswahl"] = (st.session_state["aktuelle_uebung"]
                                              if st.session_state["aktuelle_uebung"] in uebungen_der_gruppe else None)

        def chip_text(name: str) -> str:
            fertig = saetze_erledigt(heute_df, name) >= UEBUNG_NACH_NAME[name]["saetze"]
            return f"✓ {name}" if fertig else name

        st.pills("Übung", uebungen_der_gruppe, key="uebung_auswahl", format_func=chip_text,
                 on_change=bei_uebung_angetippt, label_visibility="collapsed")

    # Satz eintragen
    with st.container(key="karte_satz"):
        satz_nummer = min(saetze_erledigt(heute_df, aktuelle_uebung["name"]) + 1, aktuelle_uebung["saetze"])
        tag_text = f' · {aktuelle_uebung["tag"]}' if aktuelle_uebung.get("tag") else ""
        st.markdown(f'<p class="kopf-label">{icon_html(ICON_HANTEL)}{aktuelle_uebung["gruppe"]}{tag_text}</p>'
                    f'<p class="kopf-name">{html.escape(aktuelle_uebung["name"])}</p>'
                    f'<p class="kopf-ziel">Satz {satz_nummer} von {aktuelle_uebung["saetze"]} · '
                    f'Ziel {aktuelle_uebung["wdh"]} Wiederholungen</p>', unsafe_allow_html=True)
        trennlinie()
        stepper("gewicht", "Gewicht", "kg", schritt=2.5, minimum=0, maximum=500, nachkommastellen=0)
        trennlinie()
        stepper("wiederholungen", "Wiederholungen", "", schritt=1, minimum=1, maximum=100)
        st.button("Satz speichern", key="speichern_satz", on_click=bei_satz_speichern)

    # Zusammenfassung
    geplant = sum(u["saetze"] for u in ALLE_UEBUNGEN)
    gezaehlt = sum(min(saetze_erledigt(heute_df, u["name"]), u["saetze"]) for u in ALLE_UEBUNGEN)
    fertig = sum(saetze_erledigt(heute_df, u["name"]) >= u["saetze"] for u in ALLE_UEBUNGEN)
    volumen_kg = float((heute_df["Gewicht_kg"] * heute_df["Wiederholungen"]).sum()) if not heute_df.empty else 0.0

    st.markdown(f"""
    <p class="abschnitt">Zusammenfassung</p>
    <div class="karte zusammenfassung">
      <div class="ring" style="background: conic-gradient({AKZENT} {gezaehlt / geplant * 360}deg, var(--feld) 0deg);">
        <div class="ring-innen"></div></div>
      <div>
        <div class="messwert"><span>Sätze</span><b>{gezaehlt}<small>/{geplant}</small></b></div>
        <div class="messwert"><span>Übungen fertig</span><b>{fertig}<small>/{len(ALLE_UEBUNGEN)}</small></b></div>
        <div class="messwert"><span>Volumen</span><b>{tausender(volumen_kg)}<small>kg</small></b></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Verlauf heute
    st.markdown('<p class="abschnitt">Verlauf heute</p>', unsafe_allow_html=True)
    if heute_df.empty:
        st.markdown('<div class="leer">Noch nichts eingetragen.<br>'
                    'Wähle eine Übung und speichere deinen ersten Satz.</div>', unsafe_allow_html=True)
    else:
        widgets_html = ""
        for uebung_name in dict.fromkeys(heute_df["Uebung"].iloc[::-1]):   # zuletzt trainiert zuerst
            saetze = heute_df[heute_df["Uebung"] == uebung_name]
            anzahl = len(saetze)
            wdh_liste = ", ".join(str(int(w)) for w in saetze["Wiederholungen"])
            widgets_html += (
                f'<div class="widget"><div class="widget-kopf">'
                f'<span class="widget-name"><span style="color: var(--akzent)">{icon_html(ICON_HANTEL)}</span>'
                f'{html.escape(str(uebung_name))}</span>'
                f'<span class="widget-zeit">{saetze["Uhrzeit"].iloc[-1]}</span></div>'
                f'<div><div class="widget-wert">{zahl_format(saetze["Gewicht_kg"].max())}<small>kg</small></div>'
                f'<div class="widget-info">{anzahl} {"Satz" if anzahl == 1 else "Sätze"} · {wdh_liste} W</div>'
                f'</div></div>')
        st.markdown(f'<div class="widgets">{widgets_html}</div>', unsafe_allow_html=True)
        st.button("Letzten Satz löschen", key="letzten_loeschen", on_click=bei_letzten_satz_loeschen)

# ===============================================================
# 11) REITER: KÖRPERDATEN
# ===============================================================
else:
    # Aktuelles Körpergewicht
    if gewichte_df.empty:
        gewicht_text, zeit_text, unterzeile, linie_html = "–", "", "Noch kein Gewicht gespeichert", ""
    else:
        letzter = gewichte_df.iloc[-1]
        gewicht_text = zahl_format(float(letzter["Gewicht_kg"]), 1)
        datum_obj = datetime.strptime(str(letzter["Datum"]), "%Y-%m-%d")
        zeit_text = (f"Heute, {letzter['Uhrzeit']}" if datum_obj.date() == heute.date()
                     else datum_obj.strftime("%d.%m.%Y"))
        if len(gewichte_df) > 1:
            differenz = float(letzter["Gewicht_kg"]) - float(gewichte_df.iloc[-2]["Gewicht_kg"])
            vorzeichen = "+" if differenz > 0 else ("−" if differenz < 0 else "±")
            unterzeile = f"{vorzeichen}{zahl_format(abs(differenz), 1)} kg seit letztem Eintrag"
        else:
            unterzeile = "Erster Eintrag"
        linie_html = verlaufslinie_svg(gewichte_df["Gewicht_kg"].astype(float).tail(14).tolist())

    st.markdown(f"""
    <div class="karte">
      <div class="karte-kopf"><span class="karte-label">Körpergewicht</span><span class="karte-zeit">{zeit_text}</span></div>
      <div class="gross">{gewicht_text}<small>kg</small></div>
      <div class="unterzeile">{unterzeile}</div>
      {linie_html}
    </div>""", unsafe_allow_html=True)

    # Gewicht eintragen
    with st.container(key="karte_gewicht"):
        st.markdown('<p class="kopf-name">Gewicht eintragen</p>'
                    '<p class="kopf-ziel">Am besten morgens, nüchtern</p>', unsafe_allow_html=True)
        trennlinie()
        stepper("koerpergewicht", "Körpergewicht", "kg", schritt=0.1, minimum=30, maximum=300, nachkommastellen=1)
        st.button("Gewicht speichern", key="speichern_gewicht", on_click=bei_koerpergewicht_speichern)

    # Kalorienbedarf
    st.markdown('<p class="abschnitt">Kalorienbedarf</p>', unsafe_allow_html=True)
    rechen_gewicht = (float(gewichte_df["Gewicht_kg"].iloc[-1]) if not gewichte_df.empty
                      else float(st.session_state["koerpergewicht"]))
    ist_maennlich = st.session_state["geschlecht"] == "Männlich"
    faktor = AKTIVITAETS_STUFEN[st.session_state["aktivitaet"]]
    grundumsatz, gesamtbedarf = kalorienbedarf(rechen_gewicht, st.session_state["groesse"],
                                               st.session_state["alter"], ist_maennlich, faktor)

    st.markdown(f"""
    <div class="karte">
      <div class="karte-kopf"><span class="karte-label">Täglicher Bedarf</span>
        <span class="karte-zeit">Heute</span></div>
      <div class="gross">{tausender(gesamtbedarf)}<small>kcal</small></div>
      <div class="aufteilung">
        <div><span>Grundumsatz</span><b>{tausender(grundumsatz)}<small> kcal</small></b></div>
        <div><span>Aktivität</span><b>{st.session_state["aktivitaet"]}</b></div>
      </div>
    </div>""", unsafe_allow_html=True)

    with st.container(key="karte_kalorien"):
        st.slider("Alter (Jahre)", min_value=14, max_value=80, key="alter", on_change=einstellungen_speichern)
        st.slider("Körpergröße (cm)", min_value=140, max_value=210, key="groesse", on_change=einstellungen_speichern)
        trennlinie()
        st.markdown('<p class="feld-label">Geschlecht</p>', unsafe_allow_html=True)
        segment_control(["Männlich", "Weiblich"], "geschlecht", "geschlecht_auswahl",
                        bei_aenderung=einstellungen_speichern)
        st.markdown(f'<p class="feld-label">Aktivität · {AKTIVITAETS_TEXT[st.session_state["aktivitaet"]]}</p>',
                    unsafe_allow_html=True)
        segment_control(list(AKTIVITAETS_STUFEN), "aktivitaet", "aktivitaet_auswahl",
                        bei_aenderung=einstellungen_speichern)
