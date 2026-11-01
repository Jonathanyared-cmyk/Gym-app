"""
Gym Log – Apple-Health-Look (Hell/Dunkel) für iPhone & PC
Start:   streamlit run app.py
Ordner:  bilder/   -> Maschinenfotos + plus.svg, minus.svg, dumbbell.svg
Daten:   trainingsdaten.csv, weight_data.csv, einstellungen.json (werden automatisch angelegt)
Braucht: streamlit >= 1.45 (siehe requirements.txt)
"""

import base64
import html
import json
import re
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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

# PAL-Faktor (Aktivität) – Standard: "Sehr aktiv" = 1,75
PAL_STUFEN = {
    "Wenig aktiv (sitzend)": 1.2,
    "Moderat aktiv (1-3x Training)": 1.375,
    "Sehr aktiv (3-5x hartes Training)": 1.55,
    "Extrem aktiv (Tägliches Training)": 1.725,
}
MUSKELAUFBAU_UEBERSCHUSS_KCAL = 300
PROTEIN_G_PRO_KG = 2.0
FETT_G_PRO_KG = 0.8
PAUSE_SEKUNDEN = 90

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
STANDARD_EINSTELLUNGEN = {"light_mode": False, "alter": 25, "groesse": 178,
                          "pal_stufe": "Sehr aktiv (3-5x hartes Training)"}

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
    if gespeichert.get("pal_stufe") not in PAL_STUFEN:
        gespeichert.pop("pal_stufe", None)
    for schluessel, standardwert in STANDARD_EINSTELLUNGEN.items():
        if schluessel not in st.session_state:
            st.session_state[schluessel] = gespeichert.get(schluessel, standardwert)


