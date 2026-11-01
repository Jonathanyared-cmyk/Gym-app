import streamlit as st
import os
import pandas as pd
from pathlib import Path

# Seite konfigurieren
st.set_page_config(
    page_title="Gym App",
    page_icon="🏋️‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Pfade für Daten und Bilder
DATA_FILE = "training_data.csv"
WEIGHT_FILE = "weight_data.csv"
IMAGE_DIR = Path(__file__).parent / "gym Bilder"

# Initialisiere Dateien falls nicht existent
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["Datum", "Übung", "Gewicht", "Wiederholungen"]).to_csv(DATA_FILE, index=False)
if not os.path.exists(WEIGHT_FILE):
    pd.DataFrame(columns=["Datum", "Gewicht", "Größe", "Alter", "Aktivität", "Kalorien"]).to_csv(WEIGHT_FILE, index=False)

# CSS für radikalen Apple Health iOS 18 Look injizieren
# Entfernt alle Streamlit-Klobigkeiten und baut echte iOS 18 UI Cards
st.markdown("""
    <style>
    /* Streamlit Defaults komplett ausblenden */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif !important;
    }
    
    /* Globaler Container */
    .ios-container {
        max-width: 480px;
        margin: 0 auto;
        padding: 16px;
    }
    
    /* Apple iOS 18 Segmented Control (Navigation) */
    .segmented-control {
        display: flex;
        background-color: #1C1C1E;
        border-radius: 9px;
        padding: 2px;
        margin-bottom: 24px;
    }
    .segmented-item {
        flex: 1;
        text-align: center;
        padding: 8px 0;
        font-size: 14px;
        font-weight: 500;
        border-radius: 7px;
        cursor: pointer;
        color: #8E8E93;
        transition: all 0.2s ease;
    }
    .segmented-item.active {
        background-color: #2C2C2E;
        color: #FFFFFF;
        font-weight: 600;
    }
    
    /* Apple UI Cards */
    .ios-card {
        background-color: #1C1C1E;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        border: none;
    }
    
    .card-title {
        color: #8E8E93;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    /* Formularelemente iOS-Style */
    .ios-label {
        font-size: 14px;
        font-weight: 500;
        color: #AEAEB2;
        margin-bottom: 6px;
    }
    
    /* Verstecke klobige Streamlit Selectbox Ränder */
    div[data-baseweb="select"] {
        background-color: #2C2C2E !important;
        border-radius: 10px !important;
        border: none !important;
    }
    div[data-baseweb="select"] * {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }
    
    /* Custom Stepper (Plus/Minus in einer Zeile) */
    .stepper-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #2C2C2E;
        border-radius: 12px;
        padding: 8px 16px;
        margin-bottom: 16px;
    }
    .stepper-value {
        font-size: 24px;
        font-weight: 700;
        color: #FFFFFF;
    }
    
    /* Große Metriken wie Apple Health */
    .health-metric {
        font-size: 36px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .health-unit {
        font-size: 16px;
        font-weight: 500;
        color: #FF2D55;
    }
    
    /* Primärer iOS Button */
    .stButton>button {
        width: 100% !important;
        background-color: #FF2D55 !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 14px !important;
        border-radius: 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        transition: transform 0.1s ease, background-color 0.2s !important;
    }
    .stButton>button:active {
        transform: scale(0.97) !important;
    }
    
    /* Native iOS Selection Wheel simulieren */
    select.ios-wheel {
        width: 100%;
        background-color: #2C2C2E;
        color: white;
        border: none;
        padding: 12px;
        border-radius: 10px;
        font-size: 16px;
        font-family: inherit;
        appearance: none;
        background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%238E8E93' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        background-size: 16px;
    }
    
    /* Bilder-Rahmen fixieren */
    .image-container {
        width: 100%;
        max-height: 220px;
        background-color: #1C1C1E;
        border-radius: 14px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
    }
    .image-container img {
        max-height: 220px;
        width: 100%;
        object-fit: contain !important;
    }
    </style>
""", unsafe_allow_html=True)

