import streamlit as st
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

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="RE:STOCK Pro",
    page_icon="https://cdn-icons-png.flaticon.com/512/2921/2921822.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (CLEAN MOBILE APP THEME) ---
def local_css():
    st.markdown("""
    <style>
        /* 1. RESET & BASICS */
        .stApp {
            background-color: #F7F9FC; /* Light gray background like modern apps */
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* 2. HIDE DEFAULT STREAMLIT ELEMENTS */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stSidebar"] {display: none;} /* Hide sidebar completely for "App" feel */

        /* 3. PRODUCT CARD STYLING */
        /* We will use st.container(border=True) and style it here */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white;
            border-radius: 12px;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            padding: 10px !important;
            transition: transform 0.1s;
        }
        
        /* 4. TYPOGRAPHY */
        h3 { font-size: 16px !important; font-weight: 600 !important; margin-bottom: 0px !important; color: #333; }
        p { font-size: 14px !important; color: #666; margin-bottom: 5px !important; }
        .price-tag { font-size: 18px; font-weight: 800; color: #111; }
        
        /* 5. ADD BUTTON (Green Circle) */
        div.stButton > button {
            background-color: #2E7D32 !important; /* Green like the reference */
            color: white !important;
            border-radius: 50px !important;
            border: none !important;
            font-weight: bold;
            height: 35px;
            padding: 0px 15px;
        }
        div.stButton > button:hover {
            background-color: #1B5E20 !important;
        }

        /* 6. TOP NAVIGATION BAR */
        .nav-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: white;
            z-index: 1000;
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nav-title {
            font-size: 20px;
            font-weight: 700;
            color: #333;
        }
        
        /* Adjust top padding so content isn't hidden behind fixed nav */
        .block-container { padding-top: 5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [KEEP YOUR API & DB SETUP HERE] ---
# (I am mocking the DB call for the UI demo, keep your original code here)
if "user_info" not in st.session_state: st.session_state.user_info = {"household_id": "DEMO123"} 

# --- HELPER: PRODUCT CARD ---
def render_product_card(item):
    """
    Renders a single item as a card, similar to the reference image.
    """
    with st.container(border=True): # This creates the white card box
        # 1. Image Area (Placeholder logic)
        # In a real app, you'd show item.get('image_url')
        st.markdown(
            f"""
            <div style="height: 100px; background-color: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">
                <span style="font-size: 40px;">🥗</span>
            </div>
            """, unsafe_allow_html=True
        )
        
        # 2. Details
        st.markdown(f"### {item['item_name']}")
        st.markdown(f"{item.get('weight', '1')} {item.get('weight_unit', 'unit')}")
        
        # 3. Price & Action Row
        c1, c2 = st.columns([2, 1])
        with c1:
            # Mocking price as it wasn't in original schema, usually you'd pull this from DB
            st.markdown(f"<div class='price-tag'>$3.99</div>", unsafe_allow_html=True)
        with c2:
            if st.button("➕", key=f"btn_{item['id']}"):
                st.toast(f"Added {item['item_name']}")
                # Add your DB update logic here

# --- MAIN APP LAYOUT ---
def main():
    local_css()
    
    # 1. Custom Top Bar (Mimics Mobile App Header)
    st.markdown("""
        <div class="nav-container">
            <div class="nav-title">📍 1200 Mercer Street</div>
            <div>👤 🛒</div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Categories (Horizontal Scroll Simulation)
    st.markdown("**Categories**")
    cat_cols = st.columns(4)
    with cat_cols[0]: st.button("🥦 Fresh", use_container_width=True)
    with cat_cols[1]: st.button("🥩 Meat", use_container_width=True)
    with cat_cols[2]: st.button("🥛 Dairy", use_container_width=True)
    with cat_cols[3]: st.button("🥖 Bakery", use_container_width=True)
    
    st.write("") # Spacer

    # 3. The Grid Layout (The key to the "App" look)
    st.markdown("### Your Items")
    
    # Mock Data (Replace this with your `db.collection...` fetch)
    items = [
        {"id": "1", "item_name": "Whole Milk", "weight": "1", "weight_unit": "gal"},
        {"id": "2", "item_name": "Eggs Large", "weight": "12", "weight_unit": "count"},
        {"id": "3", "item_name": "Bananas", "weight": "2", "weight_unit": "lb"},
        {"id": "4", "item_name": "Sourdough", "weight": "1", "weight_unit": "loaf"},
        {"id": "5", "item_name": "Chicken Breast", "weight": "1.5", "weight_unit": "lb"},
        {"id": "6", "item_name": "Spinach", "weight": "10", "weight_unit": "oz"},
    ]
    
    # Create the Grid: Loop through items and place them in columns
    # We use 2 columns to match the reference image's mobile view
    cols = st.columns(2) 
    
    for i, item in enumerate(items):
        with cols[i % 2]: # Alternates between column 0 and column 1
            render_product_card(item)

    # 4. Sticky Bottom Nav (Visual Simulation)
    # Streamlit cannot do a real sticky bottom nav easily without extra plugins,
    # but we can put it at the bottom of the script.
    st.markdown("---")
    nav_cols = st.columns(3)
    with nav_cols[0]: st.button("🏠 Home", use_container_width=True)
    with nav_cols[1]: st.button("🔍 Search", use_container_width=True)
    with nav_cols[2]: st.button("🧾 Orders", use_container_width=True)

if __name__ == "__main__":
    main()
