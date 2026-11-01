"""
Gym Log – Apple-Health-Look mit Hell/Dunkel-Modus, Training und Körperdaten
Start:   streamlit run app.py
Bilder:  Ordner "bilder" neben dieser Datei, z. B. bilder/brustpresse.jpg
Daten:   trainingsdaten.csv, weight_data.csv, einstellungen.json (werden automatisch angelegt)
"""

import base64
import html
import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# Trainingsplan
# Annahmen, wo Angaben fehlten: 2 Sätze à 6–8 W, Latzug 45 kg, Seitenheben 6 kg
# "bildnamen" = weitere Schreibweisen, unter denen das Foto gefunden wird
# ---------------------------------------------------------------
TRAININGSPLAN = [
    {"gruppe": "Erste Gruppe", "uebungen": [
        {"name": "Brustpresse", "tag": "A", "saetze": 2, "wdh": "6–8", "kg": 35},
        {"name": "Rudermaschine", "saetze": 2, "wdh": "6–8", "kg": 45},
        {"name": "Schulterpresse", "tag": "A", "saetze": 2, "wdh": "6–8", "kg": 30},
        {"name": "Butterfly", "saetze": 2, "wdh": "6–8", "kg": 30},
        {"name": "Trizepsmaschine", "saetze": 2, "wdh": "6–8", "kg": 50},
    ]},
    {"gruppe": "Zweite Gruppe", "uebungen": [
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

# Aktivitätsfaktor (PAL) für den Gesamtbedarf
AKTIVITAETS_STUFEN = {
    "Wenig – Bürojob, kaum Sport": 1.2,
    "Leicht – 1–2× Training pro Woche": 1.375,
    "Mittel – 3–5× Training pro Woche": 1.55,
    "Hoch – 6–7× Training pro Woche": 1.725,
}

# ---------------------------------------------------------------
# Dateien
# ---------------------------------------------------------------
APP_ORDNER = os.path.dirname(os.path.abspath(__file__))
BILDER_ORDNER = os.path.join(APP_ORDNER, "bilder")
TRAINING_CSV = os.path.join(APP_ORDNER, "trainingsdaten.csv")
GEWICHT_CSV = os.path.join(APP_ORDNER, "weight_data.csv")
EINSTELLUNGEN_DATEI = os.path.join(APP_ORDNER, "einstellungen.json")
TRAINING_SPALTEN = ["Datum", "Uhrzeit", "Gruppe", "Uebung", "Gewicht_kg", "Wiederholungen"]
GEWICHT_SPALTEN = ["Datum", "Uhrzeit", "Gewicht_kg"]
BILD_ENDUNGEN = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}

# Annahmen für den ersten Start (danach merkt sich die App deine Werte)
STANDARD_EINSTELLUNGEN = {
    "light_mode": False, "alter": 25, "groesse": 178,
    "geschlecht": "Männlich", "aktivitaet": "Mittel – 3–5× Training pro Woche",
}

st.set_page_config(page_title="Gym Log", page_icon="🏋️", layout="centered",
                   initial_sidebar_state="collapsed")


# ---------------------------------------------------------------
# Einstellungen (Design, Alter, Größe ...) dauerhaft merken
# ---------------------------------------------------------------
def einstellungen_laden() -> None:
    gespeichert = {}
    if os.path.exists(EINSTELLUNGEN_DATEI):
        with open(EINSTELLUNGEN_DATEI, encoding="utf-8") as datei:
            gespeichert = json.load(datei)
    for schluessel, standardwert in STANDARD_EINSTELLUNGEN.items():
        if schluessel not in st.session_state:
            st.session_state[schluessel] = gespeichert.get(schluessel, standardwert)


def einstellungen_speichern() -> None:
    werte = {schluessel: st.session_state[schluessel] for schluessel in STANDARD_EINSTELLUNGEN}
    with open(EINSTELLUNGEN_DATEI, "w", encoding="utf-8") as datei:
        json.dump(werte, datei, ensure_ascii=False, indent=2)


einstellungen_laden()

# ---------------------------------------------------------------
# Apple-Health-Design: zwei Farbpaletten + gemeinsames CSS
# ---------------------------------------------------------------
FARBEN_DUNKEL = {
    "bg": "#000000", "karte": "#1C1C1E", "feld": "#2C2C2E", "linie": "#2C2C2E",
    "segment": "#1C1C1E", "segment_an": "#3A3A3C",
    "text": "#FFFFFF", "grau": "#8E8E93", "schatten": "none", "orange": "#FF9F0A",
}
FARBEN_HELL = {
    "bg": "#F2F2F7", "karte": "#FFFFFF", "feld": "#F2F2F7", "linie": "#E5E5EA",
    "segment": "#E3E3E8", "segment_an": "#FFFFFF",
    "text": "#000000", "grau": "#6C6C70", "orange": "#E08600",
    "schatten": "0 1px 3px rgba(0,0,0,.06), 0 6px 20px rgba(0,0,0,.05)",
}
AKZENT = "#FF2D55"   # Apple-Health-Pink, in beiden Modi gleich
farben = FARBEN_HELL if st.session_state["light_mode"] else FARBEN_DUNKEL

DESIGN_CSS = f"""
<style>
:root {{
    --bg: {farben["bg"]}; --karte: {farben["karte"]}; --feld: {farben["feld"]}; --linie: {farben["linie"]};
    --segment: {farben["segment"]}; --segment-an: {farben["segment_an"]};
    --text: {farben["text"]}; --grau: {farben["grau"]}; --schatten: {farben["schatten"]};
    --orange: {farben["orange"]}; --akzent: {AKZENT}; --akzent-weich: rgba(255,45,85,.16);
}}
html, body, .stApp, [class*="css"], input, button, label, p, h1, h2, h3, span, div {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                 "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}

/* Streamlit-Elemente ausblenden */
#MainMenu {{ visibility: hidden; }}
header {{ visibility: hidden; height: 0; }}
footer {{ visibility: hidden; height: 0; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none !important; }}

.stApp {{ background: var(--bg); color: var(--text); }}
.block-container {{ max-width: 560px; padding: 1.25rem 1rem 4rem; }}
[data-testid="stVerticalBlock"] {{ gap: 1rem; }}
.stApp p, .stApp span, .stApp div {{ color: var(--text); }}

/* Überschriften */
.datum {{ color: var(--grau) !important; font-size: 13px; font-weight: 600; text-transform: uppercase;
          letter-spacing: .06em; margin: 0; }}
.titel {{ color: var(--text); font-size: 34px; font-weight: 700; letter-spacing: -.02em; margin: 2px 0 0; padding: 0; }}
.abschnitt {{ color: var(--text); font-size: 22px; font-weight: 700; margin: 14px 0 0; }}

/* Design-Umschalter */
[data-testid="stToggle"] label p, [data-testid="stCheckbox"] label p {{
    color: var(--grau) !important; font-size: 13px !important; text-transform: none !important; letter-spacing: 0; }}

/* Reiter als iOS-Segmented-Control */
[data-baseweb="tab-list"] {{ background: var(--segment); border-radius: 10px; padding: 2px; gap: 0; }}
[data-baseweb="tab"] {{ flex: 1; justify-content: center; height: 38px; border-radius: 8px;
    background: transparent !important; }}
[data-baseweb="tab"][aria-selected="true"] {{ background: var(--segment-an) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.12); }}
[data-baseweb="tab"] p {{ color: var(--text) !important; font-size: 14px !important; font-weight: 500; }}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none; }}
[data-baseweb="tab-panel"] {{ padding-top: 1rem; }}

/* Maschinenbild */
.foto {{ border-radius: 20px; overflow: hidden; aspect-ratio: 4 / 3; background: var(--karte);
         box-shadow: var(--schatten); }}
.foto img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.foto-leer {{ height: 100%; display: grid; place-content: center; justify-items: center; gap: 10px;
              color: var(--grau) !important; font-size: 13px; text-align: center; padding: 20px; }}
.foto-leer b {{ color: var(--akzent); font-size: 44px; font-weight: 300; }}

/* Labels & Auswahlliste */
label, [data-testid="stWidgetLabel"] p {{ color: var(--grau) !important; font-size: 13px !important;
                                         font-weight: 400 !important; }}
[data-baseweb="select"] > div {{ background: var(--karte) !important; border: none !important;
    border-radius: 14px !important; min-height: 54px; box-shadow: var(--schatten); }}
[data-baseweb="select"] div, [data-baseweb="select"] span {{ color: var(--text) !important; font-size: 16px; }}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li {{ background: var(--karte) !important; color: var(--text) !important; }}

/* Karten-Formulare */
[data-testid="stForm"] {{ background: var(--karte); border: none !important; border-radius: 16px;
    padding: 20px; box-shadow: var(--schatten); }}
.kopf-label {{ color: var(--akzent) !important; font-size: 15px; font-weight: 600; margin: 0; }}
.kopf-name {{ color: var(--text); font-size: 24px; font-weight: 700; letter-spacing: -.01em; margin: 2px 0; }}
.kopf-ziel {{ color: var(--grau) !important; font-size: 15px; font-weight: 300; margin: 0 0 6px; }}

[data-testid="stNumberInput"] > div > div {{ background: var(--feld) !important; border: none !important;
    border-radius: 14px !important; overflow: hidden; }}
[data-testid="stNumberInput"] > div > div:focus-within {{ box-shadow: 0 0 0 2px var(--akzent); }}
[data-testid="stNumberInput"] input {{ height: 64px; background: var(--feld) !important; border: none !important;
    color: var(--text) !important; -webkit-text-fill-color: var(--text);
    font-size: 28px !important; font-weight: 300 !important; text-align: center; }}
[data-testid="stNumberInput"] button {{ height: 64px; min-width: 44px; background: var(--feld) !important;
    border: none !important; color: var(--akzent) !important; }}
[data-testid="stNumberInput"] button svg {{ fill: var(--akzent) !important; }}

/* Speichern-Buttons: flach, breit, federnd */
[data-testid="stFormSubmitButton"] button {{
    width: 100%; height: 56px; margin-top: 8px; border: none !important; border-radius: 14px !important;
    background: var(--akzent) !important; transition: transform .1s ease, opacity .1s ease;
}}
[data-testid="stFormSubmitButton"] button p {{ color: #FFFFFF !important; font-size: 17px !important; font-weight: 600 !important; }}
[data-testid="stFormSubmitButton"] button:active {{ transform: scale(.97); opacity: .9; }}

/* "Letzten Satz löschen" als Text-Button */
.stButton button {{ background: transparent !important; border: none !important; padding: 4px 0 !important; }}
.stButton button p {{ color: #FF453A !important; font-size: 15px !important; }}

/* Regler, Radio */
[data-testid="stSlider"] [data-testid="stThumbValue"] {{ color: var(--akzent) !important; }}
[data-testid="stSlider"] div[data-baseweb="slider"] > div > div {{ background: var(--linie); }}
[data-testid="stRadio"] [role="radiogroup"] label p {{ color: var(--text) !important; font-size: 15px !important; }}
.einstellungen-karte {{ background: var(--karte); border-radius: 16px; padding: 4px 20px 12px;
    box-shadow: var(--schatten); }}

/* Karten */
.karte {{ background: var(--karte); border-radius: 16px; padding: 20px; box-shadow: var(--schatten); }}
.karte-kopf {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 12px; }}
.karte-label {{ color: var(--akzent) !important; font-size: 15px; font-weight: 600; }}
.karte-label.orange {{ color: var(--orange) !important; }}
.karte-zeit {{ color: var(--grau) !important; font-size: 13px; }}
.gross {{ color: var(--text); font-size: 44px; font-weight: 600; letter-spacing: -.02em; line-height: 1;
          font-variant-numeric: tabular-nums; }}
.gross small, .messwert small, .widget-wert small {{ color: var(--grau) !important; font-weight: 500; margin-left: 3px; }}
.gross small {{ font-size: 18px; }}
.unterzeile {{ color: var(--grau) !important; font-size: 14px; margin-top: 6px; }}
.verlaufslinie {{ width: 100%; height: 64px; display: block; margin-top: 14px; }}
.aufteilung {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border-top: 1px solid var(--linie);
               margin-top: 16px; padding-top: 14px; }}
.aufteilung span {{ display: block; color: var(--grau) !important; font-size: 13px; }}
.aufteilung b {{ color: var(--text); font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.formel {{ color: var(--grau) !important; font: 12.5px/1.6 ui-monospace, "SF Mono", Menlo, Consolas, monospace !important;
           margin: 14px 0 0; }}

/* Zusammenfassung */
.zusammenfassung {{ display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center; }}
.ring {{ width: 84px; height: 84px; border-radius: 50%; display: grid; place-items: center; }}
.ring-innen {{ width: 64px; height: 64px; border-radius: 50%; background: var(--karte); }}
.messwert {{ display: flex; justify-content: space-between; align-items: baseline; padding: 8px 0;
             border-bottom: 1px solid var(--linie); }}
.messwert:last-child {{ border-bottom: none; }}
.messwert span {{ color: var(--grau) !important; font-size: 14px; }}
.messwert b {{ color: var(--text); font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.messwert small {{ font-size: 14px; }}

/* Verlauf als iOS-Widgets */
.widgets {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.widget {{ background: var(--karte); border-radius: 16px; padding: 16px; display: grid; gap: 14px; min-width: 0;
           box-shadow: var(--schatten); }}
.widget-kopf {{ display: flex; justify-content: space-between; gap: 8px; }}
.widget-name {{ color: var(--akzent) !important; font-size: 14px; font-weight: 600; overflow: hidden;
                text-overflow: ellipsis; white-space: nowrap; }}
.widget-zeit {{ color: var(--grau) !important; font-size: 13px; flex: none; }}
.widget-wert {{ color: var(--text); font-size: 30px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.widget-wert small {{ font-size: 15px; }}
.widget-info {{ color: var(--grau) !important; font-size: 13px; }}
.leer {{ background: var(--karte); border-radius: 16px; padding: 28px 20px; text-align: center;
         color: var(--grau) !important; font-size: 15px; line-height: 1.5; box-shadow: var(--schatten); }}

[data-testid="stToast"] {{ background: var(--karte) !important; color: var(--text) !important; }}
@media (max-width: 380px) {{ .widgets {{ grid-template-columns: 1fr; }} }}
</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------
def zahl_format(wert: float, nachkommastellen=None) -> str:
    """80.0 -> '80', 82.5 -> '82,5' (oder feste Nachkommastellen)"""
    text = f"{wert:g}" if nachkommastellen is None else f"{wert:.{nachkommastellen}f}"
    return text.replace(".", ",")


def tausender(wert: float) -> str:
    return f"{wert:,.0f}".replace(",", ".")


def vergleichs_name(text: str) -> str:
    """'Bizepscurls am Kabelturm' -> 'bizepscurlsamkabelturm'"""
    text = text.lower()
    for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, ersatz)
    return re.sub(r"[^a-z0-9]", "", text)


def beispiel_dateiname(name: str) -> str:
    ohne_klammer = re.sub(r"\(.*?\)", "", name).strip().lower()
    for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        ohne_klammer = ohne_klammer.replace(umlaut, ersatz)
    return re.sub(r"[^a-z0-9]+", "_", ohne_klammer).strip("_") + ".jpg"


def bild_pfad_finden(uebung: dict):
    """Sucht im Ordner 'bilder' ein Foto, dessen Name zur Übung passt."""
    if not os.path.isdir(BILDER_ORDNER):
        return None
    gesuchte_namen = [uebung["name"], re.sub(r"\(.*?\)", "", uebung["name"])] + uebung.get("bildnamen", [])
    gesuchte_namen = {vergleichs_name(name) for name in gesuchte_namen}
    for dateiname in sorted(os.listdir(BILDER_ORDNER)):
        stamm, endung = os.path.splitext(dateiname)
        if endung.lower() in BILD_ENDUNGEN and vergleichs_name(stamm) in gesuchte_namen:
            return os.path.join(BILDER_ORDNER, dateiname)
    return None


@st.cache_data
def bild_als_html(pfad: str) -> str:
    with open(pfad, "rb") as datei:
        daten = base64.b64encode(datei.read()).decode()
    bildtyp = BILD_ENDUNGEN[os.path.splitext(pfad)[1].lower()]
    return f'<img src="data:image/{bildtyp};base64,{daten}" alt="">'


def csv_laden(pfad: str, spalten: list) -> pd.DataFrame:
    if not os.path.exists(pfad):
        return pd.DataFrame(columns=spalten)
    return pd.read_csv(pfad, encoding="utf-8")


def zeile_anhaengen(pfad: str, zeile: dict) -> None:
    pd.DataFrame([zeile]).to_csv(pfad, mode="a", header=not os.path.exists(pfad),
                                 index=False, encoding="utf-8")


def jetzt_datum_uhrzeit():
    jetzt = datetime.now()
    return jetzt.strftime("%Y-%m-%d"), jetzt.strftime("%H:%M")


# ---------------------------------------------------------------
# Training: Daten & Logik
# ---------------------------------------------------------------
def heutige_saetze_laden() -> pd.DataFrame:
    alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    return alle_saetze[alle_saetze["Datum"] == datetime.now().strftime("%Y-%m-%d")]


def saetze_erledigt(heute_df: pd.DataFrame, uebung_name: str) -> int:
    return int((heute_df["Uebung"] == uebung_name).sum())


def letztes_gewicht(uebung: dict) -> float:
    alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    saetze_der_uebung = alle_saetze[alle_saetze["Uebung"] == uebung["name"]]
    if saetze_der_uebung.empty:
        return float(uebung["kg"])
    return float(saetze_der_uebung["Gewicht_kg"].iloc[-1])


def eingabe_vorbelegen(uebung_name: str) -> None:
    uebung = UEBUNG_NACH_NAME[uebung_name]
    st.session_state["gewicht"] = letztes_gewicht(uebung)
    st.session_state["wiederholungen"] = int(uebung["wdh"].split("–")[0])


def naechste_offene_uebung(heute_df: pd.DataFrame) -> str:
    for uebung in ALLE_UEBUNGEN:
        if saetze_erledigt(heute_df, uebung["name"]) < uebung["saetze"]:
            return uebung["name"]
    return ALLE_UEBUNGEN[0]["name"]


def bei_auswahl_geaendert() -> None:
    eingabe_vorbelegen(st.session_state["aktuelle_uebung"])


def bei_satz_speichern() -> None:
    uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]
    gewicht = float(st.session_state["gewicht"])
    wiederholungen = int(st.session_state["wiederholungen"])
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(TRAINING_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gruppe": uebung["gruppe"],
                                   "Uebung": uebung["name"], "Gewicht_kg": gewicht,
                                   "Wiederholungen": wiederholungen})
    st.session_state["meldung"] = f"{uebung['name']} · {zahl_format(gewicht)} kg × {wiederholungen}"

    heute_df = heutige_saetze_laden()
    if saetze_erledigt(heute_df, uebung["name"]) >= uebung["saetze"]:
        st.session_state["aktuelle_uebung"] = naechste_offene_uebung(heute_df)
        eingabe_vorbelegen(st.session_state["aktuelle_uebung"])


def letzten_satz_loeschen() -> None:
    alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    if not alle_saetze.empty:
        alle_saetze.iloc[:-1].to_csv(TRAINING_CSV, index=False, encoding="utf-8")


# ---------------------------------------------------------------
# Körperdaten: Daten & Kalorien
# ---------------------------------------------------------------
def gewichte_laden() -> pd.DataFrame:
    return csv_laden(GEWICHT_CSV, GEWICHT_SPALTEN)


def bei_koerpergewicht_speichern() -> None:
    gewicht = round(float(st.session_state["koerpergewicht_eingabe"]), 1)
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(GEWICHT_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gewicht_kg": gewicht})
    st.session_state["meldung"] = f"Körpergewicht {zahl_format(gewicht, 1)} kg gespeichert"


def kalorienbedarf(gewicht_kg: float, groesse_cm: float, alter_jahre: int,
                   ist_maennlich: bool, aktivitaetsfaktor: float):
    """
    Mifflin-St. Jeor:
      Grundumsatz = 10 × Gewicht(kg) + 6,25 × Größe(cm) − 5 × Alter(J) + 5   (Männer)
      Grundumsatz = 10 × Gewicht(kg) + 6,25 × Größe(cm) − 5 × Alter(J) − 161 (Frauen)
      Gesamtbedarf = Grundumsatz × Aktivitätsfaktor
    """
    geschlechts_wert = 5 if ist_maennlich else -161
    grundumsatz = 10 * gewicht_kg + 6.25 * groesse_cm - 5 * alter_jahre + geschlechts_wert
    gesamtbedarf = grundumsatz * aktivitaetsfaktor
    return grundumsatz, gesamtbedarf


def verlaufslinie_svg(werte: list) -> str:
    """Kleine Linie wie in Apple Health (letzte 14 Einträge)."""
    if len(werte) < 2:
        return ""
    kleinster, groesster = min(werte), max(werte)
    spanne = (groesster - kleinster) or 1
    punkte = [(6 + i * 288 / (len(werte) - 1), 56 - (w - kleinster) / spanne * 48) for i, w in enumerate(werte)]
    linie = " ".join(f"{x:.1f},{y:.1f}" for x, y in punkte)
    letzter_x, letzter_y = punkte[-1]
    return (f'<svg class="verlaufslinie" viewBox="0 0 300 64" preserveAspectRatio="none">'
            f'<polyline points="{linie}" fill="none" stroke="{AKZENT}" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{letzter_x:.1f}" cy="{letzter_y:.1f}" r="4" fill="{AKZENT}"/></svg>')


# ---------------------------------------------------------------
# Startzustand
# ---------------------------------------------------------------
heute_df = heutige_saetze_laden()
if st.session_state.get("aktuelle_uebung") not in UEBUNG_NACH_NAME:
    st.session_state["aktuelle_uebung"] = naechste_offene_uebung(heute_df)
    eingabe_vorbelegen(st.session_state["aktuelle_uebung"])

gewichte_df = gewichte_laden()
if "koerpergewicht_eingabe" not in st.session_state:
    st.session_state["koerpergewicht_eingabe"] = (float(gewichte_df["Gewicht_kg"].iloc[-1])
                                                  if not gewichte_df.empty else 80.0)   # Annahme: 80 kg

if "meldung" in st.session_state:
    st.toast(st.session_state.pop("meldung"), icon="✅")

# ---------------------------------------------------------------
# Kopf: Design-Umschalter + Titel
# ---------------------------------------------------------------
st.toggle("Apple Light Mode", key="light_mode", on_change=einstellungen_speichern)

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
heute = datetime.now()
st.markdown(f'<p class="datum">{WOCHENTAGE[heute.weekday()]}, {heute.day}. {MONATE[heute.month - 1]}</p>'
            f'<p class="titel">Training</p>', unsafe_allow_html=True)

reiter_training, reiter_koerper = st.tabs(["Training", "Körperdaten"])

# ===============================================================
# REITER 1: TRAINING
# ===============================================================
with reiter_training:
    aktuelle_uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]

    bild_pfad = bild_pfad_finden(aktuelle_uebung)
    if bild_pfad:
        st.markdown(f'<div class="foto">{bild_als_html(bild_pfad)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="foto"><div class="foto-leer"><b>+</b>Kein Foto gefunden.<br>'
                    f'Lege es ab als bilder/{beispiel_dateiname(aktuelle_uebung["name"])}</div></div>',
                    unsafe_allow_html=True)

    def anzeige_name(name: str) -> str:
        uebung = UEBUNG_NACH_NAME[name]
        haken = "✓ " if saetze_erledigt(heute_df, name) >= uebung["saetze"] else ""
        return f"{haken}{name}  ·  {uebung['gruppe']}"

    st.selectbox("Übung", options=[u["name"] for u in ALLE_UEBUNGEN], key="aktuelle_uebung",
                 format_func=anzeige_name, on_change=bei_auswahl_geaendert)

    with st.form("satz_formular"):
        satz_nummer = min(saetze_erledigt(heute_df, aktuelle_uebung["name"]) + 1, aktuelle_uebung["saetze"])
        tag_text = f' · {aktuelle_uebung["tag"]}' if aktuelle_uebung.get("tag") else ""
        st.markdown(f'<p class="kopf-label">{aktuelle_uebung["gruppe"]}{tag_text}</p>'
                    f'<p class="kopf-name">{html.escape(aktuelle_uebung["name"])}</p>'
                    f'<p class="kopf-ziel">Satz {satz_nummer} von {aktuelle_uebung["saetze"]} · '
                    f'Ziel {aktuelle_uebung["wdh"]} Wiederholungen</p>', unsafe_allow_html=True)
        spalte_gewicht, spalte_wdh = st.columns(2)
        with spalte_gewicht:
            st.number_input("Gewicht (kg)", min_value=0.0, max_value=500.0, step=2.5,
                            format="%.1f", key="gewicht")
        with spalte_wdh:
            st.number_input("Wiederholungen", min_value=1, max_value=100, step=1, key="wiederholungen")
        st.form_submit_button("Satz speichern", on_click=bei_satz_speichern)

    # Zusammenfassung
    geplante_saetze = sum(u["saetze"] for u in ALLE_UEBUNGEN)
    gezaehlte_saetze = sum(min(saetze_erledigt(heute_df, u["name"]), u["saetze"]) for u in ALLE_UEBUNGEN)
    fertige_uebungen = sum(saetze_erledigt(heute_df, u["name"]) >= u["saetze"] for u in ALLE_UEBUNGEN)
    winkel = gezaehlte_saetze / geplante_saetze * 360
    volumen_kg = float((heute_df["Gewicht_kg"] * heute_df["Wiederholungen"]).sum()) if not heute_df.empty else 0.0

    st.markdown(f"""
    <p class="abschnitt">Zusammenfassung</p>
    <div class="karte zusammenfassung">
      <div class="ring" style="background: conic-gradient({AKZENT} {winkel}deg, rgba(255,45,85,.16) 0deg);">
        <div class="ring-innen"></div>
      </div>
      <div>
        <div class="messwert"><span>Sätze</span><b>{gezaehlte_saetze}<small>/{geplante_saetze}</small></b></div>
        <div class="messwert"><span>Übungen fertig</span><b>{fertige_uebungen}</b></div>
        <div class="messwert"><span>Volumen</span><b>{tausender(volumen_kg)}<small>kg</small></b></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Verlauf heute als Widgets
    st.markdown('<p class="abschnitt">Verlauf heute</p>', unsafe_allow_html=True)
    if heute_df.empty:
        st.markdown('<div class="leer">Noch nichts eingetragen.<br>'
                    'Wähle oben eine Übung und speichere deinen ersten Satz.</div>', unsafe_allow_html=True)
    else:
        reihenfolge = list(dict.fromkeys(heute_df["Uebung"].iloc[::-1]))   # zuletzt trainiert zuerst
        widgets_html = ""
        for uebung_name in reihenfolge:
            saetze_der_uebung = heute_df[heute_df["Uebung"] == uebung_name]
            anzahl = len(saetze_der_uebung)
            wdh_liste = ", ".join(str(int(w)) for w in saetze_der_uebung["Wiederholungen"])
            widgets_html += f"""
            <div class="widget">
              <div class="widget-kopf"><span class="widget-name">{html.escape(str(uebung_name))}</span>
                <span class="widget-zeit">{saetze_der_uebung["Uhrzeit"].iloc[-1]}</span></div>
              <div><div class="widget-wert">{zahl_format(saetze_der_uebung["Gewicht_kg"].max())}<small>kg</small></div>
                <div class="widget-info">{anzahl} {"Satz" if anzahl == 1 else "Sätze"} · {wdh_liste} W</div></div>
            </div>"""
        st.markdown(f'<div class="widgets">{widgets_html}</div>', unsafe_allow_html=True)

        if st.button("Letzten Satz löschen"):
            letzten_satz_loeschen()
            st.rerun()

# ===============================================================
# REITER 2: KÖRPERDATEN
# ===============================================================
with reiter_koerper:
    # Kachel: aktuelles Körpergewicht
    if gewichte_df.empty:
        gewicht_text, zeit_text, unterzeile, linie_html = "–", "", "Noch kein Gewicht gespeichert", ""
    else:
        letzter = gewichte_df.iloc[-1]
        gewicht_text = zahl_format(float(letzter["Gewicht_kg"]), 1)
        datum_obj = datetime.strptime(letzter["Datum"], "%Y-%m-%d")
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
      <div class="karte-kopf"><span class="karte-label">♥ Körpergewicht</span><span class="karte-zeit">{zeit_text}</span></div>
      <div class="gross">{gewicht_text}<small>kg</small></div>
      <div class="unterzeile">{unterzeile}</div>
      {linie_html}
    </div>""", unsafe_allow_html=True)

    # Gewicht eintragen
    with st.form("gewicht_formular"):
        st.markdown('<p class="kopf-name">Gewicht eintragen</p>'
                    '<p class="kopf-ziel">Am besten morgens, nüchtern</p>', unsafe_allow_html=True)
        st.number_input("Körpergewicht (kg)", min_value=30.0, max_value=300.0, step=0.1,
                        format="%.1f", key="koerpergewicht_eingabe")
        st.form_submit_button("Gewicht speichern", on_click=bei_koerpergewicht_speichern)

    # Kalorienbedarf
    st.markdown('<p class="abschnitt">Kalorienbedarf</p>', unsafe_allow_html=True)

    rechen_gewicht = (float(gewichte_df["Gewicht_kg"].iloc[-1]) if not gewichte_df.empty
                      else float(st.session_state["koerpergewicht_eingabe"]))
    ist_maennlich = st.session_state["geschlecht"] == "Männlich"
    faktor = AKTIVITAETS_STUFEN[st.session_state["aktivitaet"]]
    grundumsatz, gesamtbedarf = kalorienbedarf(rechen_gewicht, st.session_state["groesse"],
                                               st.session_state["alter"], ist_maennlich, faktor)
    geschlechts_text = "+ 5" if ist_maennlich else "− 161"

    st.markdown(f"""
    <div class="karte">
      <div class="karte-kopf"><span class="karte-label orange">🔥 Täglicher Bedarf</span>
        <span class="karte-zeit">Mifflin-St. Jeor</span></div>
      <div class="gross">{tausender(gesamtbedarf)}<small>kcal</small></div>
      <div class="aufteilung">
        <div><span>Grundumsatz</span><b>{tausender(grundumsatz)} kcal</b></div>
        <div><span>Aktivitätsfaktor</span><b>{zahl_format(faktor)}</b></div>
      </div>
      <p class="formel">10 × {zahl_format(rechen_gewicht, 1)} + 6,25 × {st.session_state["groesse"]}
        − 5 × {st.session_state["alter"]} {geschlechts_text} = {tausender(grundumsatz)} kcal
        × {zahl_format(faktor)} = {tausender(gesamtbedarf)} kcal</p>
    </div>""", unsafe_allow_html=True)

    with st.container():
        st.slider("Alter (Jahre)", min_value=14, max_value=80, key="alter", on_change=einstellungen_speichern)
        st.slider("Körpergröße (cm)", min_value=140, max_value=210, key="groesse", on_change=einstellungen_speichern)
        st.radio("Geschlecht", ["Männlich", "Weiblich"], key="geschlecht", horizontal=True,
                 on_change=einstellungen_speichern)
        st.selectbox("Aktivität", list(AKTIVITAETS_STUFEN), key="aktivitaet", on_change=einstellungen_speichern)
