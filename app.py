"""
Gym Log – stabile Version im Apple-Health-/ESN-Look
Start:   streamlit run app.py
Ordner:  bilder/  -> Maschinenfotos + plus.svg, minus.svg
Daten:   trainingsdaten.csv, weight_data.csv, einstellungen.json (werden automatisch angelegt)
Design:  .streamlit/config.toml (dunkles Farbschema) + CSS unten

Nur eingebaute Streamlit-Elemente. Das CSS ändert ausschließlich das Aussehen:
Greift eine Regel nicht, sieht ein Element schlichter aus – die App läuft trotzdem.
"""

import base64
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# Trainingsplan
# Annahmen, wo Angaben fehlten: 2 Sätze à 6–8 W, Latzug 45 kg, Seitenheben 6 kg
# ---------------------------------------------------------------
TRAININGSPLAN = {
    "Gruppe 1": [
        {"name": "Brustpresse", "saetze": 2, "wdh": "6–8", "kg": 35.0},
        {"name": "Rudermaschine", "saetze": 2, "wdh": "6–8", "kg": 45.0},
        {"name": "Schulterpresse", "saetze": 2, "wdh": "6–8", "kg": 30.0},
        {"name": "Butterfly", "saetze": 2, "wdh": "6–8", "kg": 30.0},
        {"name": "Trizepsmaschine", "saetze": 2, "wdh": "6–8", "kg": 50.0},
    ],
    "Gruppe 2": [
        {"name": "Latzug (Medium Wide Grip)", "saetze": 2, "wdh": "6–8", "kg": 45.0,
         "bildnamen": ["Lastzug (Medium Wide Trip)", "Latzug", "Lastzug"]},
        {"name": "Trizeps am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 20.0},
        {"name": "Bizepscurls am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 25.0},
        {"name": "Reverse Curls am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 15.0,
         "bildnamen": ["Reverse Curls am Kabetlturm"]},
        {"name": "Schulterheben am Kabelturm", "saetze": 2, "wdh": "6–8", "kg": 20.0},
        {"name": "Seitenheben mit Kurzhanteln", "saetze": 3, "wdh": "8–12", "kg": 6.0,
         "bildnamen": ["Hanteln Seitenheben", "Seitenheben"]},
    ],
}
UEBUNGEN = {}
for gruppe, liste in TRAININGSPLAN.items():
    for uebung in liste:
        UEBUNGEN[uebung["name"]] = dict(uebung, gruppe=gruppe)

AKTIVITAETS_FAKTOR = 1.55          # "Sehr aktiv / 3-5x Gym pro Woche"
MUSKELAUFBAU_UEBERSCHUSS = 300     # kcal

BEREICH_TRAINING = "🏋️‍♂️ Training"
BEREICH_KOERPER = "📊 Körperdaten"

# ---------------------------------------------------------------
# Dateien
# ---------------------------------------------------------------
APP_ORDNER = Path(__file__).resolve().parent
TRAINING_CSV = APP_ORDNER / "trainingsdaten.csv"
GEWICHT_CSV = APP_ORDNER / "weight_data.csv"
EINSTELLUNGEN_DATEI = APP_ORDNER / "einstellungen.json"
TRAINING_SPALTEN = ["Datum", "Uhrzeit", "Gruppe", "Uebung", "Gewicht_kg", "Wiederholungen"]
GEWICHT_SPALTEN = ["Datum", "Uhrzeit", "Gewicht_kg"]
BILD_ENDUNGEN = (".jpg", ".jpeg", ".png", ".webp")

st.set_page_config(page_title="Gym Log", page_icon="🏋️", layout="centered")


# ---------------------------------------------------------------
# Hilfsfunktionen (alle mit Sicherheitsnetz – nie ein roter Fehler)
# ---------------------------------------------------------------
def bilder_ordner():
    try:
        return next((o for o in APP_ORDNER.iterdir() if o.is_dir() and o.name.lower() == "bilder"), None)
    except Exception:
        return None


def svg_icon(dateiname: str, ersatz_svg: str) -> str:
    """Liest bilder/<dateiname> als data:-URI für CSS. Fehlt die Datei, kommt ein schlichtes Ersatz-Icon."""
    svg_text = ersatz_svg
    try:
        ordner = bilder_ordner()
        if ordner is not None:
            for datei in ordner.iterdir():
                if datei.name.lower() == dateiname:
                    svg_text = datei.read_text(encoding="utf-8")
                    break
    except Exception:
        svg_text = ersatz_svg
    return "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode()


def csv_laden(pfad: Path, spalten: list) -> pd.DataFrame:
    try:
        if pfad.exists():
            daten = pd.read_csv(pfad, encoding="utf-8")
            if all(spalte in daten.columns for spalte in spalten):
                return daten[spalten]
    except Exception:
        pass
    return pd.DataFrame(columns=spalten)


def zeile_speichern(pfad: Path, zeile: dict) -> bool:
    try:
        pd.DataFrame([zeile]).to_csv(pfad, mode="a", header=not pfad.exists(), index=False, encoding="utf-8")
        return True
    except Exception:
        return False


def einstellungen_laden() -> dict:
    werte = {"alter": 25, "groesse": 178}    # Annahme für den ersten Start
    try:
        if EINSTELLUNGEN_DATEI.exists():
            gespeichert = json.loads(EINSTELLUNGEN_DATEI.read_text(encoding="utf-8"))
            werte["alter"] = int(gespeichert.get("alter", werte["alter"]))
            werte["groesse"] = int(gespeichert.get("groesse", werte["groesse"]))
    except Exception:
        pass
    return werte


def einstellungen_speichern(alter: int, groesse: int) -> None:
    try:
        EINSTELLUNGEN_DATEI.write_text(json.dumps({"alter": alter, "groesse": groesse}), encoding="utf-8")
    except Exception:
        pass


def vergleichs_name(text: str) -> str:
    """'Bizepscurls am Kabelturm' -> 'bizepscurlsamkabelturm' (Groß/Klein, Umlaute, Leerzeichen egal)"""
    text = unicodedata.normalize("NFC", text).lower()
    for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, ersatz)
    return re.sub(r"[^a-z0-9]", "", text)


def bild_finden(uebung: dict):
    try:
        ordner = bilder_ordner()
        if ordner is None:
            return None
        namen = [uebung["name"], re.sub(r"\(.*?\)", "", uebung["name"])] + uebung.get("bildnamen", [])
        gesucht = {vergleichs_name(name) for name in namen}
        for datei in sorted(ordner.iterdir()):
            if datei.suffix.lower() in BILD_ENDUNGEN and vergleichs_name(datei.stem) in gesucht:
                return str(datei)
    except Exception:
        return None
    return None


def zahl(wert: float) -> str:
    """80.0 -> '80', 82.5 -> '82,5'"""
    return f"{float(wert):g}".replace(".", ",")


def tausender(wert: float) -> str:
    return f"{int(wert):,}".replace(",", ".")


# ---------------------------------------------------------------
# Icons für die Stepper-Tasten
# ---------------------------------------------------------------
ICON_PLUS = svg_icon("plus.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                     '<rect x="11" y="4" width="2" height="16" rx="1"/><rect x="4" y="11" width="16" height="2" rx="1"/></svg>')
ICON_MINUS = svg_icon("minus.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                      '<rect x="4" y="11" width="16" height="2" rx="1"/></svg>')

# ---------------------------------------------------------------
# Design: Apple Health / ESN (nur CSS)
# ---------------------------------------------------------------
DESIGN_CSS = """
<style>
:root {
    --schwarz: #000000;
    --kachel: #1C1C1E;
    --feld: #2C2C2E;
    --linie: #38383A;
    --weiss: #FFFFFF;
    --grau: #8E8E93;
    --rot: #FF2D55;
    --schrift: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
               "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
}

/* ---------- Grundlagen ---------- */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDecoration"], [data-testid="stToolbar"] {display: none !important;}
.stApp {background-color: var(--schwarz) !important;}
.block-container {max-width: 560px; padding: 1.25rem 16px 3rem !important;}
[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"] {gap: 16px;}
.stApp *:not(svg):not(path) {box-shadow: none !important;}

/* ---------- Schrift ---------- */
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp h1, .stApp h2, .stApp h3,
.stApp li, [data-testid="stMarkdownContainer"], [data-baseweb="select"] div,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
    font-family: var(--schrift) !important;
    -webkit-font-smoothing: antialiased;
}
.stApp h1 {color: var(--weiss) !important; font-size: clamp(28px, 8vw, 34px) !important; font-weight: 700 !important;
           letter-spacing: -0.02em; padding: 0 !important;}
.stApp h2, .stApp h3 {color: var(--weiss) !important; font-size: clamp(19px, 5.5vw, 22px) !important;
                      font-weight: 700 !important; padding: 8px 0 0 !important;}

/* Nie abgehackt, nie mitten im Wort getrennt */
.stApp p, .stApp label, .stApp span, [data-testid="stMetricLabel"] *, [data-testid="stCaptionContainer"] * {
    white-space: normal !important; word-break: keep-all !important; overflow-wrap: break-word !important;
    overflow: visible !important; text-overflow: clip !important;
}
[data-testid="stWidgetLabel"] p, .stApp label p {
    color: var(--grau) !important; font-size: clamp(12px, 3.4vw, 13px) !important; font-weight: 500 !important;
}
[data-testid="stCaptionContainer"] p {color: var(--grau) !important; font-size: clamp(13px, 3.6vw, 14px) !important;}

/* ---------- Navigation: st.radio als iOS-Segmentanzeige ---------- */
.st-key-navigation [role="radiogroup"], [data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 0 !important;
    width: 100%; background: var(--kachel); border-radius: 10px; padding: 3px;
}
[data-testid="stRadio"] [role="radiogroup"] > label {
    flex: 1 1 0; min-width: 0; margin: 0 !important; padding: 8px 6px !important;
    justify-content: center; border-radius: 8px; cursor: pointer; transition: background 0.2s ease;
}
[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {display: none !important;}  /* Kreis weg */
[data-testid="stRadio"] [role="radiogroup"] > label p {
    color: var(--weiss) !important; font-size: clamp(14px, 4vw, 16px) !important; font-weight: 500 !important;
    text-align: center;
}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {background: #636366;}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {font-weight: 600 !important;}

/* ---------- Auswahlbox als Kachel ---------- */
[data-testid="stSelectbox"] {background: var(--kachel); border-radius: 12px !important; padding: 12px 16px 8px;}
[data-baseweb="select"] > div {
    background: var(--kachel) !important; border: none !important; border-radius: 12px !important;
    min-height: 44px; height: auto !important; padding-left: 0 !important;
}
[data-baseweb="select"] > div > div:first-child {padding-left: 0 !important;}
[data-baseweb="select"] div {color: var(--weiss) !important; font-size: clamp(15px, 4.4vw, 17px) !important;
    font-weight: 600 !important; white-space: normal !important; overflow: visible !important; text-overflow: clip !important;}
[data-baseweb="select"] svg {fill: var(--grau) !important; color: var(--grau) !important;}
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul {background: var(--kachel) !important; border: none !important;
    border-radius: 12px !important;}
[data-baseweb="popover"] li {background: var(--kachel) !important; color: var(--weiss) !important;
    font-size: clamp(15px, 4.4vw, 17px) !important; white-space: normal !important; min-height: 48px;
    border-bottom: 0.5px solid var(--linie);}
[data-baseweb="popover"] li:last-child {border-bottom: none;}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {background: var(--feld) !important;}

/* ---------- Formulare & einzelne Felder als Kacheln ---------- */
[data-testid="stForm"] {background: var(--kachel) !important; border: none !important;
    border-radius: 12px !important; padding: 16px !important;}
[data-testid="stNumberInput"]:not([data-testid="stForm"] [data-testid="stNumberInput"]) {
    background: var(--kachel); border-radius: 12px !important; padding: 12px 16px 16px;
}

/* ---------- Stepper: [−]  Zahl  [+]  fest in einer Zeile ---------- */
[data-testid="stNumberInputContainer"], [data-testid="stNumberInput"] > div > div {
    display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
    align-items: center !important; gap: 8px; background: transparent !important; border: none !important;
}
[data-testid="stNumberInputContainer"] > div:last-child {display: contents;}   /* Tasten-Gruppe auflösen */
[data-testid="stNumberInputStepDown"] {order: -1;}                            /* Minus nach links */
[data-testid="stNumberInput"] [data-baseweb="input"] {
    flex: 1 1 auto; min-width: 0; background: var(--feld) !important; border: none !important; border-radius: 12px !important;
}
[data-testid="stNumberInput"] input {
    background: var(--feld) !important; border: none !important; height: 52px; text-align: center;
    color: var(--weiss) !important; -webkit-text-fill-color: var(--weiss);
    font-size: clamp(22px, 7vw, 28px) !important; font-weight: 700 !important; font-variant-numeric: tabular-nums;
}
[data-testid="stNumberInput"] button {
    flex: 0 0 52px; width: 52px !important; height: 52px !important; padding: 0 !important;
    border: none !important; border-radius: 50% !important; background: var(--feld) !important;
    position: relative; transition: transform 0.1s ease;
}
[data-testid="stNumberInput"] button:active {transform: scale(0.92);}
[data-testid="stNumberInput"] button svg {display: none !important;}           /* Standard-Icon weg */
[data-testid="stNumberInput"] button::before {                                  /* deine SVGs rein  */
    content: ""; position: absolute; inset: 0; margin: auto; width: 20px; height: 20px;
    background-color: var(--weiss);
    -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat;
}
[data-testid="stNumberInputStepDown"] {--icon: url("__ICON_MINUS__");}
[data-testid="stNumberInputStepUp"] {--icon: url("__ICON_PLUS__");}

/* ---------- Speicher-Button ---------- */
[data-testid="stFormSubmitButton"], [data-testid="stFormSubmitButton"] > div {width: 100% !important;}
[data-testid="stFormSubmitButton"] button {
    width: 100% !important; height: 52px; margin-top: 4px; background: var(--rot) !important;
    border: none !important; border-radius: 12px !important; transition: transform 0.1s ease, opacity 0.1s ease;
}
[data-testid="stFormSubmitButton"] button p {color: var(--weiss) !important; font-size: 17px !important; font-weight: 700 !important;}
[data-testid="stFormSubmitButton"] button:active {transform: scale(0.97); opacity: 0.85;}
.stButton button {background: transparent !important; border: none !important; padding: 8px 0 !important; min-height: 44px;}
.stButton button p {color: var(--rot) !important; font-size: 15px !important; font-weight: 400 !important;}

/* ---------- Kennzahlen: große, fette, weiße Zahlen ---------- */
[data-testid="stMetric"] {background: var(--kachel); border-radius: 12px !important; padding: 16px !important; text-align: center;}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div {justify-content: center !important; width: 100%;}
[data-testid="stMetricLabel"] p {color: var(--grau) !important; font-size: clamp(12px, 3.6vw, 14px) !important;
    font-weight: 600 !important; text-align: center;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {
    justify-content: center !important; text-align: center; width: 100%; color: var(--weiss) !important;
    font-size: clamp(30px, 10vw, 40px) !important; font-weight: 700 !important; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums; white-space: normal !important; overflow: visible !important;
}
[data-testid="stMetricDelta"] {justify-content: center !important; color: var(--grau) !important;}
[data-testid="stMetricDelta"] svg {display: none;}

/* ---------- Maschinenbild & Platzhalter ---------- */
[data-testid="stImage"], [data-testid="stImageContainer"], .stImage {
    background-color: var(--kachel) !important; border-radius: 12px !important; padding: 12px;
    display: flex; justify-content: center; overflow: hidden;
}
[data-testid="stImage"] img, [data-testid="stImageContainer"] img, .stImage img {
    width: 100% !important; max-height: 260px; object-fit: contain !important; background-color: var(--kachel) !important;
}
.platzhalter {
    background: var(--kachel); border-radius: 12px; height: 180px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
    color: var(--grau); font-size: 14px; text-align: center; padding: 16px;
}
.platzhalter b {font-size: 34px; font-weight: 200; color: var(--linie); line-height: 1;}

/* ---------- Meldungen & Tabelle ---------- */
[data-testid="stAlert"] > div, [data-testid="stAlertContainer"] {background: var(--kachel) !important;
    border: none !important; border-radius: 12px !important;}
[data-testid="stAlert"] p {color: var(--weiss) !important; font-size: 15px !important;}
[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden; background: var(--kachel); border: none !important;}
</style>
"""
st.markdown(DESIGN_CSS.replace("__ICON_PLUS__", ICON_PLUS).replace("__ICON_MINUS__", ICON_MINUS),
            unsafe_allow_html=True)

# ---------------------------------------------------------------
# Kopf + Navigation
# ---------------------------------------------------------------
heute = datetime.now().strftime("%Y-%m-%d")
st.title("Gym Log")
bereich = st.radio("Bereich", [BEREICH_TRAINING, BEREICH_KOERPER], horizontal=True,
                   label_visibility="collapsed", key="navigation")

# ===============================================================
# BEREICH 1: TRAINING
# ===============================================================
if bereich == BEREICH_TRAINING:
    alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    heutige_saetze = alle_saetze[alle_saetze["Datum"] == heute]

    uebung_name = st.selectbox("Übung", list(UEBUNGEN),
                               format_func=lambda name: f"{UEBUNGEN[name]['gruppe']} · {name}")
    uebung = UEBUNGEN[uebung_name]

    # Bild oder eleganter Platzhalter
    bild_pfad = bild_finden(uebung)
    bild_gezeigt = False
    if bild_pfad:
        try:
            st.image(bild_pfad)
            bild_gezeigt = True
        except Exception:
            bild_gezeigt = False
    if not bild_gezeigt:
        st.markdown('<div class="platzhalter"><b>＋</b>Noch kein Foto für diese Übung</div>',
                    unsafe_allow_html=True)

    erledigt = int((heutige_saetze["Uebung"] == uebung_name).sum())
    st.caption(f"Ziel: {uebung['saetze']} Sätze × {uebung['wdh']} Wiederholungen  ·  "
               f"heute erledigt: {erledigt} von {uebung['saetze']}")

    fruehere = alle_saetze[alle_saetze["Uebung"] == uebung_name]
    start_gewicht = float(fruehere["Gewicht_kg"].iloc[-1]) if not fruehere.empty else uebung["kg"]
    start_wdh = int(uebung["wdh"].split("–")[0])

    with st.form("satz_formular"):
        gewicht = st.number_input("Gewicht (kg)", min_value=0.0, max_value=500.0,
                                  value=start_gewicht, step=2.5, key=f"gewicht_{uebung_name}")
        wiederholungen = st.number_input("Wiederholungen", min_value=1, max_value=100,
                                         value=start_wdh, step=1, key=f"wdh_{uebung_name}")
        gespeichert = st.form_submit_button("Training loggen", type="primary")

    if gespeichert:
        ok = zeile_speichern(TRAINING_CSV, {
            "Datum": heute, "Uhrzeit": datetime.now().strftime("%H:%M"), "Gruppe": uebung["gruppe"],
            "Uebung": uebung_name, "Gewicht_kg": float(gewicht), "Wiederholungen": int(wiederholungen),
        })
        if ok:
            st.success(f"Gespeichert: {uebung_name} · {zahl(gewicht)} kg × {int(wiederholungen)}")
            alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
            heutige_saetze = alle_saetze[alle_saetze["Datum"] == heute]
        else:
            st.warning("Speichern hat nicht geklappt. Bitte noch einmal versuchen.")

    st.subheader("Heute")
    if heutige_saetze.empty:
        st.caption("Noch keine Sätze heute.")
    else:
        spalte_1, spalte_2 = st.columns(2)
        spalte_1.metric("Sätze", len(heutige_saetze))
        volumen = float((heutige_saetze["Gewicht_kg"] * heutige_saetze["Wiederholungen"]).sum())
        spalte_2.metric("Volumen", f"{tausender(volumen)} kg")

        anzeige = heutige_saetze.iloc[::-1][["Uhrzeit", "Uebung", "Gewicht_kg", "Wiederholungen"]].rename(
            columns={"Uebung": "Übung", "Gewicht_kg": "kg", "Wiederholungen": "Wdh."})
        st.dataframe(anzeige, hide_index=True)

        if st.button("Letzten Satz löschen"):
            try:
                alle_saetze.iloc[:-1].to_csv(TRAINING_CSV, index=False, encoding="utf-8")
                st.rerun()
            except Exception:
                st.warning("Löschen hat nicht geklappt.")

# ===============================================================
# BEREICH 2: KÖRPERDATEN
# ===============================================================
else:
    gewichte = csv_laden(GEWICHT_CSV, GEWICHT_SPALTEN)
    letztes_gewicht = float(gewichte["Gewicht_kg"].iloc[-1]) if not gewichte.empty else 80.0   # Annahme: 80 kg

    st.subheader("Körpergewicht")
    if not gewichte.empty:
        veraenderung = None
        if len(gewichte) > 1:
            veraenderung = f"{letztes_gewicht - float(gewichte['Gewicht_kg'].iloc[-2]):+.1f} kg".replace(".", ",")
        st.metric("Aktuell", f"{zahl(round(letztes_gewicht, 1))} kg", veraenderung, delta_color="off")

    with st.form("gewicht_formular"):
        neues_gewicht = st.number_input("Gewicht heute (kg)", min_value=30.0, max_value=300.0,
                                        value=letztes_gewicht, step=0.1, format="%.1f")
        if st.form_submit_button("Gewicht speichern", type="primary"):
            if zeile_speichern(GEWICHT_CSV, {"Datum": heute, "Uhrzeit": datetime.now().strftime("%H:%M"),
                                             "Gewicht_kg": round(float(neues_gewicht), 1)}):
                st.success("Gewicht gespeichert.")
                letztes_gewicht = round(float(neues_gewicht), 1)
            else:
                st.warning("Speichern hat nicht geklappt. Bitte noch einmal versuchen.")

    # Kalorien (Mifflin-St. Jeor, Männer · PAL 1,55 · +300 kcal) – nur die Ergebnisse
    st.subheader("Kalorien")
    einstellungen = einstellungen_laden()
    alter = st.number_input("Alter (Jahre)", min_value=14, max_value=90, value=einstellungen["alter"], step=1)
    groesse = st.number_input("Größe (cm)", min_value=140, max_value=220, value=einstellungen["groesse"], step=1)
    if (alter, groesse) != (einstellungen["alter"], einstellungen["groesse"]):
        einstellungen_speichern(int(alter), int(groesse))

    bmr = (10 * letztes_gewicht) + (6.25 * groesse) - (5 * alter) + 5
    tagesbedarf = bmr * AKTIVITAETS_FAKTOR
    zielbedarf = tagesbedarf + MUSKELAUFBAU_UEBERSCHUSS

    st.metric("Tagesbedarf (Gewicht halten)", f"{tausender(tagesbedarf)} kcal")
    st.metric("Zielbedarf (Muskelaufbau / Zunehmen)", f"{tausender(zielbedarf)} kcal")