def einstellungen_speichern() -> None:
    werte = {schluessel: st.session_state[schluessel] for schluessel in STANDARD_EINSTELLUNGEN}
    try:
        EINSTELLUNGEN_DATEI.write_text(json.dumps(werte, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass   # z. B. schreibgeschützt – dann gilt die Einstellung nur für diese Sitzung


einstellungen_laden()


# ===============================================================
# 4) ICONS (SF Symbols aus "bilder") – Ersatz-Icons, falls eine Datei fehlt
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


def bilder_ordner_finden():
    """Ordner 'bilder' neben app.py – auch als 'Bilder' (Linux/Cloud unterscheidet Groß/Klein)."""
    if BILDER_ORDNER.is_dir():
        return BILDER_ORDNER
    for ordner in APP_ORDNER.iterdir():
        if ordner.is_dir() and ordner.name.lower() == "bilder":
            return ordner
    return None


@st.cache_data
def icon_als_data_uri(icon_name: str) -> str:
    ordner = bilder_ordner_finden()
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
    return f'<span class="{klasse}" style="--icon: url(\'{data_uri}\')" aria-hidden="true"></span>'


# ===============================================================
# 5) FARBEN
# ===============================================================
FARBEN_DUNKEL = {
    "bg": "#000000", "karte": "#1C1C1E", "feld": "#2C2C2E", "linie": "#38383A",
    "segment": "#2C2C2E", "segment_an": "#636366", "text": "#FFFFFF", "grau": "#8E8E93",
    "schatten": "none",
}
FARBEN_HELL = {
    "bg": "#F2F2F7", "karte": "#FFFFFF", "feld": "#F2F2F7", "linie": "#E5E5EA",
    "segment": "#EEEEF0", "segment_an": "#FFFFFF", "text": "#000000", "grau": "#6C6C70",
    "schatten": "0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04)",
}
AKZENT = "#FF2D55"
farben = FARBEN_HELL if st.session_state["light_mode"] else FARBEN_DUNKEL
KOMPONENTEN_FARBEN = {k: farben[k] for k in ("text", "grau", "feld", "linie")}


# ===============================================================
# 6) iOS-EINGABE-KOMPONENTE (Stepper + Scrollrad)
#    Eigenes kleines HTML-Bauteil: Flexbox hält −, Zahl, + garantiert in einer Zeile,
#    und ein natives <select> öffnet auf dem iPhone das echte iOS-Scrollrad.
# ===============================================================
KOMPONENTEN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
    -webkit-font-smoothing: antialiased; }
  * { box-sizing: border-box; }
  button { touch-action: manipulation; -webkit-tap-highlight-color: transparent; font: inherit; }

  /* Stepper: −  Wert  +  (immer eine Zeile) */
  .stepper { display: flex; flex-direction: row; flex-wrap: nowrap; align-items: center;
             justify-content: space-between; gap: 12px; height: 84px; }
  .rund { flex: 0 0 56px; width: 56px; height: 56px; padding: 0; border: none; border-radius: 50%;
          background: var(--feld); display: grid; place-items: center; cursor: pointer;
          transition: transform .1s ease, opacity .15s ease; }
  .rund:active { transform: scale(.92); }
  .rund:disabled { opacity: .35; cursor: default; }
  .rund i { width: 22px; height: 22px; background: var(--text);
            -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat; }
  .wert { flex: 1 1 auto; min-width: 0; text-align: center; line-height: 1.1; }
  .wert span { display: block; color: var(--grau); font-size: 13px; margin-bottom: 2px; }
  .wert b { color: var(--text); font-size: 36px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
  .wert small { color: var(--grau); font-size: 15px; font-weight: 500; margin-left: 4px; }

  /* Scrollrad-Zeilen wie in den iOS-Einstellungen */
  .zeile { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 16px;
           min-height: 52px; padding: 8px 0; border-bottom: 1px solid var(--linie); }
  .zeile:last-child { border-bottom: none; }
  .zeile label { color: var(--text); font-size: clamp(14px, 4vw, 17px); white-space: nowrap; }
  .pille { color: var(--text); background: var(--feld); border-radius: 8px; padding: 6px 12px; text-align: right;
           font-size: clamp(14px, 4vw, 17px); font-variant-numeric: tabular-nums;
           white-space: normal; word-break: keep-all; max-width: 70%; }
  .zeile select { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer;
                  font-size: 16px; -webkit-appearance: none; appearance: none; }
</style></head>
<body><div id="app"></div>
<script>
  const senden = (type, daten) =>
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, daten || {}), "*");
  const hoeheMelden = () => senden("streamlit:setFrameHeight", { height: document.body.scrollHeight });
  const zahlFormat = (w, n) => (n > 0 ? w.toFixed(n) : String(Math.round(w * 100) / 100)).replace(".", ",");

  let args = null, wert = null, werte = {}, letzterToken = null, gebaut = false;

  function stepperAnzeigen() {
    document.getElementById("zahl").textContent = zahlFormat(wert, args.nachkomma);
    document.getElementById("einheit").textContent = args.einheit;
    document.getElementById("label").textContent = args.label;
    document.getElementById("minus").disabled = wert <= args.min;
    document.getElementById("plus").disabled = wert >= args.max;
  }
  function stepperAendern(richtung) {
    let neu = Math.round((wert + richtung * args.schritt) * 100) / 100;
    wert = Math.min(args.max, Math.max(args.min, neu));
    stepperAnzeigen();
    senden("streamlit:setComponentValue", { value: { wert: wert, token: letzterToken }, dataType: "json" });
  }
  function stepperRendern() {
    if (args.token !== letzterToken) { wert = args.wert; letzterToken = args.token; }
    if (!gebaut) {
      document.getElementById("app").innerHTML =
        '<div class="stepper">' +
        '<button class="rund" id="minus" aria-label="Weniger"><i style="--icon:url(\'' + args.icon_minus + '\')"></i></button>' +
        '<div class="wert"><span id="label"></span><b id="zahl"></b><small id="einheit"></small></div>' +
        '<button class="rund" id="plus" aria-label="Mehr"><i style="--icon:url(\'' + args.icon_plus + '\')"></i></button>' +
        '</div>';
      document.getElementById("minus").onclick = () => stepperAendern(-1);
      document.getElementById("plus").onclick = () => stepperAendern(1);
      gebaut = true;
    }
    stepperAnzeigen();
  }

  function walzenRendern() {
    if (args.token !== letzterToken) {
      args.felder.forEach(f => { werte[f.key] = f.wert; });
      letzterToken = args.token;
    }
    if (!gebaut) {
      document.getElementById("app").innerHTML = args.felder.map((f, i) => {
        let optionen = "";
        if (f.optionen) {   // Text-Auswahl (z. B. Aktivität)
          f.optionen.forEach(o => { optionen += '<option value="' + o + '">' + o + '</option>'; });
        } else {            // Zahlen-Walze (Alter, Größe)
          for (let v = f.min; v <= f.max; v++) optionen += '<option value="' + v + '">' + v + ' ' + f.einheit + '</option>';
        }
        return '<div class="zeile"><label for="walze' + i + '">' + f.label + '</label>' +
               '<span class="pille" id="pille' + i + '"></span>' +
               '<select id="walze' + i + '" aria-label="' + f.label + '">' + optionen + '</select></div>';
      }).join("");
      args.felder.forEach((f, i) => {
        document.getElementById("walze" + i).onchange = (e) => {
          werte[f.key] = f.optionen ? e.target.value : Number(e.target.value);
          walzenAnzeigen();
          senden("streamlit:setComponentValue", { value: { werte: werte, token: letzterToken }, dataType: "json" });
        };
      });
      gebaut = true;
    }
    walzenAnzeigen();
  }
  function walzenAnzeigen() {
    args.felder.forEach((f, i) => {
      document.getElementById("walze" + i).value = String(werte[f.key]);
      document.getElementById("pille" + i).textContent = f.optionen ? werte[f.key] : werte[f.key] + " " + f.einheit;
    });
  }

  window.addEventListener("message", (e) => {
    const d = e.data;
    if (!d || d.type !== "streamlit:render") return;
    args = d.args;
    for (const k in args.farben) document.documentElement.style.setProperty("--" + k, args.farben[k]);
    if (args.art === "stepper") stepperRendern(); else walzenRendern();
    hoeheMelden();
  });
  senden("streamlit:componentReady", { apiVersion: 1 });
