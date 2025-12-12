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
st.set_page_config(page_title="KitchenMind Pro", page_icon="🥗", layout="wide")

# --- CUSTOM CSS ---
def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; font-family: 'Helvetica Neue', sans-serif; }
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, div, span { color: #333333 !important; }
        div[data-baseweb="input"] { background-color: #FFFFFF !important; border: 1px solid #E0E0E0 !important; border-radius: 10px !important; }
        input { color: #333333 !important; -webkit-text-fill-color: #333333 !important; caret-color: #333333 !important; }
        div.stButton > button {
            background-color: #43A047 !important; color: white !important; border-radius: 15px !important;
            padding: 15px 24px !important; font-weight: 600 !important; width: 100%; border: none !important;
        }
        div.stButton > button:hover { background-color: #2E7D32 !important; box-shadow: 0 4px 10px rgba(67, 160, 71, 0.2); }
        .new-badge { background-color: #FF5722; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7em; font-weight: bold; }
        .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- API & DATABASE ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "PASTE_YOUR_LOCAL_KEY_HERE"

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.warning(f"⚠️ Gemini API Warning: {e}")

if not firebase_admin._apps:
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
    else:
        try:
            cred = credentials.Certificate("firebase_key.json")
        except:
            st.error("❌ Firebase Key not found.")
            st.stop()
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- HELPER: BARCODE FETCH & PARSE ---
def fetch_barcode_data(barcode):
    if not barcode or len(barcode) < 5: return None
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('status') == 1:
            p = data['product']
            raw_qty = p.get('quantity', '')
            weight_val = 0.0
            unit_val = 'count'
            if raw_qty:
                match = re.match(r"([0-9.]+)\s*([a-zA-Z]+)", raw_qty)
                if match:
                    try:
                        weight_val = float(match.group(1))
                        unit_val = match.group(2).lower()
                    except: pass
            return {
                "item_name": p.get('product_name', ''),
                "notes": p.get('brands', ''),
                "weight": weight_val,
                "weight_unit": unit_val
            }
    except: return None
    return None

# --- 2. MAIN NAVIGATION ---
def main():
    local_css()
    if 'user_info' not in st.session_state: st.session_state.user_info = None
    if 'current_page' not in st.session_state: st.session_state.current_page = 'home'

    if not st.session_state.user_info:
        login_signup_screen()
    else:
        sidebar_nav()
        page = st.session_state.current_page
        hh_id = st.session_state.user_info['household_id']
        
        if page == 'home': page_home_dashboard(hh_id)
        elif page == 'kitchen_mind_pro': page_kitchen_mind_pro(hh_id)
        elif page == 'manual_add': page_manual_add(hh_id)
        elif page == 'inventory': page_inventory(hh_id)
        elif page == 'shopping_list': page_shopping_list(hh_id)

def sidebar_nav():
    with st.sidebar:
        st.title("🥗 KitchenMind")
        if st.button("🏠 Home"):
            st.session_state.current_page = 'home'
            st.rerun()
        st.divider()
        st.caption(f"ID: {st.session_state.user_info['household_id']}")
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.session_state.current_page = 'home'
            st.rerun()

# --- 3. LOGIN SCREEN ---
def login_signup_screen():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🥗 KitchenMind")
        st.caption("Smart Inventory")
        tab1, tab2 = st.tabs(["Login", "Create Household"])
        with tab1:
            with st.form("login"):
                email = st.text_input("Email").lower().strip()
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    users = db.collection('users').where('email', '==', email).where('password', '==', password).stream()
                    user = next(users, None)
                    if user:
                        st.session_state.user_info = user.to_dict()
                        st.session_state.current_page = 'home'
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            st.write("New?")
            new_email = st.text_input("New Email").lower().strip()
            new_pass = st.text_input("New Password", type="password")
            mode = st.radio("Mode", ["Create New", "Join Existing"])
            hh_input = st.text_input("Household ID / Name")
            if st.button("Start"):
                if not new_email or not new_pass: return
                hh_id = str(uuid.uuid4())[:6].upper()
                if mode == "Create New":
                    db.collection('households').document(hh_id).set({"name": hh_input, "id": hh_id})
                    db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_id})
                    st.success(f"Created! ID: {hh_id}")
                else:
                    db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_input})
                    st.success("Joined!")

# --- 4. HOME DASHBOARD ---
def page_home_dashboard(hh_id):
    st.title(f"👋 Welcome")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📸 KitchenMind Pro <span class='new-badge'>NEW</span>", unsafe_allow_html=True)
        if st.button("Launch Scanner 🚀"):
            st.session_state.current_page = 'kitchen_mind_pro'
            st.rerun()
    with col2:
        st.markdown("### 📝 Manual Add")
        if st.button("Add Item ✍️"):
            st.session_state.current_page = 'manual_add'
            st.rerun()
    st.write("")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("### 📦 Inventory")
        if st.button("View Kitchen 🥬"):
            st.session_state.current_page = 'inventory'
            st.rerun()
    with col4:
        st.markdown("### 🛒 Shopping List")
        if st.button("Go to Cart 🛒"):
            st.session_state.current_page = 'shopping_list'
            st.rerun()

# --- 5. KITCHEN MIND PRO ---
def page_kitchen_mind_pro(hh_id):
    st.button("← Back Home", on_click=lambda: st.session_state.update(current_page='home'))
    st.title("📸 KitchenMind Pro")
    st.info("AI Priority. Barcode Backup.")

    if 'scanned_data' not in st.session_state:
        st.session_state.scanned_data = None

    img_file = st.file_uploader("", type=['jpg','png','jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("Analyze Image"):
            with st.spinner("🤖 Analyzing..."):
                try:
                    prompt = """
                    Analyze image. Return JSON list. Fields: 
                    - item_name, quantity (float), weight (float), weight_unit,
                    - category, estimated_expiry (YYYY-MM-DD), threshold (float),
                    - suggested_store, storage_location, barcode, notes
                    """
                    response = client.models.generate_content(model="gemini-flash-latest", contents=[prompt, image])
                    clean_json = response.text.replace("```json","").replace("```","").strip()
                    ai_data = json.loads(clean_json)
                    
                    for item in ai_data:
                        bc = item.get('barcode', '')
                        db_data = fetch_barcode_data(bc) if bc else None
                        if db_data:
                            if not item.get('item_name'): item['item_name'] = db_data['item_name']
                            if not item.get('notes'): item['notes'] = db_data['notes']
                            if (item.get('weight',0)==0) and db_data['weight']>0:
                                item['weight'] = db_data['weight']
                                item['weight_unit'] = db_data['weight_unit']

                    st.session_state.scanned_data = ai_data
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.scanned_data:
        st.divider()
        edited_df = st.data_editor(
            st.session_state.scanned_data,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item_name": "Item Name",
                "quantity": st.