# Gesamten App-Content in iOS-Kapsel rendern
st.markdown('<div class="ios-container">', unsafe_allow_html=True)

# Navigation via nativer Streamlit state, aber versteckt gesteuert
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "🏋️‍♂️ Training"

# Styling für simulierten iOS-Tab-Wechsler oben
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🏋️‍♂️ Training", key="btn_train"):
        st.session_state.current_tab = "🏋️‍♂️ Training"
with col_nav2:
    if st.button("📊 Körperdaten", key="btn_body"):
        st.session_state.current_tab = "📊 Körperdaten"

# Trainingsplan-Definitionen
TRAININGSPLAN = {
    "Push / Brust & Schultern": ["Brustpresse", "Schulterdrücken", "Flys", "Trizepsdrücken"],
    "Pull / Rücken & Bizeps": ["Latzug", "Rudern an der Maschine", "Hyperextensions", "Bizepscurls"],
    "Legs / Beine": ["Kniebeugen", "Beinpresse", "Beinstrecker", "Wadenheben"]
}

if st.session_state.current_tab == "🏋️‍♂️ Training":
    st.markdown('<div class="ios-card"><div class="card-title">Übungs-Auswahl</div>', unsafe_allow_html=True)
    
    # Flaches Dropdown ohne Suchen-Zwang
    kategorie = st.selectbox("Kategorie", list(TRAININGSPLAN.keys()), label_visibility="collapsed")
    uebung = st.selectbox("Übung", TRAININGSPLAN[kategorie])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bild-Logik (100% sauber gecapped)
    # Bildname erzeugen aus Kleinbuchstaben, keine Umlaute
    img_name = uebung.lower().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe").replace(" ", "") + ".svg"
    img_path = IMAGE_DIR / img_name
    
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    if img_path.exists():
        st.image(str(img_path))
    else:
        # Eleganter Apple Platzhalter, falls SVG noch nicht geladen ist
        st.markdown(f'<div style="color: #8E8E93; font-size: 14px; padding: 40px; text-align: center;">📷 Bild für {uebung} wird geladen...</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Custom Stepper für Gewicht und Wiederholungen (Echtes Flexbox)
    st.markdown('<div class="ios-card"><div class="card-title">Trainingswerte</div>', unsafe_allow_html=True)
    
    # Gewicht Stepper
    if "weight_val" not in st.session_state: st.session_state.weight_val = 50.0
    st.markdown('<div class="ios-label">Gewicht</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c1:
        if st.button("➖", key="w_minus"): st.session_state.weight_val = max(0.0, st.session_state.weight_val - 2.5)
    with c2:
        st.markdown(f'<div class="stepper-container" style="margin-bottom:0px; justify-content:center;"><span class="stepper-value">{st.session_state.weight_val} <span style="font-size:16px; color:#8E8E93;">kg</span></span></div>', unsafe_allow_html=True)
    with c3:
        if st.button("➕", key="w_plus"): st.session_state.weight_val += 2.5
        
    st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
        
    # Wiederholungen Stepper
    if "reps_val" not in st.session_state: st.session_state.reps_val = 10
    st.markdown('<div class="ios-label">Wiederholungen</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1,2,1])
    with r1:
        if st.button("➖", key="r_minus"): st.session_state.reps_val = max(1, st.session_state.reps_val - 1)
    with r2:
        st.markdown(f'<div class="stepper-container" style="margin-bottom:0px; justify-content:center;"><span class="stepper-value">{st.session_state.reps_val} <span style="font-size:16px; color:#8E8E93;">Reps</span></span></div>', unsafe_allow_html=True)
    with r3:
        if st.button("➕", key="r_plus"): st.session_state.reps_val += 1
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Einloggen Button
    if st.button("Training loggen"):
        new_row = pd.DataFrame([{"Datum": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Übung": uebung, "Gewicht": st.session_state.weight_val, "Wiederholungen": st.session_state.reps_val}])
        new_row.to_csv(DATA_FILE, mode='a', header=False, index=False)
        st.markdown('<p style="color: #8E8E93; font-size: 13px; text-align: center; margin-top: 8px;">✓ Erfolgreich in Health-Daten gesichert</p>', unsafe_allow_html=True)

elif st.session_state.current_tab == "📊 Körperdaten":
    st.markdown('<div class="ios-card"><div class="card-title">Meine Vitalwerte</div>', unsafe_allow_html=True)
    
    # Echtes iOS Selection Wheel für Alter & Größe simulieren über st.selectbox
    st.markdown('<div class="ios-label">Körpergröße (cm)</div>', unsafe_allow_html=True)
    groesse = st.selectbox("Größe", list(range(140, 220)), index=40, label_visibility="collapsed")
    
    st.markdown('<div class="ios-label" style="margin-top:15px;">Alter (Jahre)</div>', unsafe_allow_html=True)
    alter = st.selectbox("Alter", list(range(14, 80)), index=6, label_visibility="collapsed")
    
    st.markdown('<div class="ios-label" style="margin-top:15px;">Aktuelles Gewicht (kg)</div>', unsafe_allow_html=True)
    if "body_weight" not in st.session_state: st.session_state.body_weight = 75.0
    bw1, bw2, bw3 = st.columns([1,2,1])
    with bw1:
        if st.button("➖", key="bw_minus"): st.session_state.body_weight = max(30.0, st.session_state.body_weight - 0.5)
    with bw2:
        st.markdown(f'<div class="stepper-container" style="margin-bottom:0px; justify-content:center;"><span class="stepper-value">{st.session_state.body_weight} <span style="font-size:16px; color:#8E8E93;">kg</span></span></div>', unsafe_allow_html=True)
    with bw3:
        if st.button("➕", key="bw_plus"): st.session_state.body_weight += 0.5
        
    st.markdown('<div class="ios-label" style="margin-top:15px;">Aktivitätslevel</div>', unsafe_allow_html=True)
    aktivitaet = st.selectbox("Aktivität", ["Wenig aktiv (Sitzend)", "Moderat (1-3x Training)", "Sehr aktiv (3-5x Gym)"], index=2, label_visibility="collapsed")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Exakter medizinischer Kalorien-Rechner (Mifflin-St. Jeor)
    bmr = (10 * st.session_state.body_weight) + (6.25 * groesse) - (5 * alter) + 5
    
    if "Sehr aktiv" in aktivitaet: pal = 1.55
    elif "Moderat" in aktivitaet: pal = 1.375
    else: pal = 1.2
    
    tdee = int(bmr * pal)
    muskelaufbau = tdee + 300
    
    # Makros berechnen für sauberen Aufbau (2g Protein, 0.8g Fett)
    protein = int(st.session_state.body_weight * 2.0)
    fett = int(st.session_state.body_weight * 0.8)
    rest_cal = muskelaufbau - (protein * 4) - (fett * 9)
    carbs = int(max(0, rest_cal / 4))
    
    # Wunderschöne, ultra-moderne Apple Health Ausgabekacheln
    st.markdown(f'''
    <div class="ios-card">
        <div class="card-title">Tagesbedarf zum Halten</div>
        <div class="health-metric">{tdee} <span class="health-unit">kcal / Tag</span></div>
    </div>
    
    <div class="ios-card" style="border-left: 4px solid #FF2D55;">
        <div class="card-title" style="color: #FF2D55;">Zielbedarf Muskelaufbau (+300 kcal)</div>
        <div class="health-metric">{muskelaufbau} <span class="health-unit">kcal / Tag</span></div>
    </div>
    
    <div class="ios-card">
        <div class="card-title">Makronährstoff-Ziele am Tagesende</div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px;">
            <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: 700; color: #FFFFFF;">{protein}g</div>
                <div style="font-size: 12px; color: #8E8E93;">Protein</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: 700; color: #FFFFFF;">{carbs}g</div>
                <div style="font-size: 12px; color: #8E8E93;">Kohlenhydrate</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 18px; font-weight: 700; color: #FFFFFF;">{fett}g</div>
                <div style="font-size: 12px; color: #8E8E93;">Fett</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