</script></body></html>
"""


def ios_komponente_anlegen():
    """Schreibt das HTML-Bauteil in einen Temp-Ordner und meldet es bei Streamlit an."""
    ordner = Path(tempfile.gettempdir()) / "gymlog_ios_eingabe"
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / "index.html"
    if not datei.exists() or datei.read_text(encoding="utf-8") != KOMPONENTEN_HTML:
        datei.write_text(KOMPONENTEN_HTML, encoding="utf-8")
    return components.declare_component("gymlog_ios_eingabe", path=str(ordner))


ios_eingabe = ios_komponente_anlegen()


def stepper_wert_uebernehmen(feld: str) -> None:
    """Übernimmt den zuletzt getippten Stepper-Wert – aber nur, wenn er zur aktuellen Übung gehört."""
    antwort = st.session_state.get(f"stepper_{feld}")
    if isinstance(antwort, dict) and antwort.get("token") == st.session_state.get(f"{feld}_token", 0):
        st.session_state[feld] = antwort["wert"]


def wert_von_aussen_setzen(feld: str, wert: float) -> None:
    """Setzt einen Stepper-Wert aus Python (z. B. neue Übung) und macht alte Eingaben ungültig."""
    st.session_state[feld] = wert
    st.session_state[f"{feld}_token"] = st.session_state.get(f"{feld}_token", 0) + 1


def stepper(feld: str, beschriftung: str, einheit: str, schritt: float,
            minimum: float, maximum: float, nachkomma: int = 0) -> None:
    ios_eingabe(art="stepper", wert=float(st.session_state[feld]), schritt=schritt, min=minimum, max=maximum,
                nachkomma=nachkomma, einheit=einheit, label=beschriftung,
                token=st.session_state.get(f"{feld}_token", 0), farben=KOMPONENTEN_FARBEN,
                icon_plus=ICON_PLUS, icon_minus=ICON_MINUS, key=f"stepper_{feld}", default=None)


def koerperangaben_uebernehmen() -> None:
    antwort = st.session_state.get("walzen_koerper")
    if isinstance(antwort, dict) and "werte" in antwort:
        werte = antwort["werte"]
        neu = (int(werte["alter"]), int(werte["groesse"]), werte.get("pal_stufe", st.session_state["pal_stufe"]))
        if neu[2] not in PAL_STUFEN:
            return
        if neu != (st.session_state["alter"], st.session_state["groesse"], st.session_state["pal_stufe"]):
            st.session_state["alter"], st.session_state["groesse"], st.session_state["pal_stufe"] = neu
            einstellungen_speichern()


# ===============================================================
# 7) CSS
# ===============================================================
DESIGN_CSS = f"""
<style>
:root {{
    --bg: {farben["bg"]}; --karte: {farben["karte"]}; --feld: {farben["feld"]}; --linie: {farben["linie"]};
    --segment: {farben["segment"]}; --segment-an: {farben["segment_an"]};
    --text: {farben["text"]}; --grau: {farben["grau"]}; --schatten: {farben["schatten"]}; --akzent: {AKZENT};
}}

/* ---------- Grundgerüst & Streamlit ausblenden ---------- */
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
.block-container {{ max-width: 520px; padding: 16px 16px 64px !important; }}
[data-testid="stVerticalBlock"] {{ gap: 16px !important; }}
[data-testid="stElementContainer"] p {{ margin: 0; }}

/* ---------- Kein Text wird abgeschnitten (nie "..."), Schrift passt sich an ---------- */
.stApp p, .stApp span, .stApp button, .stApp button p,
.karte, .widget, .widget-name, .kopf-name, .kopf-ziel, .feld-label, .messwert span {{
    white-space: normal !important; word-break: keep-all !important; overflow-wrap: break-word;
    overflow: visible; text-overflow: clip !important; hyphens: none;
}}
/* Fließtext skaliert flüssig mit der iPhone-Breite (große Kennzahlen bleiben fest) */
.stApp button p, .kopf-ziel, .feld-label, .messwert span, .widget-name, .widget-info,
.unterzeile, .aufteilung span, .karte-label, .kopf-label {{
    font-size: clamp(14px, 4vw, 17px) !important;
}}
iframe {{ border: none; display: block; }}
button {{ touch-action: manipulation; -webkit-tap-highlight-color: transparent; }}

/* ---------- Kopf ---------- */
.datum {{ color: var(--grau) !important; font-size: 13px; font-weight: 600; letter-spacing: .04em;
          text-transform: uppercase; margin: 0; }}
.titel {{ font-size: 34px; font-weight: 700; letter-spacing: -.025em; margin: 0; line-height: 1.15; }}
.abschnitt {{ font-size: 20px; font-weight: 700; letter-spacing: -.01em; margin: 0 !important; }}
[data-testid="stToggle"] label p, [data-testid="stCheckbox"] label p {{ color: var(--grau) !important; font-size: 14px !important; }}
.st-key-kopfzeile [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; align-items: center; }}
.st-key-kopfzeile [data-testid="stColumn"] {{ min-width: 0 !important; }}
.st-key-kopfzeile [data-testid="stColumn"]:last-child {{ flex: 0 0 auto !important; width: auto !important; }}

/* ---------- Kacheln: einheitlich 16px Radius, 16px Innenabstand ---------- */
[class*="st-key-karte"], .karte {{
    background: var(--karte); border-radius: 16px; padding: 16px !important; margin: 0 !important;
    box-shadow: var(--schatten);
}}
[class*="st-key-karte"] [data-testid="stVerticalBlock"] {{ gap: 16px !important; }}
.kopf-label {{ color: var(--akzent) !important; font-size: 14px; font-weight: 600; margin: 0 0 4px !important; }}
.kopf-name {{ font-size: clamp(18px, 5.5vw, 22px); font-weight: 700; letter-spacing: -.01em; line-height: 1.25; }}
.kopf-ziel {{ color: var(--grau) !important; font-size: 15px; margin: 4px 0 0 !important; }}
.trennlinie {{ height: 1px; background: var(--linie); }}
.feld-label {{ color: var(--grau) !important; font-size: 13px; margin: 0; }}

