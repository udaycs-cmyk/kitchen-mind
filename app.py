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
            --accent-mint: #A0E8AF;
            --card-white: #FFFFFF;
        }

        /* --- BASE STYLES --- */
        .stApp {
            background-color: var(--bg-oatmeal);
            color: var(--text-brown);
        }
        
        /* Typography Override */
        h1, h2, h3, h4, h5, h6, p, label, .stButton button, .stTextInput input {
            font-family: 'Fredoka', sans-serif !important;
            color: var(--text-brown) !important;
        }
        
        /* --- HERO SECTION --- */
        .landing-hero {
            height: 95vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: radial-gradient(circle at 50% 50%, #FFF 0%, #FDF5EB 70%);
        }
        .bounce-arrow {
            animation: bounce 2s infinite;
            margin-top: 40px;
        }
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-15px);}
            60% {transform: translateY(-7px);}
        }

        /* --- PANTRY CARD GRID --- */
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
            position: relative;
        }
        .pantry-card:hover { transform: translateY(-3px); }
        
        /* Status Badge Style inside Card */
        .status-badge {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: rgba(255,255,255,0.6);
            display: inline-block;
            margin-bottom: 8px;
        }

        /* Card Colors */
        .card-bg-0 { background-color: #FFF3E0; border: 2px solid #FFE0B2; } 
        .card-bg-1 { background-color: #E3F2FD; border: 2px solid #BBDEFB; } 
        .card-bg-2 { background-color: #F1F8E9; border: 2px solid #DCEDC8; } 
        .card-bg-3 { background-color: #F3E5F5; border: 2px solid #E1BEE7; } 
        .card-bg-4 { background-color: #FFFDE7; border: 2px solid #FFF9C4; } 

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

        [data-testid="stSidebar"] { display: none; }
        header, footer { visibility: hidden; }
        .block-container { padding-top: 1rem; padding-bottom: 5rem; }
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
    return """<svg width="80" height="80" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M50 10C27.9 10 10 27.9 10 50S27.9 90 50 90 90 72.1 90 50 72.1 10 50 10z" fill="#FF8C69"/><path d="M35 40c0 2.8-2.2 5-5 5s-5-2.2-5-5 2.2-5 5-5 5 2.2 5 5zM75 40c0 2.8-2.2 5-5 5s-5-2.2-5-5 2.2-5 5-5 5 2.2 5 5z" fill="#3E322C"/><path d="M35 65s5 5 15 5 15-5 15-5" stroke="#3E322C" stroke-width="5" stroke-linecap="round"/><path d="M50 5s5 10 0 15" stroke="#4CAF50" stroke-width="6" stroke-linecap="round"/></svg>"""

def get_down_arrow():
    return """<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FF8C69" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>"""

# --- SMART ICONS ---
def get_smart_icon(item_name, category):
    name = item_name.lower()
    icons = {
        "milk": "🥛", "egg": "🥚", "bread": "🍞", "banana": "🍌", "apple": "🍎", 
        "chicken": "🍗", "beef": "🥩", "rice": "🍚", "pasta": "🍝", "cheese": "🧀",
        "yogurt": "🥣", "water": "💧", "coffee": "☕", "tea": "🍵", "juice": "🧃",
        "cookie": "🍪", "chocolate": "🍫", "carrot": "🥕", "broccoli": "🥦",
        "onion": "🧅", "garlic": "🧄", "tomato": "🍅", "potato": "🥔", "corn": "🌽",
        "avocado": "🥑", "salad": "🥗", "pizza": "🍕", "burger": "🍔", "fish": "🐟"
    }
    for key, icon in icons.items():
        if key in name: return icon
    cat_icons = {
        "Produce": "🥬", "Dairy": "🧀", "Meat": "🥩", "Pantry": "🥫", 
        "Frozen": "❄️", "Snacks": "🍿", "Beverages": "🥤", "Household": "🧻"
    }
    return cat_icons.get(category, "🥗")

# --- MAIN ---
def main():
    local_css()
    if 'user_info' not in st.session_state: st.session_state.user_info = None
    if 'imgs' not in st.session_state: st.session_state.imgs = {'f':None,'b':None,'d':None}
    if 'active' not in st.session_state: st.session_state.active = None
    if 'data' not in st.session_state: st.session_state.data = None
    
    if not st.session_state.user_info:
        login_screen()
    else:
        app_interface()

def login_screen():
    st.markdown(f"""
<div class="landing-hero">
{get_bean_logo()}
<h1 style="font-size: 3.5rem; margin: 10px 0;">Kitchen Mind</h1>
<p style="color:#8D7B72; font-size:1.5rem;">Mindful inventory for a happy home.</p>
<div class="bounce-arrow">{get_down_arrow()}</div>
<p style="font-size: 0.8rem; opacity: 0.5;">SCROLL TO START</p>
</div>
""", unsafe_allow_html=True)
    
    st.divider()
    c1,c2,c3=st.columns([1,2,1])
    with c2:
        st.markdown("<h3 style='text-align:center;'>Welcome In</h3>", unsafe_allow_html=True)
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
    t1, t2, t3, t4 = st.tabs(["🏠 Home", "📸 Scan", "📦 Pantry", "🛒 List"])
    hh_id = st.session_state.user_info.get('household_id','DEMO')
    
    with t1: page_home(hh_id)
    with t2: page_scanner(hh_id)
    with t3: page_pantry(hh_id)
    with t4: page_list(hh_id)

def page_home(hh_id):
    st.markdown("## Good Morning!")
    st.write("What would you like to do today?")
    c1,c2 = st.columns(2)
    with c1: 
        if st.button("📸 Scan New Items", use_container_width=True): st.info("Tap the 'Scan' tab above!")
    with c2:
        if st.button("📝 Add Manually", use_container_width=True): manual_add_dialog(hh_id)

@st.dialog("Add Item")
def manual_add_dialog(hh_id):
    # RESTORED: Full Fields from Original Pro Code
    with st.form("add"):
        c1, c2 = st.columns([2,1])
        name = c1.text_input("Item Name")
        category = c2.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"])
        
        st.markdown("##### Details")
        c3, c4, c5 = st.columns(3)
        qty = c3.number_input("Current Count", 1.0, step=0.5)
        init_qty = c4.number_input("Initial Qty", 1.0, step=0.5, value=qty)
        weight = c5.number_input("Weight", 0.0, step=0.5)
        
        c6, c7, c8 = st.columns(3)
        w_unit = c6.selectbox("Unit", ["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"])
        threshold = c7.number_input("Alert Limit", 1.0)
        expiry = c8.date_input("Expiry", datetime.date.today() + datetime.timedelta(days=7))
        
        store = st.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"])
        notes = st.text_area("Notes")
        barcode = st.text_input("Barcode (Optional)")
        
        if st.form_submit_button("Save"):
            db.collection('inventory').add({
                "item_name":name, "category":category, "quantity":qty, "initial_quantity":init_qty,
                "weight":weight, "weight_unit":w_unit, "threshold":threshold,
                "estimated_expiry":str(expiry), "suggested_store":store, "notes":notes, "barcode":barcode,
                "household_id":hh_id, "added_at":firestore.SERVER_TIMESTAMP
            })
            st.rerun()

def page_scanner(hh_id):
    st.markdown("## 📸 Kitchen Mind")
    st.info("Capture 3 angles for best results.")
    
    c1, c2, c3 = st.columns(3)
    def render_cam(col, key, label):
        with col:
            st.markdown(f"<div class='pantry-card card-bg-1' style='height: auto; min-height: 150px;'><strong>{label}</strong></div>", unsafe_allow_html=True)
            if st.session_state.imgs[key]:
                st.image(st.session_state.imgs[key], use_container_width=True)
                if st.button("Clear", key=f"del_{key}"): 
                    st.session_state.imgs[key]=None; st.rerun()
            elif st.session_state.active == key:
                p = st.camera_input("Snap", key=f"cam_{key}", label_visibility="collapsed")
                if p: st.session_state.imgs[key] = Image.open(p); st.session_state.active = None; st.rerun()
            else:
                if st.button("Tap to Snap", key=f"btn_{key}", use_container_width=True): st.session_state.active = key; st.rerun()

    render_cam(c1, 'f', "1. Front")
    render_cam(c2, 'b', "2. Back")
    render_cam(c3, 'd', "3. Expiry")

    valid = [i for i in st.session_state.imgs.values() if i]
    if valid:
        st.divider()
        if st.button("✨ Analyze Photos", type="primary", use_container_width=True):
            with st.spinner("Reading..."):
                st.session_state.data = [{"item_name":"Scanned Product", "quantity":1.0, "category":"Pantry"}]
                st.rerun()

    if st.session_state.data:
        df = st.data_editor(st.session_state.data, num_rows="dynamic")
        if st.button("Save to Pantry"):
            batch=db.batch()
            for i in df:
                ref=db.collection('inventory').document()
                batch.set(ref,{**i,"household_id":hh_id,"initial_quantity":i.get('quantity',1)})
            batch.commit(); st.session_state.data=None; st.rerun()

# --- 3. PANTRY (Cards + Restored Fields) ---
def page_pantry(hh_id):
    st.markdown("## 📦 My Pantry")
    
    try:
        items = list(db.collection('inventory').where('household_id','==',hh_id).stream())
        data = [{'id': i.id, **i.to_dict()} for i in items]
        
        shop_docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
        shopping_list_names = {d.to_dict()['item_name'].lower() for d in shop_docs}
    except:
        data = []
        shopping_list_names = set()
    
    if not data: st.info("Pantry is empty."); return

    cols = st.columns(2) 
    today = datetime.date.today()
    
    for idx, item in enumerate(data):
        color_class = f"card-bg-{idx % 5}"
        
        # RESTORED: Expiry Logic & Badges
        try: exp = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
        except: exp = today + datetime.timedelta(days=365)
        
        days_left = (exp - today).days
        if days_left < 0: badge = "🔴 Expired"
        elif days_left < 7: badge = f"🟠 {days_left}d left"
        else: badge = f"🟢 {days_left}d left"

        # LOGIC: Auto-Add to Shopping List based on Threshold (Alert Limit)
        curr = float(item.get('quantity', 0))
        thresh = float(item.get('threshold', 1))
        
        if curr < thresh and item['item_name'].lower() not in shopping_list_names:
             # SMART CALCULATION: How many do we need to reach the threshold?
             calc_needed = max(1.0, thresh - curr)
             
             db.collection('shopping_list').add({
                "item_name": item['item_name'], "household_id": hh_id,
                "store": item.get('suggested_store', 'General'), 
                "qty_needed": calc_needed, # <--- CALCULATED
                "status": "Pending", "reason": "Auto-Refill"
            })
             st.toast(f"🚨 Added {item['item_name']} (Buy {calc_needed})")
             shopping_list_names.add(item['item_name'].lower())

        icon = get_smart_icon(item.get('item_name', ''), item.get('category', 'General'))
        
        with cols[idx % 2]:
            with st.container():
                # HTML Card with Badge
                st.markdown(f"""
                <div class="pantry-card {color_class}">
                    <div class="status-badge">{badge}</div>
                    <div style="font-size: 3rem; margin-bottom:10px;">{icon}</div>
                    <div style="font-size: 1.1rem; font-weight: 700; line-height: 1.2;">
                        {item.get('item_name', 'Unknown')}
                    </div>
                    <div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 10px;">
                        {item.get('category', 'General')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                init = float(item.get('initial_quantity', curr)) or 1.0
                st.progress(min(curr/init, 1.0))
                
                # RESTORED: Full Edit Fields in Expander
                with st.expander(f"Edit ({curr})"):
                    nc = st.number_input("Count", 0.0, value=curr, key=f"q_{item['id']}")
                    ni = st.number_input("Initial Qty", 0.0, value=init, key=f"i_{item['id']}")
                    nw = st.number_input("Weight", 0.0, value=float(item.get('weight', 0)), key=f"w_{item['id']}")
                    nt = st.number_input("Alert Limit", 0.0, value=float(item.get('threshold', 1)), key=f"t_{item['id']}")
                    
                    updates = {}
                    if nc != curr: updates['quantity'] = nc
                    if ni != init: updates['initial_quantity'] = ni
                    if nw != float(item.get('weight', 0)): updates['weight'] = nw
                    if nt != float(item.get('threshold', 1)): updates['threshold'] = nt
                    
                    if updates:
                        db.collection('inventory').document(item['id']).update(updates)
                        st.rerun()
                    
                    if st.button("Delete", key=f"d_{item['id']}"):
                        db.collection('inventory').document(item['id']).delete()
                        st.rerun()

def page_list(hh_id):
    st.markdown("## 🛒 Shopping List")
    
    # 1. Manual Add with Quantity
    with st.container(border=True):
        with st.form("ql"):
            c1, c2, c3 = st.columns([3, 1, 1])
            txt = c1.text_input("Item Name")
            qty = c2.number_input("Qty", 1.0, step=1.0)
            if c3.form_submit_button("Add", use_container_width=True) and txt:
                db.collection('shopping_list').add({
                    "item_name": txt, 
                    "household_id": hh_id, 
                    "qty_needed": qty, # <--- SAVES YOUR INPUT
                    "status": "Pending",
                    "store": "General"
                })
                st.rerun()
            
    items = list(db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream())
    
    if not items: 
        st.info("Your list is empty! Great job.")
        return
    
    # Sort data for display
    data = [{'id': x.id, **x.to_dict()} for x in items]
    
    # Group by Store (Pro Logic)
    stores = list(set([d.get('store', 'General') for d in data]))
    
    for s in stores:
        st.markdown(f"### 📍 {s}")
        store_items = [d for d in data if d.get('store') == s]
        
        for i in store_items:
            # Joyful List Card
            with st.container(border=True):
                c1, c2 = st.columns([1, 5])
                if c1.button("✓", key=i['id'], use_container_width=True):
                    db.collection('shopping_list').document(i['id']).update({'status': 'Bought'})
                    st.rerun()
                
                # Smart Icon
                icon = get_smart_icon(i['item_name'], "General")
                
                # Show Name and Quantity Needed
                qty_show = float(i.get('qty_needed', 1))
                # Format: remove decimals if whole number (e.g. 2.0 -> 2)
                q_str = f"{int(qty_show)}" if qty_show.is_integer() else f"{qty_show}"
                
                c2.markdown(f"<div style='font-size:1.1rem;'>{icon} <strong>{i['item_name']}</strong></div>", unsafe_allow_html=True)
                c2.caption(f"Buy: {q_str}")

if __name__ == "__main__":
    main()
