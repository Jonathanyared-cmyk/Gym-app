"""
Gym Log – stabile Version (nur eingebaute Streamlit-Elemente)
Start:   streamlit run app.py
Ordner:  bilder/  -> Maschinenfotos (z. B. bilder/brustpresse.jpg)
Daten:   trainingsdaten.csv, weight_data.csv, einstellungen.json (werden automatisch angelegt)
Design:  .streamlit/config.toml (dunkles Farbschema)
"""

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

AKTIVITAETS_FAKTOR = 1.55          # Standard-Faktor für aktives Training
MUSKELAUFBAU_UEBERSCHUSS = 300     # kcal

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
# Apple-Health-Look (nur CSS – die Streamlit-Elemente selbst bleiben unverändert)
# Jede Regel betrifft nur das Aussehen. Greift eine Regel einmal nicht,
# sieht das Element nur "normaler" aus – die App funktioniert trotzdem.
# ---------------------------------------------------------------
st.markdown("""
<style>
:root {
    --schwarz: #000000;
    --kachel: #1C1C1E;
    --feld: #2C2C2E;
    --linie: #38383A;
    --weiss: #FFFFFF;
    --hellgrau: #8E8E93;
    --rot: #FF2D55;
}

/* ---------- Grundlagen ---------- */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDecoration"], [data-testid="stToolbar"] {display: none !important;}

.stApp {background-color: var(--schwarz) !important;}
.block-container {max-width: 560px; padding: 1.5rem 16px 3rem !important;}
[data-testid="stVerticalBlock"] {gap: 16px;}

/* Apple-Systemschrift für alle Texte (Icons bleiben unberührt) */
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp h1, .stApp h2, .stApp h3,
.stApp li, [data-testid="stMarkdownContainer"], [data-baseweb="select"] div {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                 "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* Überschriften wie in Apple Health */
.stApp h1 {color: var(--weiss) !important; font-size: 34px !important; font-weight: 700 !important;
           letter-spacing: -0.02em; padding: 0 0 4px !important;}
.stApp h2, .stApp h3 {color: var(--weiss) !important; font-size: 22px !important; font-weight: 700 !important;
                      padding: 8px 0 0 !important;}

/* Texte: immer voll ausgeschrieben, nie "..." und nie mitten im Wort getrennt */
.stApp p, .stApp label, .stApp span, [data-testid="stMetricLabel"] *, [data-testid="stCaptionContainer"] * {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
}
[data-testid="stWidgetLabel"] p, .stApp label p {
    color: var(--hellgrau) !important; font-size: 15px !important; font-weight: 500 !important;
}
[data-testid="stCaptionContainer"] p {color: var(--hellgrau) !important; font-size: 14px !important;}

/* ---------- Kacheln: Auswahlboxen ---------- */
[data-testid="stSelectbox"] {
    background: var(--kachel); border-radius: 16px !important; padding: 16px;
}
[data-baseweb="select"] > div {
    background: var(--feld) !important; border: none !important; border-radius: 12px !important;
    min-height: 50px; height: auto !important;
}
[data-baseweb="select"] > div > div {padding-top: 8px; padding-bottom: 8px;}
[data-baseweb="select"] div {color: var(--weiss) !important; font-size: 17px !important;
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important;}
[data-baseweb="select"] svg {fill: var(--hellgrau) !important; color: var(--hellgrau) !important;}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li {background: var(--kachel) !important;}
[data-baseweb="popover"] li {color: var(--weiss) !important; font-size: 17px !important;
    white-space: normal !important; min-height: 48px;}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {background: var(--feld) !important;}

/* ---------- Kacheln: Formulare (Satz / Gewicht) ---------- */
[data-testid="stForm"] {
    background: var(--kachel) !important; border: none !important;
    border-radius: 16px !important; padding: 16px !important;
}

/* Zahlenfelder: anthrazit, groß, gut tippbar */
[data-testid="stNumberInput"] input {
    background: var(--feld) !important; color: var(--weiss) !important; -webkit-text-fill-color: var(--weiss);
    font-size: 20px !important; font-weight: 500; height: 50px; border: none !important;
}
[data-testid="stNumberInput"] > div > div {
    background: var(--feld) !important; border: none !important; border-radius: 12px !important; overflow: hidden;
}
[data-testid="stNumberInput"] button {
    background: var(--feld) !important; border: none !important; color: var(--weiss) !important; min-width: 44px;
}
[data-testid="stNumberInput"] button:hover {background: var(--linie) !important;}

/* Zahlenfelder außerhalb eines Formulars (Alter, Größe) bekommen eine eigene Kachel */
[data-testid="stNumberInput"]:not([data-testid="stForm"] [data-testid="stNumberInput"]) {
    background: var(--kachel); border-radius: 16px !important; padding: 16px;
}

/* ---------- Speicher-Button: flach, breit, Apple-Rot ---------- */
[data-testid="stFormSubmitButton"], [data-testid="stFormSubmitButton"] > div {width: 100% !important;}
[data-testid="stFormSubmitButton"] button {
    width: 100% !important; height: 52px; margin-top: 4px;
    background: var(--rot) !important; border: none !important; border-radius: 14px !important;
    box-shadow: none !important; transition: transform 0.1s ease, opacity 0.1s ease;
}
[data-testid="stFormSubmitButton"] button p {color: var(--weiss) !important; font-size: 17px !important;
                                             font-weight: 600 !important;}
[data-testid="stFormSubmitButton"] button:active {transform: scale(0.97); opacity: 0.9;}

/* Zweitrangige Buttons ("Letzten Satz löschen") dezent */
.stButton button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 8px 0 !important; min-height: 44px;
}
.stButton button p {color: var(--hellgrau) !important; font-size: 15px !important;}

/* ---------- Kacheln: Kennzahlen (st.metric) ---------- */
[data-testid="stMetric"] {
    background: var(--kachel); border-radius: 16px !important; padding: 16px !important;
}
[data-testid="stMetricLabel"] p {color: var(--hellgrau) !important; font-size: 15px !important; font-weight: 500 !important;}
[data-testid="stMetricValue"] {color: var(--weiss) !important; font-size: 32px !important; font-weight: 600 !important;
                               font-variant-numeric: tabular-nums;}
[data-testid="stMetricValue"] div {white-space: normal !important; overflow: visible !important;}
[data-testid="stMetricDelta"] {color: var(--hellgrau) !important;}

/* ---------- Kachel: Maschinenbild (immer komplett sichtbar) ---------- */
[data-testid="stImage"], [data-testid="stImageContainer"], .stImage {
    background: var(--kachel); border-radius: 16px !important; padding: 16px;
    display: flex; justify-content: center; overflow: hidden;
}
[data-testid="stImage"] img, [data-testid="stImageContainer"] img, .stImage img {
    width: 100% !important; max-height: 260px; object-fit: contain !important;
    border-radius: 10px;
}

/* ---------- Info- und Erfolgsmeldungen als ruhige Kacheln ---------- */
[data-testid="stAlert"] > div, [data-testid="stAlertContainer"] {
    background: var(--kachel) !important; border: none !important; border-radius: 16px !important;
}
[data-testid="stAlert"] p {color: var(--weiss) !important; font-size: 15px !important;}

/* ---------- Tabelle "Heute" ---------- */
[data-testid="stDataFrame"] {border-radius: 16px; overflow: hidden; background: var(--kachel);}

/* Kennzahlen nebeneinander (Sätze / Volumen) dürfen auf dem iPhone nebeneinander bleiben */
[data-testid="stHorizontalBlock"] {gap: 16px;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------
# Hilfsfunktionen (alle mit Sicherheitsnetz)
# ---------------------------------------------------------------
def csv_laden(pfad: Path, spalten: list) -> pd.DataFrame:
    """Liest eine CSV. Fehlt sie oder ist sie kaputt, kommt eine leere Tabelle zurück."""
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
    standard = {"alter": 25, "groesse": 178}    # Annahme für den ersten Start
    try:
        if EINSTELLUNGEN_DATEI.exists():
            standard.update(json.loads(EINSTELLUNGEN_DATEI.read_text(encoding="utf-8")))
    except Exception:
        pass
    return standard


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
    """Sucht das Foto im Ordner 'bilder'. Gibt None zurück, wenn nichts passt – nie einen Fehler."""
    try:
        ordner = next((o for o in APP_ORDNER.iterdir() if o.is_dir() and o.name.lower() == "bilder"), None)
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


# ---------------------------------------------------------------
# Kopf + Navigation
# ---------------------------------------------------------------
heute = datetime.now().strftime("%Y-%m-%d")
st.title("Gym Log")

bereich = st.selectbox("Bereich wählen", ["🏋️‍♂️ Trainings-Tracker", "📊 Meine Körperdaten & Kalorien"])

# ===============================================================
# BEREICH 1: TRAININGS-TRACKER
# ===============================================================
if bereich == "🏋️‍♂️ Trainings-Tracker":
    alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    heutige_saetze = alle_saetze[alle_saetze["Datum"] == heute]

    uebung_name = st.selectbox(
        "Übung wählen", list(UEBUNGEN),
        format_func=lambda name: f"{UEBUNGEN[name]['gruppe']} · {name}",
    )
    uebung = UEBUNGEN[uebung_name]

    # Bild der Maschine
    bild_pfad = bild_finden(uebung)
    if bild_pfad:
        try:
            st.image(bild_pfad)
        except Exception:
            st.info("Maschinen-Bild wird geladen...")
    else:
        st.info("Maschinen-Bild wird geladen...")

    # Ziel und Fortschritt dieser Übung
    erledigt = int((heutige_saetze["Uebung"] == uebung_name).sum())
    st.caption(f"Ziel: {uebung['saetze']} Sätze × {uebung['wdh']} Wiederholungen  ·  "
               f"heute erledigt: {erledigt} von {uebung['saetze']}")

    # Startgewicht = zuletzt benutztes Gewicht, sonst Plan-Gewicht
    fruehere = alle_saetze[alle_saetze["Uebung"] == uebung_name]
    start_gewicht = float(fruehere["Gewicht_kg"].iloc[-1]) if not fruehere.empty else uebung["kg"]
    start_wdh = int(uebung["wdh"].split("–")[0])

    with st.form("satz_formular"):
        gewicht = st.number_input("Gewicht (kg)", min_value=0.0, max_value=500.0,
                                  value=start_gewicht, step=2.5, key=f"gewicht_{uebung_name}")
        wiederholungen = st.number_input("Wiederholungen", min_value=1, max_value=100,
                                         value=start_wdh, step=1, key=f"wdh_{uebung_name}")
        gespeichert = st.form_submit_button("Satz speichern", type="primary")

    if gespeichert:
        jetzt = datetime.now()
        ok = zeile_speichern(TRAINING_CSV, {
            "Datum": heute, "Uhrzeit": jetzt.strftime("%H:%M"), "Gruppe": uebung["gruppe"],
            "Uebung": uebung_name, "Gewicht_kg": float(gewicht), "Wiederholungen": int(wiederholungen),
        })
        if ok:
            st.success(f"Gespeichert: {uebung_name} · {zahl(gewicht)} kg × {int(wiederholungen)}")
            alle_saetze = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
            heutige_saetze = alle_saetze[alle_saetze["Datum"] == heute]
        else:
            st.warning("Speichern hat nicht geklappt. Bitte noch einmal versuchen.")

    # Heutiger Verlauf
    st.subheader("Heute")
    if heutige_saetze.empty:
        st.caption("Noch keine Sätze heute.")
    else:
        spalte_1, spalte_2 = st.columns(2)
        spalte_1.metric("Sätze", len(heutige_saetze))
        volumen = float((heutige_saetze["Gewicht_kg"] * heutige_saetze["Wiederholungen"]).sum())
        spalte_2.metric("Volumen", f"{volumen:,.0f} kg".replace(",", "."))

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
# BEREICH 2: KÖRPERDATEN & KALORIEN
# ===============================================================
else:
    gewichte = csv_laden(GEWICHT_CSV, GEWICHT_SPALTEN)
    letztes_gewicht = float(gewichte["Gewicht_kg"].iloc[-1]) if not gewichte.empty else 80.0   # Annahme: 80 kg

    # Körpergewicht
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

    # Kalorienrechner (Mifflin-St. Jeor, Männer)
    st.subheader("Kalorien")
    einstellungen = einstellungen_laden()
    alter = st.number_input("Alter (Jahre)", min_value=14, max_value=90,
                            value=int(einstellungen["alter"]), step=1)
    groesse = st.number_input("Größe (cm)", min_value=140, max_value=220,
                              value=int(einstellungen["groesse"]), step=1)
    if (alter, groesse) != (einstellungen["alter"], einstellungen["groesse"]):
        einstellungen_speichern(int(alter), int(groesse))

    bmr = (10 * letztes_gewicht) + (6.25 * groesse) - (5 * alter) + 5
    tagesbedarf = bmr * AKTIVITAETS_FAKTOR
    muskelaufbau = tagesbedarf + MUSKELAUFBAU_UEBERSCHUSS

    st.metric("Grundumsatz", f"{int(bmr)} kcal")
    st.metric("Tagesbedarf zum Halten", f"{int(tagesbedarf)} kcal")
    st.metric("Zielbedarf für Muskelaufbau (+300 kcal)", f"{int(muskelaufbau)} kcal")
    st.caption(f"Berechnet mit {zahl(round(letztes_gewicht, 1))} kg Körpergewicht.")