/* ---------- Icons ---------- */
.icon, .icon-gross {{
    display: inline-block; flex: none; width: 1.05em; height: 1.05em; vertical-align: -0.15em; margin-right: 6px;
    background-color: currentColor;
    -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat;
}}
.icon-gross {{ width: 48px; height: 48px; margin: 0; }}

/* ---------- iOS-Segmented-Control ---------- */
[class*="st-key-segment"] [data-testid="stButtonGroup"],
[class*="st-key-segment"] [data-testid="stButtonGroup"] > div {{ width: 100%; }}
[class*="st-key-segment"] [data-testid="stButtonGroup"] > div > div {{
    display: flex !important; width: 100%; flex-wrap: nowrap !important; gap: 0 !important;
    background: var(--segment); border-radius: 10px; padding: 2px;
}}
[class*="st-key-segment"] button {{
    flex: 1 1 0 !important; min-width: 0 !important; min-height: 40px; height: auto !important;
    padding: 6px 8px !important; border: none !important;
    border-radius: 8px !important; background: transparent !important; box-shadow: none !important;
    transition: background .2s ease;
}}
[class*="st-key-segment"] button p {{ color: var(--text) !important; font-size: clamp(14px, 4vw, 17px) !important;
    font-weight: 500 !important; line-height: 1.2; text-align: center; }}
[class*="st-key-segment"] button[kind$="Active"], [class*="st-key-segment"] button[data-testid$="Active"] {{
    background: var(--segment-an) !important; box-shadow: 0 1px 4px rgba(0,0,0,.15) !important; }}
[class*="st-key-segment"] button[kind$="Active"] p,
[class*="st-key-segment"] button[data-testid$="Active"] p {{ font-weight: 600 !important; }}
.st-key-segment_reiter button {{ min-height: 48px; }}

/* ---------- Übungs-Chips ---------- */
.st-key-uebung_auswahl [data-testid="stButtonGroup"] > div > div {{ flex-wrap: wrap !important; gap: 8px !important; }}
.st-key-uebung_auswahl button {{
    min-height: 44px; height: auto !important; max-width: 100%; padding: 8px 16px !important;
    border: none !important; border-radius: 22px !important;
    background: var(--feld) !important; box-shadow: none !important;
}}
.st-key-uebung_auswahl button p {{ color: var(--text) !important; font-size: clamp(14px, 4vw, 17px) !important;
    line-height: 1.25; text-align: left; }}
.st-key-uebung_auswahl button[kind$="Active"], .st-key-uebung_auswahl button[data-testid$="Active"] {{
    background: var(--text) !important; }}
.st-key-uebung_auswahl button[kind$="Active"] p,
.st-key-uebung_auswahl button[data-testid$="Active"] p {{ color: var(--karte) !important; font-weight: 600 !important; }}

/* ---------- Speicher-Button: einzige Akzentfarbe ---------- */
[class*="st-key-speichern"], [class*="st-key-speichern"] > div {{ width: 100% !important; }}
[class*="st-key-speichern"] button {{
    width: 100% !important; height: 54px; border: none !important; border-radius: 14px !important;
    background: var(--akzent) !important; box-shadow: none !important; transition: transform .1s ease, opacity .1s ease;
}}
[class*="st-key-speichern"] button p {{ color: #FFFFFF !important; font-size: 17px !important; font-weight: 600 !important; }}
[class*="st-key-speichern"] button:active {{ transform: scale(.97); opacity: .9; }}

.st-key-letzten_loeschen button {{ background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 8px 4px !important; min-height: 44px; }}
.st-key-letzten_loeschen button p {{ color: var(--grau) !important; font-size: 15px !important; }}

/* ---------- Maschinenfoto: komplett sichtbar ---------- */
.foto {{ width: 100%; height: 200px; max-height: 200px; border-radius: 14px; margin-bottom: 12px;
         overflow: hidden; background-color: var(--karte); box-shadow: var(--schatten);
         display: flex; align-items: center; justify-content: center; }}
.foto img {{ width: 100%; height: 100%; max-height: 200px; object-fit: contain !important;
             background-color: var(--karte); display: block; }}
.foto-leer {{ display: grid; justify-items: center; gap: 10px; color: var(--grau) !important;
              font-size: 13px; text-align: center; line-height: 1.5; }}

/* ---------- Kennzahlen ---------- */
.karte-kopf {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 16px; }}
.karte-label {{ color: var(--akzent) !important; font-size: 14px; font-weight: 600; }}
.karte-zeit {{ color: var(--grau) !important; font-size: 13px; white-space: nowrap; }}
.gross {{ font-size: 40px; font-weight: 600; letter-spacing: -.025em; line-height: 1; font-variant-numeric: tabular-nums; }}
.gross small, .messwert small, .widget-wert small, .aufteilung small {{ color: var(--grau) !important; font-weight: 500;
    margin-left: 3px; letter-spacing: 0; }}
.gross small {{ font-size: 17px; }}
.unterzeile {{ color: var(--grau) !important; font-size: 14px; margin-top: 8px; }}
.verlaufslinie {{ width: 100%; height: 56px; display: block; margin-top: 16px; }}
.aufteilung {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border-top: 1px solid var(--linie);
               margin-top: 16px; padding-top: 16px; }}
