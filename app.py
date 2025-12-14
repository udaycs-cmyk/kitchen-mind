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
import io

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Kitchen Mind",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. JOYFUL HUMANISM DESIGN SYSTEM (CSS) ---
def local_css():
    st.markdown("""
    <style>
        /* IMPORT FREDOKA FONT */
        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@300;400;500;600;700&display=swap');

        /* --- VARIABLES --- */
        :root {
            --bg-oatmeal: #FDF5EB;
            --text-brown: #4A3B32;
            --accent-coral: #FF8C69;
            --card-white: #FFFFFF;
            /* Headspace-inspired Palette */
            --hs-orange: #FF9C59;
            --hs-blue: #596DFF;
            --hs-yellow: #FFD54F;
            --hs-green: #4CAF50;
            --hs-purple: #9C27B0;
            --hs-mint: #A0E8AF;
        }

        /* --- BASE STYLES --- */
        .stApp {
            background-color: var(--bg-oatmeal);
            color: var(--text-brown);
        }
        
        /* Typography */
        h1, h2, h3, h4, h5, h6, p, label, .stButton button, .stTextInput input {
            font-family: 'Fredoka', sans-serif !important;
            color: var(--text-brown) !important;
        }
        
        /* Mobile-First Headings */
        h3 { font-size: 1.3rem !important; font-weight: 600 !important; }
        p, .caption { font-size: 0.95rem !important; }

        /* --- PANTRY CARD GRID --- */
        /* We create a class for the colorful cards */
        .pantry-card {
            border-radius: 24px;
            padding: 20px;
            color: #3E322C;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            transition: transform 0.2s;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .pantry-card:hover { transform: translateY(-3px); }
        
        /* Color Classes for Cards */
        .card-bg-0 { background-color: #FFF3E0; border: 2px solid #FFE0B2; } /* Peach */
        .card-bg-1 { background-color: #E3F2FD; border: 2px solid #BBDEFB; } /* Blue */
        .card-bg-2 { background-color: #F1F8E9; border: 2px solid #DCEDC8; } /* Green */
        .card-bg-3 { background-color: #F3E5F5; border: 2px solid #E1BEE7; } /* Purple */
        .card-bg-4 { background-color: #FFFDE7; border: 2px solid #FFF9C4; } /* Yellow */

        /* --- SOFT INPUTS --- */
        div[data-baseweb="input"] {
            background-color: var(--card-white) !important;
            border: 2px solid #F0E6D8 !important;
            border-radius: 20px !important;
            padding: 5px;
        }
        
        /* --- BUBBLE BUTTONS --- */
        div.stButton > button {
            background-color: var(--accent-coral) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 10px 25px !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 15px rgba(255, 140, 105, 0.3);
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: rgba(255,255,255,0.6);
            border-radius: 22px;
            border: none;
            color: var(--text-brown);
            font-weight: 600;
            padding: 0 20px;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: var(--accent-coral);
            color: white !important;
        }

        /* Hide Cruft */
        [data-testid="stSidebar"] { display: none; }
        header, footer { visibility: hidden; }
        
        /* Remove default container padding to look more like an app */
        .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- API & DATABASE ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "PASTE_YOUR_LOCAL_KEY_HERE"

try: client = genai.Client(api_key=GEMINI_API_KEY)
except: pass

if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets: cred = credentials.Certificate(dict(st.secrets["firebase"]))
        else: cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()

# --- ASSETS ---
def get_bean_logo():
    return """<svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M50 10C27.9 10 10 27.9 10 50S27.9 90 50 90 90 72.1 90 50 72.1 10 50 10z" fill="#FF8C69"/><path d="M35 40c0 2.8-2.2 5-5 5s-5-2.2-5-5 2.2-5 5-5 5 2.2 5 5zM75 40c0 2.8-2.2 5-5 5s-5-2.2-5-5 2.2-5 5-5 5 2.2 5 5z" fill="#3E322C"/><path d="M35 65s5 5 15 5 15-5 15-5" stroke="#3E322C" stroke-width="5" stroke-linecap="round"/><path d="M50 5s5 10 0 15" stroke="#4CAF50" stroke-width="6" stroke-linecap="round"/></svg>"""

def get_down_arrow():
    return """<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FF8C69" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>"""

# --- MAIN ---
def main():
    local_css()
    if 'user_info' not in st.session_state: st.session_state.user_info = None
    if 'imgs' not in st.session_state: st.session_state.imgs = {'f':None,'b':None,'d':None}
    if 'data' not in st.session_state: st.session_state.data = None
    
    if not st.session_state.user_info:
        login_screen()
    else:
        app_interface()

def login_screen():
    # Login Logic (Same as before)
    st.markdown(f"""<div style="height:80vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">{get_bean_logo()}<h1 style="margin:10px 0;">Kitchen Mind</h1><p style="color:#8D7B72;font-size:1.2rem;">Mindful inventory.</p></div>""", unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,2,1])
    with c2:
        with st.form("log"):
            email=st.text_input("Email")
            pw=st.text_input("Password",type="password")
            if st.form_submit_button("Start Cooking"):
                try:
                    users=db.collection('users').where('email','==',email.strip().lower()).where('password','==',pw).stream()
                    u=next(users,None)
                    if u: st.session_state.user_info=u.to_dict(); st.rerun()
                    else: st.error("No account found.")
                except: st.error("Login error.")

