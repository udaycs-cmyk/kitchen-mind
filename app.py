import streamlit as st
# (Other imports remain the same, keeping them for backend functionality)
import google.genai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import json
import datetime
import uuid
import time
import requests
import re
import math
import io

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="Kitchen Mind", # Removed "Pro" for a friendlier feel
    page_icon="🍊", # Switched to a friendly fruit emoji
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. JOYFUL HUMANISM DESIGN SYSTEM (CSS) ---
def local_css():
    st.markdown("""
    <style>
        /* --- TYPOGRAPHY IMPORT --- */
        /* Importing Fredoka for that rounded, friendly geometry */
        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');

        /* --- COLOR PALETTE & BASE THEME --- */
        :root {
            --bg-oatmeal: #FDF5EB;
            --text-dark-brown: #3E322C;
            --text-medium-brown: #7A685F;
            --accent-coral: #FF8C69;
            --accent-coral-hover: #E87B5A;
            --card-white: #FFFFFF;
            --soft-mint: #D7EBE3;
            --soft-yellow: #FBE7C0;
            --soft-shadow: 0 12px 24px rgba(62, 50, 44, 0.08);
        }

        /* --- GLOBAL RESETS --- */
        .stApp {
            background-color: var(--bg-oatmeal);
            font-family: 'Fredoka', sans-serif;
            color: var(--text-dark-brown);
        }
        
        /* Overriding Streamlit text colors */
        h1, h2, h3, h4, h5, h6, p, div, span, label {
            color: var(--text-dark-brown) !important;
            font-family: 'Fredoka', sans-serif !important;
        }

        h1 { font-weight: 700; letter-spacing: -0.02em; }
        h3 { font-weight: 600; color: var(--text-medium-brown) !important; }
        p.caption { color: var(--text-medium-brown) !important; font-size: 0.95rem;}

        /* Hide standard elements */
        [data-testid="stSidebar"] { display: none; }
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* --- SHAPE LANGUAGE: EXTREME ROUNDING --- */
        
        /* Inputs */
        div[data-baseweb="input"] {
            background-color: var(--card-white) !important;
            border: 2px solid transparent !important;
            border-radius: 24px !important;
            box-shadow: var(--soft-shadow) !important;
            padding: 5px;
            transition: all 0.3s ease;
        }
        /* Focus state for inputs - playful border */
        div[data-baseweb="input"]:focus-within {
            border-color: var(--accent-coral) !important;
        }
        input, textarea {
            color: var(--text-dark-brown) !important;
            caret-color: var(--accent-coral) !important;
            font-family: 'Fredoka', sans-serif !important;
        }

        /* Buttons - The biggest change. Soft blobs. */
        div.stButton > button {
            background-color: var(--accent-coral) !important;
            color: white !important;
            border-radius: 30px !important; /* Extreme rounding */
            border: none !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
            padding: 0.75rem 2rem !important;
            box-shadow: 0 8px 16px rgba(255, 140, 105, 0.3);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        div.stButton > button:hover {
            transform: translateY(-3px) scale(1.02);
            background-color: var(--accent-coral-hover) !important;
            box-shadow: 0 12px 20px rgba(255, 140, 105, 0.4);
        }
        /* Secondary buttons (if needed later) could use the mint/yellow colors */

        /* --- CUSTOM JOYFUL CARDS --- */
        .joyful-card {
            background-color: var(--card-white);
            border-radius: 32px; /* Super round corners */
            padding: 30px;
            box-shadow: var(--soft-shadow);
            border: 2px solid #F8F0E6; /* Subtle definition */
            text-align: center;
            height: 100%;
            transition: transform 0.3s ease;
        }
        .joyful-card:hover {
             transform: translateY(-5px);
        }
        
        /* Specific card themes for visual variety */
        .card-mint { background-color: var(--soft-mint); }
        .card-yellow { background-color: var(--soft-yellow); }

        /* --- TAB STYLING (Softening the tabs) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
            border-bottom: none;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            border-radius: 25px;
            background-color: rgba(255,255,255,0.5);
            color: var(--text-medium-brown);
            font-weight: 600;
            border: none !important;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: var(--accent-coral) !important;
            color: white !important;
        }

        /* --- UTILITIES --- */
        .illustration-container {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }
        /* Center column content nicely */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# --- [KEEP YOUR EXISTING API/DB SETUP HERE] ---
# (Mocking DB for UI demonstration)
if 'user_info' not in st.session_state: st.session_state.user_info = {"household_id": "JOYFUL_HOME"}
if 'current_page' not in st.session_state: st.session_state.current_page = 'home'
hh_id = st.session_state.user_info['household_id']

# --- CUSTOM VECTORS (The "Bean" Illustrations) ---
# These replace stock photos/generic icons with on-brand, flat, rounded illustrations.

def get_hero_scan_svg():
    return """
    <svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="90" cy="80" r="70" fill="#FBE7C0"/>
        <path d="M125.5 64.5C125.5 86.8675 107.368 105 85 105C62.6325 105 44.5 86.8675 44.5 64.5C44.5 42.1325 62.6325 24 85 24C107.368 24 125.5 42.1325 125.5 64.5Z" fill="#FF8C69"/>
        <circle cx="75" cy="58" r="6" fill="#3E322C"/> <circle cx="95" cy="58" r="6" fill="#3E322C"/>
        <path d="M80 72 Q85 78 90 72" stroke="#3E322C" stroke-width="3" stroke-linecap="round"/>
        <rect x="60" y="95" width="50" height="40" rx="12" fill="white" stroke="#3E322C" stroke-width="3"/>
        <circle cx="85" cy="115" r="12" stroke="#FF8C69" stroke-width="3"/>
    </svg>
    """

def get_pantry_svg():
    return """
    <svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="80" height="80" rx="20" fill="#D7EBE3"/>
        <path d="M15 40 H85" stroke="white" stroke-width="4" stroke-linecap="round"/>
        <path d="M15 70 H85" stroke="white" stroke-width="4" stroke-linecap="round"/>
        <circle cx="35" cy="28" r="10" fill="#FF8C69"/>
        <rect x="55" y="18" width="20" height="20" rx="6" fill="#F4D06F"/>
        <circle cx="65" cy="55" r="12" fill="#AED9C5"/>
    </svg>
    """

def get_cart_svg():
    return """
    <svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="80" height="80" rx="20" fill="#FBE7C0"/>
        <rect x="30" y="5" width="40" height="15" rx="7.5" fill="#7A685F"/>
        <rect x="25" y="35" width="50" height="8" rx="4" fill="white"/>
        <circle cx="35" cy="39" r="3" fill="#FF8C69"/>
        <rect x="25" y="55" width="50" height="8" rx="4" fill="white"/>
        <circle cx="35" cy="59" r="3" fill="#FF8C69"/>
         <rect x="25" y="75" width="30" height="8" rx="4" fill="white" opacity="0.5"/>
    </svg>
    """

# --- MAIN NAVIGATION & PAGE ROUTING ---
def main():
    local_css()
    
    # We use tabs for navigation, adapted to the new soft style
    # Using emojis that match the friendly vibe
    tab_home, tab_stock, tab_cart = st.tabs([
        "🍊 Home", 
        "📦 Pantry", 
        "🛒 List"
    ])

    with tab_home:
         page_home_joyful()
    with tab_stock:
         # (Placeholders for future redesigns of these pages)
         st.title("Pantry View")
         st.info("Your joyful pantry redesign is coming soon.")
    with tab_cart:
         st.title("Shopping List")
         st.info("Your mindful shopping list is coming soon.")


# --- THE NEW JOYFUL HOME DASHBOARD ---
def page_home_joyful():
    # Spacing blocker for the top
    st.write("")
    st.write("")

    # 1. Warm Greeting Header
    st.markdown("# Good morning!")
    st.markdown("### Let's nourish your home today.")
    st.write("") # Spacer

    # 2. The Hero Action Card (Scanning is the primary focus)
    # Using containers with custom classes for the new look
    with st.container():
        st.markdown('<div class="joyful-card">', unsafe_allow_html=True)
        
        # Layout: Illustration on left, CTA on right (desktop) / stacked (mobile)
        c_hero_img, c_hero_cta = st.columns([2, 3])
        
        with c_hero_img:
             st.markdown(f'<div class="illustration-container">{get_hero_scan_svg()}</div>', unsafe_allow_html=True)
        
        with c_hero_cta:
            st.write("") # Vertical centering spacer
            st.markdown("<h2>Add new items to your kitchen.</h2>", unsafe_allow_html=True)
            st.markdown('<p class="caption">Snap a photo. Our friendly AI will handle the details.</p>', unsafe_allow_html=True)
            st.write("")
            # The primary action button - now a soft coral blob
            if st.button("✨ Start Scanning", use_container_width=True):
                st.toast("Opening the scanner gently...")
                # Add navigation logic here
        
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("") # Spacer between sections

    # 3. Secondary Actions Grid (Pantry & Cart)
    c_pantry, c_cart = st.columns(2)

    with c_pantry:
        # A mint-colored themed card
        st.markdown('<div class="joyful-card card-mint">', unsafe_allow_html=True)
        st.markdown(f'<div class="illustration-container">{get_pantry_svg()}</div>', unsafe_allow_html=True)
        st.markdown("<h3>My Pantry</h3>", unsafe_allow_html=True)
        st.markdown('<p class="caption">See what you have in stock.</p>', unsafe_allow_html=True)
        if st.button("View Pantry", key="btn_pantry", use_container_width=True):
             st.toast("Heading to the pantry.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_cart:
        # A soft-yellow themed card
        st.markdown('<div class="joyful-card card-yellow">', unsafe_allow_html=True)
        st.markdown(f'<div class="illustration-container">{get_cart_svg()}</div>', unsafe_allow_html=True)
        st.markdown("<h3>Shopping List</h3>", unsafe_allow_html=True)
        st.markdown('<p class="caption">Items you need to replenish.</p>', unsafe_allow_html=True)
        if st.button("View List", key="btn_cart", use_container_width=True):
             st.toast("Opening shopping list.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. Subtle Footer/Quote
    st.write("")
    st.write("")
    st.markdown('<div style="text-align: center; opacity: 0.6;">Let food be thy medicine and medicine be thy food.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