.aufteilung span {{ display: block; color: var(--grau) !important; font-size: 13px; }}
.aufteilung b {{ font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.aufteilung small {{ font-size: 13px; }}

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
.widget-kopf {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }}
.widget-name {{ font-weight: 600; line-height: 1.3; min-width: 0; }}
.widget-zeit {{ color: var(--grau) !important; font-size: 13px; flex: none; }}
.widget-wert {{ font-size: 28px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
.widget-wert small {{ font-size: 14px; }}
.widget-info {{ color: var(--grau) !important; font-size: 13px; }}
.leer {{ background: var(--karte); border-radius: 16px; padding: 16px; text-align: center;
         color: var(--grau) !important; font-size: 15px; line-height: 1.5; box-shadow: var(--schatten); }}

/* ---------- Ausklappbereich (1RM) als Kachel ---------- */
[data-testid="stExpander"] details {{ background: var(--karte) !important; border: none !important;
    border-radius: 16px !important; box-shadow: var(--schatten); }}
[data-testid="stExpander"] summary {{ padding: 16px !important; }}
[data-testid="stExpander"] summary p {{ font-weight: 600 !important; }}
[data-testid="stExpander"] summary svg {{ color: var(--grau) !important; fill: var(--grau) !important; }}
[data-testid="stExpanderDetails"] {{ padding: 0 16px 16px !important; }}

/* ---------- Flache iOS-Tabelle ---------- */
.zonen {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
.zonen td {{ padding: 12px 0; border-bottom: 1px solid var(--linie); color: var(--text);
             font-size: clamp(14px, 4vw, 17px); vertical-align: top; }}
.zonen tr:last-child td {{ border-bottom: none; }}
.zonen td:last-child {{ text-align: right; font-weight: 600; white-space: nowrap !important; }}
.zonen small {{ display: block; color: var(--grau) !important; font-size: 13px; margin-top: 2px; }}
.hinweis {{ color: var(--grau) !important; font-size: 13px !important; margin-top: 12px !important; }}

/* ---------- Makro-Zeilen ---------- */
.makro {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding: 12px 0;
          border-bottom: 1px solid var(--linie); }}
.makro:last-child {{ border-bottom: none; padding-bottom: 0; }}
.makro span {{ color: var(--text); font-size: clamp(14px, 4vw, 17px); }}
.makro b {{ font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap !important; }}
.makro small {{ color: var(--grau) !important; font-size: 14px; font-weight: 500; margin-left: 3px; }}

[data-testid="stToast"] {{ background: var(--karte) !important; border-radius: 14px !important; }}
@media (max-width: 480px) {{ .widgets {{ grid-template-columns: 1fr; }} }}
</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)


# ===============================================================
# 8) HILFSFUNKTIONEN
# ===============================================================
def zahl_format(wert: float, nachkommastellen=None) -> str:
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
    return f"Noch kein Foto.<br>Erwartet: bilder/{beispiel_dateiname(uebung['name'])}"


@st.cache_data
def bild_als_html(pfad: str) -> str:
    datei = Path(pfad)
    daten = base64.b64encode(datei.read_bytes()).decode()
    return f'<img src="data:image/{BILD_ENDUNGEN[datei.suffix.lower()]};base64,{daten}" alt="">'


def segment_control(optionen: list, zustand_key: str, widget_key: str, bei_aenderung=None) -> None:
    """iOS-Segmented-Control, das nie 'leer' werden kann."""
    st.session_state[widget_key] = st.session_state[zustand_key]

    def uebernehmen():
        neuer_wert = st.session_state[widget_key]
        if neuer_wert is not None:
            st.session_state[zustand_key] = neuer_wert
            if bei_aenderung:
                bei_aenderung()

    with st.container(key=f"segment_{widget_key}"):
        st.segmented_control(widget_key, optionen, key=widget_key, on_change=uebernehmen,
                             label_visibility="collapsed")


def trennlinie() -> None:
    st.markdown('<div class="trennlinie"></div>', unsafe_allow_html=True)


# ===============================================================
# 9) TRAINING: DATEN & LOGIK
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
    uebung = UEBUNG_NACH_NAME[uebung_name]
    st.session_state["aktuelle_uebung"] = uebung_name
    st.session_state["gruppe"] = uebung["gruppe"]
    wert_von_aussen_setzen("gewicht", letztes_gewicht(uebung))
    wert_von_aussen_setzen("wiederholungen", int(uebung["wdh"].split("–")[0]))


def naechste_offene_uebung(heute_df: pd.DataFrame) -> str:
    for uebung in ALLE_UEBUNGEN:
        if saetze_erledigt(heute_df, uebung["name"]) < uebung["saetze"]:
            return uebung["name"]
    return ALLE_UEBUNGEN[0]["name"]


def bei_uebung_angetippt() -> None:
    if st.session_state["uebung_auswahl"] is not None:
        uebung_waehlen(st.session_state["uebung_auswahl"])


def bei_satz_speichern() -> None:
    stepper_wert_uebernehmen("gewicht")            # falls direkt nach dem letzten Tippen gespeichert wird
    stepper_wert_uebernehmen("wiederholungen")
    uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]
    gewicht, wiederholungen = float(st.session_state["gewicht"]), int(round(st.session_state["wiederholungen"]))
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(TRAINING_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gruppe": uebung["gruppe"],
                                   "Uebung": uebung["name"], "Gewicht_kg": gewicht,
                                   "Wiederholungen": wiederholungen})
    st.session_state["meldung"] = f"{uebung['name']} · {zahl_format(gewicht)} kg × {wiederholungen}"
    st.session_state["pause_start"] = time.time()   # startet den 90-Sekunden-Pausentimer
    heute_df = heutige_saetze_laden()
    if saetze_erledigt(heute_df, uebung["name"]) >= uebung["saetze"]:
        uebung_waehlen(naechste_offene_uebung(heute_df))