def app_interface():
    # Top Tabs acting as bottom nav style
    t1, t2, t3, t4 = st.tabs(["🏠 Home", "📸 Scan", "📦 Pantry", "🛒 List"])
    hh_id = st.session_state.user_info.get('household_id','DEMO')
    
    with t1: page_home(hh_id)
    with t2: page_scanner(hh_id)
    with t3: page_pantry(hh_id)
    with t4: page_list(hh_id)

def page_home(hh_id):
    st.markdown("## Good Morning!")
    st.write("What would you like to do?")
    c1,c2 = st.columns(2)
    with c1: 
        if st.button("📸 Scan Item", use_container_width=True): st.info("Use Scan tab!")
    with c2:
        if st.button("📝 Add Manually", use_container_width=True): manual_add_dialog(hh_id)

@st.dialog("Add Item")
def manual_add_dialog(hh_id):
    with st.form("add"):
        name=st.text_input("Item Name")
        cat=st.selectbox("Category",["Produce","Dairy","Meat","Pantry","Frozen","Snacks"])
        c1,c2=st.columns(2)
        qty=c1.number_input("Current",1.0,step=0.5)
        iq=c2.number_input("Full Size",1.0,step=0.5)
        store=st.selectbox("Store",["General","Costco","Whole Foods"])
        if st.form_submit_button("Save"):
            db.collection('inventory').add({
                "item_name":name,"category":cat,"quantity":qty,"initial_quantity":iq,
                "household_id":hh_id,"added_at":firestore.SERVER_TIMESTAMP,"threshold":1.0,"suggested_store":store
            })
            st.rerun()

def page_scanner(hh_id):
    st.markdown("## 📸 Scan")
    c1,c2=st.columns(2)
    with c1:
        if st.button("Front Photo"): st.session_state.active='f'; st.rerun()
    if st.session_state.get('active')=='f':
        p=st.camera_input("Snap")
        if p: st.session_state.imgs['f']=Image.open(p); st.session_state.active=None; st.rerun()
    
    if st.session_state.imgs['f']:
        st.image(st.session_state.imgs['f'], width=150)
        if st.button("Analyze"):
            # Mock Analysis for speed in this demo version
            st.session_state.data = [{"item_name":"Scanned Item","quantity":1,"category":"Pantry"}]
            st.rerun()

    if st.session_state.data:
        df = st.data_editor(st.session_state.data, num_rows="dynamic")
        if st.button("Save"):
            batch=db.batch()
            for i in df:
                ref=db.collection('inventory').document()
                batch.set(ref,{**i,"household_id":hh_id,"initial_quantity":i.get('quantity',1)})
            batch.commit(); st.session_state.data=None; st.rerun()

# --- 3. PANTRY (REDESIGNED: HEADSPACE CARDS) ---
def page_pantry(hh_id):
    st.markdown("## 📦 My Pantry")
    
    try:
        items = list(db.collection('inventory').where('household_id','==',hh_id).stream())
        data = [{'id': i.id, **i.to_dict()} for i in items]
    except: data = []
    
    if not data: st.info("Pantry is empty."); return

    # CSS Grid Logic using Streamlit Columns
    # We want 2 columns on mobile/desktop to mimic the Headspace grid
    cols = st.columns(2) 
    
    for idx, item in enumerate(data):
        # Cycle through 5 pastel colors based on index
        color_class = f"card-bg-{idx % 5}"
        
        with cols[idx % 2]:
            # The Card Container
            with st.container():
                # HTML Card Visual
                st.markdown(f"""
                <div class="pantry-card {color_class}">
                    <div style="font-size: 2rem; margin-bottom:10px;">🥗</div>
                    <div style="font-size: 1.1rem; font-weight: 700; line-height: 1.2;">
                        {item.get('item_name', 'Unknown')}
                    </div>
                    <div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 10px;">
                        {item.get('category', 'General')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Progress & Edit (Outside the HTML div so Streamlit widgets work)
                curr = float(item.get('quantity', 0))
                init = float(item.get('initial_quantity', curr)) or 1.0
                st.progress(min(curr/init, 1.0))
                
                # Expandable Edit Menu (Keeps card clean)
                with st.expander(f"Edit ({curr})"):
                    nc = st.number_input("Count", 0.0, value=curr, key=f"q_{item['id']}")
                    ni = st.number_input("Full Size", 0.0, value=init, key=f"i_{item['id']}")
                    
                    if nc != curr or ni != init:
                        db.collection('inventory').document(item['id']).update({'quantity':nc, 'initial_quantity':ni})
                        st.rerun()
                    
                    if st.button("Delete", key=f"d_{item['id']}"):
                        db.collection('inventory').document(item['id']).delete()
                        st.rerun()

def page_list(hh_id):
    st.markdown("## 🛒 List")
    with st.form("ql"):
        c1,c2=st.columns([3,1])
        txt=c1.text_input("Item")
        if c2.form_submit_button("Add") and txt:
            db.collection('shopping_list').add({"item_name":txt,"household_id":hh_id,"status":"Pending"})
            st.rerun()
            
    items = list(db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream())
    for i in [{'id':x.id,**x.to_dict()} for x in items]:
        c1,c2=st.columns([1,5])
        if c1.button("✓", key=i['id']):
            db.collection('shopping_list').document(i['id']).update({'status':'Bought'}); st.rerun()
        c2.write(i['item_name'])

if __name__ == "__main__":
    main()