def bei_letzten_satz_loeschen() -> None:
    alle = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    if not alle.empty:
        alle.iloc[:-1].to_csv(TRAINING_CSV, index=False, encoding="utf-8")
        st.session_state["meldung"] = "Letzter Satz gelöscht"


# ===============================================================
# 10) KÖRPERDATEN: DATEN & KALORIEN
# ===============================================================
def bei_koerpergewicht_speichern() -> None:
    stepper_wert_uebernehmen("koerpergewicht")
    gewicht = round(float(st.session_state["koerpergewicht"]), 1)
    datum, uhrzeit = jetzt_datum_uhrzeit()
    zeile_anhaengen(GEWICHT_CSV, {"Datum": datum, "Uhrzeit": uhrzeit, "Gewicht_kg": gewicht})
    st.session_state["meldung"] = f"Körpergewicht {zahl_format(gewicht, 1)} kg gespeichert"


def ernaehrungsplan_berechnen(gewicht_kg: float, groesse_cm: float, alter_jahre: int, pal: float) -> dict:
    """
    Mifflin-St. Jeor (Männer):
      Grundumsatz (BMR) = 10 × Gewicht(kg) + 6,25 × Größe(cm) − 5 × Alter(J) + 5
      Tagesbedarf (TDEE) = BMR × PAL
      Zielbedarf         = TDEE + 300 kcal (sauberer Muskelaufbau)
    Makros (bezogen auf den Zielbedarf):
      Protein = 2,0 g/kg  (4 kcal/g)   Fett = 0,8 g/kg  (9 kcal/g)
      Kohlenhydrate = restliche kcal / 4
    """
    grundumsatz = 10 * gewicht_kg + 6.25 * groesse_cm - 5 * alter_jahre + 5
    tagesbedarf = grundumsatz * pal
    zielbedarf = tagesbedarf + MUSKELAUFBAU_UEBERSCHUSS_KCAL
    protein_g = PROTEIN_G_PRO_KG * gewicht_kg
    fett_g = FETT_G_PRO_KG * gewicht_kg
    kohlenhydrate_g = max(0.0, (zielbedarf - protein_g * 4 - fett_g * 9) / 4)
    return {"grundumsatz": grundumsatz, "tagesbedarf": tagesbedarf, "zielbedarf": zielbedarf,
            "protein_g": protein_g, "fett_g": fett_g, "kohlenhydrate_g": kohlenhydrate_g}


# ===============================================================
# 10b) TRAININGS-FUNKTIONEN: Pausentimer, Fortschritts-Diagramm, 1RM
# ===============================================================
def pausentimer_html(start_zeitstempel: float, farben_dict: dict) -> str:
    """Countdown läuft im Browser: tickt jede Sekunde, ohne die App neu zu laden."""
    ende_ms = int((start_zeitstempel + PAUSE_SEKUNDEN) * 1000)
    return f"""
    <div id="timer" style="display:flex;justify-content:space-between;align-items:center;gap:16px;
         font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue','Segoe UI',Roboto,Arial,sans-serif;
         -webkit-font-smoothing:antialiased;">
      <span style="color:{farben_dict['grau']};font-size:clamp(14px,4vw,17px);">Satzpause</span>
      <b id="zeit" style="color:#FF9500;font-size:34px;font-weight:600;font-variant-numeric:tabular-nums;
         letter-spacing:-.02em;"></b>
    </div>
    <script>
      const ende = {ende_ms};
      const zeit = document.getElementById("zeit");
      function ticken() {{
        const rest = Math.max(0, Math.round((ende - Date.now()) / 1000));
        if (rest === 0) {{
          zeit.textContent = "Bereit für den nächsten Satz!";
          zeit.style.fontSize = "clamp(15px, 4.5vw, 19px)";
          zeit.style.color = "{farben_dict['text']}";
          return;
        }}
        zeit.textContent = Math.floor(rest / 60) + ":" + String(rest % 60).padStart(2, "0");
        setTimeout(ticken, 250);
      }}
      ticken();
    </script>
    <style>html,body{{margin:0;background:transparent;overflow:hidden}}</style>
    """


def fortschritt_diagramm_svg(uebung_name: str) -> str:
    """Höchstes Gewicht pro Trainingstag der gewählten Übung (letzte 12 Tage mit Training)."""
    alle = csv_laden(TRAINING_CSV, TRAINING_SPALTEN)
    verlauf = (alle[alle["Uebung"] == uebung_name].groupby("Datum")["Gewicht_kg"].max()
               .sort_index().tail(12))
    if len(verlauf) < 2:
        return ""
    werte, tage = verlauf.astype(float).tolist(), verlauf.index.tolist()
    kleinster, groesster = min(werte), max(werte)
    spanne = (groesster - kleinster) or 1
    breite, hoehe, rand_links, rand_rechts, oben, unten = 320, 150, 40, 12, 14, 26
    zeichen_breite = breite - rand_links - rand_rechts
    zeichen_hoehe = hoehe - oben - unten
    punkte = [(rand_links + i * zeichen_breite / (len(werte) - 1),
               oben + (1 - (w - kleinster) / spanne) * zeichen_hoehe) for i, w in enumerate(werte)]
    linie = " ".join(f"{x:.1f},{y:.1f}" for x, y in punkte)
    kreise = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{AKZENT}"/>' for x, y in punkte)
    datum_kurz = lambda iso: f"{iso[8:10]}.{iso[5:7]}."
    beschriftung = 'style="fill: var(--grau); font-size: 11px;"'
    return (
        f'<svg viewBox="0 0 {breite} {hoehe}" style="width:100%;height:auto;display:block" '
        f'role="img" aria-label="Gewichtsverlauf {html.escape(uebung_name)}">'
        f'<text x="0" y="{oben + 4}" {beschriftung}>{zahl_format(groesster)} kg</text>'
        f'<text x="0" y="{oben + zeichen_hoehe + 4}" {beschriftung}>{zahl_format(kleinster)} kg</text>'
        f'<polyline points="{linie}" fill="none" stroke="{AKZENT}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>{kreise}'
        f'<text x="{rand_links}" y="{hoehe - 6}" {beschriftung}>{datum_kurz(tage[0])}</text>'
        f'<text x="{breite - rand_rechts}" y="{hoehe - 6}" text-anchor="end" {beschriftung}>'
        f'{datum_kurz(tage[-1])}</text></svg>')


def auf_scheiben_runden(gewicht_kg: float) -> float:
    """Rundet auf 2,5-kg-Schritte, wie man sie an Geräten und Hanteln einstellt."""
    return round(gewicht_kg / 2.5) * 2.5


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
# 11) STARTZUSTAND + Eingaben der Komponenten übernehmen
# ===============================================================
heute_df = heutige_saetze_laden()
gewichte_df = csv_laden(GEWICHT_CSV, GEWICHT_SPALTEN)

if st.session_state.get("aktuelle_uebung") not in UEBUNG_NACH_NAME:
    uebung_waehlen(naechste_offene_uebung(heute_df))
if "bereich" not in st.session_state:
    st.session_state["bereich"] = "Training"
if "koerpergewicht" not in st.session_state:
    wert_von_aussen_setzen("koerpergewicht", float(gewichte_df["Gewicht_kg"].iloc[-1])
                           if not gewichte_df.empty else 80.0)   # Annahme: 80 kg

for stepper_feld in ("gewicht", "wiederholungen", "koerpergewicht"):
    stepper_wert_uebernehmen(stepper_feld)
koerperangaben_uebernehmen()

if "meldung" in st.session_state:
    st.toast(st.session_state.pop("meldung"))

# ===============================================================
# 12) KOPF: Datum, Hell/Dunkel, Titel, Reiter
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

# Breites iOS-Auswahlmenü ganz oben (ersetzt Titel und Gruppen-Tabs)
REITER_TRAINING, REITER_KOERPER = "🏋️‍♂️ Training", "📊 Körperdaten"
if st.session_state["bereich"] not in (REITER_TRAINING, REITER_KOERPER):
    st.session_state["bereich"] = REITER_TRAINING
segment_control([REITER_TRAINING, REITER_KOERPER], "bereich", "reiter")

# ===============================================================
# 13) REITER: TRAINING  (jedes Element = eigene Kachel)
# ===============================================================
if st.session_state["bereich"] == REITER_TRAINING:
    aktuelle_uebung = UEBUNG_NACH_NAME[st.session_state["aktuelle_uebung"]]

    # Kachel 1: Übung wählen (alle Übungen, voll ausgeschrieben)
    with st.container(key="karte_auswahl"):
        st.markdown('<p class="feld-label">Übung wählen</p>', unsafe_allow_html=True)
        st.session_state["uebung_auswahl"] = st.session_state["aktuelle_uebung"]

        def chip_text(name: str) -> str:
            fertig = saetze_erledigt(heute_df, name) >= UEBUNG_NACH_NAME[name]["saetze"]
            return f"✓ {name}" if fertig else name

        st.pills("Übung", [u["name"] for u in ALLE_UEBUNGEN], key="uebung_auswahl", format_func=chip_text,
                 on_change=bei_uebung_angetippt, label_visibility="collapsed")

    # Kachel 2: Foto der Maschine – immer komplett sichtbar
    bild_pfad = bild_pfad_finden(aktuelle_uebung)
    if bild_pfad:
        st.markdown(f'<div class="foto">{bild_als_html(bild_pfad)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="foto"><div class="foto-leer">{icon_html(ICON_HANTEL, "icon-gross")}'
                    f'{foto_fehlt_hinweis(aktuelle_uebung)}</div></div>', unsafe_allow_html=True)

    # Kachel 3: Name & Ziel
    satz_nummer = min(saetze_erledigt(heute_df, aktuelle_uebung["name"]) + 1, aktuelle_uebung["saetze"])
    tag_text = f' · {aktuelle_uebung["tag"]}' if aktuelle_uebung.get("tag") else ""
    st.markdown(f'<div class="karte"><p class="kopf-label">{icon_html(ICON_HANTEL)}{aktuelle_uebung["gruppe"]}{tag_text}</p>'
                f'<p class="kopf-name">{html.escape(aktuelle_uebung["name"])}</p>'
                f'<p class="kopf-ziel">Satz {satz_nummer} von {aktuelle_uebung["saetze"]} · '
                f'Ziel {aktuelle_uebung["wdh"]} Wiederholungen</p></div>', unsafe_allow_html=True)

    # Kachel 4 + 5: Gewicht und Wiederholungen (−  Zahl  + in einer Linie)
    with st.container(key="karte_gewicht_stepper"):
        stepper("gewicht", "Gewicht", "kg", schritt=2.5, minimum=0, maximum=500)
    with st.container(key="karte_wdh_stepper"):
        stepper("wiederholungen", "Wiederholungen", "", schritt=1, minimum=1, maximum=100)

    st.button("Satz speichern", key="speichern_satz", on_click=bei_satz_speichern)

    # FEATURE 1: Satzpausen-Timer (läuft im Browser, kein Neuladen der App)
    if "pause_start" in st.session_state:
        with st.container(key="karte_pause"):
            components.html(pausentimer_html(st.session_state["pause_start"], farben), height=44)

    # FEATURE 3: 1RM & Trainingszonen (Epley-Formel)
    with st.expander("💡 Trainings-Zonen Berechnen"):
        test_gewicht = float(st.session_state["gewicht"])
        test_wdh = int(round(st.session_state["wiederholungen"]))
        if test_gewicht <= 0:
            st.markdown('<p class="hinweis">Stell oben ein Gewicht ein, dann erscheinen hier deine Zonen.</p>',
                        unsafe_allow_html=True)
        else:
            maximalkraft = test_gewicht * (1 + test_wdh / 30)
            st.markdown(f"""
            <table class="zonen">
              <tr><td>Maximalkraft (1RM)<small>100 %</small></td><td>{zahl_format(auf_scheiben_runden(maximalkraft))} kg</td></tr>
              <tr><td>Muskelaufbau<small>75 % · ca. 8–12 Wiederholungen</small></td>
                  <td>{zahl_format(auf_scheiben_runden(maximalkraft * 0.75))} kg</td></tr>
              <tr><td>Kraftausdauer<small>60 % · ca. 15–20 Wiederholungen</small></td>
                  <td>{zahl_format(auf_scheiben_runden(maximalkraft * 0.60))} kg</td></tr>
            </table>
            <p class="hinweis">Basis: {zahl_format(test_gewicht)} kg × {test_wdh} Wiederholungen ·
               gerundet auf 2,5-kg-Schritte</p>""", unsafe_allow_html=True)

    # Kachel: Zusammenfassung
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

    # Verlauf heute als Widgets
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

    # FEATURE 2: Progressive Overload – Gewichtsverlauf der gewählten Übung
    st.markdown('<p class="abschnitt">Fortschritt</p>', unsafe_allow_html=True)
    diagramm = fortschritt_diagramm_svg(aktuelle_uebung["name"])
    inhalt = diagramm or ('<p class="unterzeile">Sobald du diese Übung an zwei verschiedenen Tagen '
                          'trainiert hast, erscheint hier dein Verlauf.</p>')
    st.markdown(f'<div class="karte"><div class="karte-kopf"><span class="karte-label">'
                f'{html.escape(aktuelle_uebung["name"])}</span><span class="karte-zeit">Höchstes Gewicht pro Tag'
                f'</span></div>{inhalt}</div>', unsafe_allow_html=True)

# ===============================================================
# 14) REITER: KÖRPERDATEN
# ===============================================================
else:
    # Kachel: aktuelles Körpergewicht
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

    # Kachel: Gewicht eintragen
    with st.container(key="karte_gewicht"):
        stepper("koerpergewicht", "Körpergewicht", "kg", schritt=0.1, minimum=30, maximum=300, nachkomma=1)
    st.button("Gewicht speichern", key="speichern_gewicht", on_click=bei_koerpergewicht_speichern)

    # Kachel: Kalorienbedarf (nur das Ergebnis)
    st.markdown('<p class="abschnitt">Kalorienbedarf</p>', unsafe_allow_html=True)
    rechen_gewicht = (float(gewichte_df["Gewicht_kg"].iloc[-1]) if not gewichte_df.empty
                      else float(st.session_state["koerpergewicht"]))
    grundumsatz, gesamtbedarf = kalorienbedarf_harris_benedict(
        rechen_gewicht, st.session_state["groesse"], st.session_state["alter"],
        PAL_STUFEN[st.session_state["pal_stufe"]])

    st.markdown(f"""
    <div class="karte">
      <div class="karte-kopf"><span class="karte-label">Täglicher Bedarf</span><span class="karte-zeit">Heute</span></div>
      <div class="gross">{tausender(gesamtbedarf)}<small>kcal</small></div>
      <div class="aufteilung">
        <div><span>Grundumsatz</span><b>{tausender(grundumsatz)}<small>kcal</small></b></div>
        <div><span>Aktivität</span><b>{st.session_state["pal_stufe"]}</b></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Kachel: Angaben (iOS-Scrollrad + Aktivität)
    with st.container(key="karte_angaben"):
        st.markdown('<p class="feld-label">Deine Angaben</p>', unsafe_allow_html=True)
        ios_eingabe(art="walzen", token=0, farben=KOMPONENTEN_FARBEN, key="walzen_koerper", default=None,
                    felder=[
                        {"key": "alter", "label": "Alter", "min": 14, "max": 90, "einheit": "Jahre",
                         "wert": int(st.session_state["alter"])},
                        {"key": "groesse", "label": "Größe", "min": 140, "max": 220, "einheit": "cm",
                         "wert": int(st.session_state["groesse"])},
                    ])
    with st.container(key="karte_aktivitaet"):
        st.markdown('<p class="feld-label">Aktivität</p>', unsafe_allow_html=True)
        segment_control(list(PAL_STUFEN), "pal_stufe", "pal_auswahl", bei_aenderung=einstellungen_speichern)
