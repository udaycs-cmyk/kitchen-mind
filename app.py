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
            --shadow-soft: 0 8px 24px rgba(74, 59, 50, 0.08);
        }

        /* --- BASE STYLES --- */
        .stApp {
            background-color: var(--bg-oatmeal);
            color: var(--text-brown);
        }
        
        /* Typography Overrides (Removed 'span' and 'div' to fix icons) */
        h1, h2, h3, h4, h5, h6, p, label, .stButton button, .stTextInput input {
            font-family: 'Fredoka', sans-serif !important;
            color: var(--text-brown) !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #FFF8F0;
            border-right: 2px solid #F0E6D8;
        }

        /* --- SOFT INPUT FIELDS --- */
        div[data-baseweb="input"] {
            background-color: var(--card-white) !important;
            border: 2px solid #F0E6D8 !important;
            border-radius: 20px !important;
            padding: 5px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.02) !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: var(--accent-coral) !important;
        }
        input {
            color: var(--text-brown) !important;
        }

        /* --- BUBBLE BUTTONS --- */
        div.stButton > button {
            background-color: var(--accent-coral) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 10px 25px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            box-shadow: 0 6px 15px rgba(255, 140, 105, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        div.stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(255, 140, 105, 0.4);
        }

        /* --- CARDS (Round & Friendly) --- */
        div[data-testid="stForm"], .element-container .stContainer {
            background-color: var(--card-white);
            border-radius: 32px;
            border: 1px solid #F5EFE6;
            padding: 25px;
            box-shadow: var(--shadow-soft);
        }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: #FFF;
            padding: 15px;
            border-radius: 20px;
            text-align: center;
            border: 2px solid #F8F0E6;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
            padding: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: rgba(255, 255, 255, 0.6);
            border-radius: 25px;
            border: none;
            color: var(--text-brown);
            font-weight: 600;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: var(--accent-coral);
            color: white !important;
        }

        /* --- HERO SECTION --- */
        .landing-hero {
            height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: radial-gradient(circle at 50% 50%, #FFF 0%, #FDF5EB 70%);
        }
        .hero-title {
            font-size: 4rem;
            font-weight: 700;
            color: var(--text-brown);
            margin-bottom: 10px;
        }
        .hero-subtitle {
            font-size: 1.5rem;
            color: #8D7B72 !important;
            margin-bottom: 40px;
        }
        .bounce-arrow {
            animation: bounce 2s infinite;
            background-color: white;
            border-radius: 50%;
            padding: 10px;
            box-shadow: var(--shadow-soft);
        }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-15px);}
            60% {transform: translateY(-7px);}
        }

        header {visibility: hidden;}
        footer {visibility: hidden;}
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

# --- CUSTOM SVGs (Bean Style Illustrations) ---
def get_bean_logo():
    return """
<svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 10C27.9086 10 10 27.9086 10 50C10 72.0914 27.9086 90 50 90C72.0914 90 90 72.0914 90 50C90 27.9086 72.0914 10 50 10Z" fill="#FF8C69"/>
    <path d="M35 40C35 42.7614 32.7614 45 30 45C27.2386 45 25 42.7614 25 40C25 37.2386 27.2386 35 30 35C32.7614 35 35 37.2386 35 40Z" fill="#3E322C"/>
    <path d="M75 40C75 42.7614 72.7614 45 70 45C67.2386 45 65 42.7614 65 40C65 37.2386 67.2386 35 70 35C72.7614 35 75 37.2386 75 40Z" fill="#3E322C"/>
    <path d="M35 65C35 65 40 70 50 70C60 70 65 65 65 65" stroke="#3E322C" stroke-width="5" stroke-linecap="round"/>
    <path d="M50 5C50 5 55 15 50 20" stroke="#4CAF50" stroke-width="6" stroke-linecap="round"/>
</svg>
    """

def get_down_arrow():
    return """
<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FF8C69" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 5v14M19 12l-7 7-7-7"/>
</svg>
    """

# --- HELPER: BARCODE (Restored Logic) ---
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

# --- MAIN LOGIC ---
def main():
    local_css()
    # Initialize Safe Session State for ALL variables
    if 'user_info' not in st.session_state: st.session_state.user_info = None
    if 'imgs' not in st.session_state: st.session_state.imgs = {'f':None, 'b':None, 'd':None}
    if 'active' not in st.session_state: st.session_state.active = None
    if 'data' not in st.session_state: st.session_state.data = None
    
    if not st.session_state.user_info:
        login_screen()
    else:
        app_interface()

def login_screen():
    # --- HERO SECTION ---
    st.markdown(f"""
<div class="landing-hero">
{get_bean_logo()}
<div class="hero-title">Kitchen Mind</div>
<div class="hero-subtitle">Mindful inventory for a happy home.</div>
<div class="scroll-indicator bounce-arrow">
{get_down_arrow()}
</div>
</div>
""", unsafe_allow_html=True)
    
    # --- LOGIN FORM ---
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h3 style='text-align: center;'>Welcome In</h3>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Sign In", "New Account"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                st.write("")
                if st.form_submit_button("Start Cooking", use_container_width=True):
                    try:
                        users = db.collection('users').where('email', '==', email.strip().lower()).where('password', '==', password).stream()
                        user = next(users, None)
                        if user:
                            st.session_state.user_info = user.to_dict()
                            st.rerun()
                        else: st.error("We couldn't find that account.")
                    except Exception as e:
                        st.error(f"Login Error: {e}")
        
        with tab2:
            with st.form("signup_form"):
                new_email = st.text_input("New Email")
                new_pass = st.text_input("Create Password", type="password")
                hh = st.text_input("Household Name")
                st.write("")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if new_email and new_pass:
                        try:
                            uid = str(uuid.uuid4())[:6].upper()
                            db.collection('users').add({
                                "email": new_email.lower(), "password": new_pass, "household_id": uid
                            })
                            db.collection('households').document(uid).set({"name": hh, "id": uid})
                            st.success(f"Welcome! Your ID is {uid}")
                        except Exception as e:
                            st.error(f"Signup Error: {e}")

def app_interface():
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"{get_bean_logo()}", unsafe_allow_html=True)
        st.markdown("### Kitchen Mind")
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.rerun()

    # --- TOP NAVIGATION ---
    t1, t2, t3, t4 = st.tabs(["🏠 Home", "📸 Scanner", "📦 Pantry", "🛒 List"])
    
    # Ensure household ID exists safely
    if st.session_state.user_info:
        hh_id = st.session_state.user_info.get('household_id', 'DEMO')
        with t1: page_home(hh_id)
        with t2: page_scanner(hh_id)
        with t3: page_pantry(hh_id)
        with t4: page_list(hh_id)

# --- 1. HOME ---
def page_home(hh_id):
    st.markdown("## Good Morning!")
    st.markdown("What would you like to do?")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### 📸 Scan")
            st.caption("Add items with AI")
            if st.button("Open Scanner", use_container_width=True): 
                st.info("Tap the 'Scanner' tab above!")
    with c2:
        with st.container(border=True):
            st.markdown("### 📝 Add")
            st.caption("Type manually")
            if st.button("Type Item", use_container_width=True):
                manual_add_dialog(hh_id)
    with c3:
        with st.container(border=True):
            st.markdown("### 📦 Check")
            st.caption("View Pantry")
            if st.button("View Stock", use_container_width=True):
                st.info("Tap the 'Pantry' tab above!")

@st.dialog("Add Item")
def manual_add_dialog(hh_id):
    # RESTORED FULL FORM LOGIC FROM OLD CODE
    with st.form("manual_add"):
        c1, c2 = st.columns([2,1])
        name = c1.text_input("Item Name")
        category = c2.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"])
        
        st.markdown("##### Details")
        c3, c4, c5 = st.columns(3)
        qty = c3.number_input("Count", 1.0, step=0.5)
        weight = c4.number_input("Weight", 0.0, step=0.5)
        w_unit = c5.selectbox("Unit", ["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"])
        
        c6, c7, c8 = st.columns(3)
        threshold = c6.number_input("Alert Limit", 1.0)
        expiry = c7.date_input("Expiry", datetime.date.today() + datetime.timedelta(days=7))
        store = c8.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"])
        
        if st.form_submit_button("Add to Pantry"):
            try:
                db.collection('inventory').add({
                    "item_name": name, "category": category,
                    "quantity": float(qty), "initial_quantity": float(qty),
                    "weight": float(weight), "weight_unit": w_unit,
                    "threshold": float(threshold), "estimated_expiry": str(expiry),
                    "suggested_store": store, "household_id": hh_id,
                    "added_at": firestore.SERVER_TIMESTAMP,
                    "last_restocked": firestore.SERVER_TIMESTAMP
                })
                st.rerun()
            except Exception as e:
                st.error("Could not add item.")

# --- 2. SCANNER ---
def page_scanner(hh_id):
    st.markdown("## 📸 Kitchen Mind")
    st.info("Snap photos of your groceries. We'll handle the rest.")
    
    def cam_block(label, key):
        with st.container(border=True):
            st.markdown(f"**{label}**")
            if st.session_state.imgs[key]:
                st.image(st.session_state.imgs[key], use_container_width=True)
                if st.button("Clear", key=f"clr_{key}"): 
                    st.session_state.imgs[key]=None; st.rerun()
            elif st.session_state.active == key:
                p = st.camera_input("Snap", key=f"cam_{key}")
                if p: 
                    st.session_state.imgs[key] = Image.open(p)
                    st.session_state.active = None
                    st.rerun()
            else:
                if st.button("Tap to Snap", key=f"btn_{key}", use_container_width=True):
                    st.session_state.active = key
                    st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1: cam_block("Front", 'f')
    with c2: cam_block("Back", 'b')
    with c3: cam_block("Expiry", 'd')

    valid = [i for i in st.session_state.imgs.values() if i]
    if valid:
        st.divider()
        if st.button("✨ Analyze Photos", type="primary", use_container_width=True):
            with st.spinner("Reading labels..."):
                try:
                    prompt = """
                    Extract JSON: item_name, quantity(float), weight(float), weight_unit, 
                    category, estimated_expiry(YYYY-MM-DD), barcode, suggested_store
                    """
                    res = client.models.generate_content(model="gemini-flash-latest", contents=[prompt]+valid)
                    clean = res.text.replace("```json","").replace("```","").strip()
                    ai_data = json.loads(clean)
                    
                    # RESTORED: Barcode Logic integration
                    for item in ai_data:
                        bc = item.get('barcode', '')
                        if bc:
                            db_data = fetch_barcode_data(bc)
                            if db_data:
                                if not item.get('item_name'): item['item_name'] = db_data['item_name']
                                if not item.get('notes'): item['notes'] = db_data['notes']

                    st.session_state.data = ai_data
                except: st.error("Could not read image. Try again.")

    if st.session_state.data:
        df = st.data_editor(st.session_state.data, num_rows="dynamic", use_container_width=True)
        if st.button("Save to Pantry", use_container_width=True):
            batch = db.batch()
            for i in df:
                ref = db.collection('inventory').document()
                batch.set(ref, {**i, "household_id": hh_id, "added_at": firestore.SERVER_TIMESTAMP, "initial_quantity": i.get('quantity',1)})
            batch.commit()
            st.success("Added!")
            st.session_state.data = None
            st.session_state.imgs = {'f':None, 'b':None, 'd':None}
            time.sleep(1)
            st.rerun()

# --- 3. PANTRY (Restored Logic + Joyful UI) ---
def page_pantry(hh_id):
    st.markdown("## 📦 My Pantry")
    
    try:
        items = list(db.collection('inventory').where('household_id','==',hh_id).stream())
        data = [{'id': i.id, **i.to_dict()} for i in items]
        
        # RESTORED: Auto-shopping list logic
        shop_docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
        shopping_list_names = {d.to_dict()['item_name'].lower() for d in shop_docs}
    except:
        data = []
        shopping_list_names = set()
    
    if not data:
        st.info("Your pantry is empty. Time to go shopping!")
        return

    today = datetime.date.today()

    for item in data:
        # RESTORED: Calculation Logic
        current_qty = float(item.get('quantity', 1))
        initial_qty = float(item.get('initial_quantity', current_qty))
        thresh = float(item.get('threshold', 1))
        
        try: exp = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
        except: exp = today + datetime.timedelta(days=365)
        
        days_left = (exp - today).days
        
        # Auto-Add Logic
        if current_qty < thresh and item['item_name'].lower() not in shopping_list_names:
             db.collection('shopping_list').add({
                "item_name": item['item_name'], "household_id": hh_id,
                "store": item.get('suggested_store', 'General'), "qty_needed": 1,
                "status": "Pending", "reason": "Auto-Refill"
            })
             st.toast(f"🚨 Added {item['item_name']} to list")
             shopping_list_names.add(item['item_name'].lower())

        # Badge Logic
        if days_left < 0: badge = "🔴 Expired"
        elif days_left < 7: badge = f"🟠 {days_left}d"
        else: badge = "🟢 Good"

        # JOYFUL CARD UI
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"### {item.get('item_name','Unknown')}")
                st.caption(f"{badge} • {item.get('category','General')} • {item.get('weight', '')} {item.get('weight_unit','')}")
                
                # Visual Bar
                prog = min(current_qty/initial_qty, 1.0) if initial_qty > 0 else 0
                st.progress(prog)
                
            with c2:
                st.write("")
                st.markdown(f"**{current_qty} left**")
            
            with st.expander("Update"):
                # RESTORED: Full Edit Fields
                ec1, ec2 = st.columns(2)
                nq = ec1.number_input("Count", 0.0, value=current_qty, key=f"q_{item['id']}")
                n_thr = ec2.number_input("Alert Limit", 0.0, value=thresh, key=f"t_{item['id']}")
                
                if nq != current_qty:
                    db.collection('inventory').document(item['id']).update({'quantity': nq})
                    st.rerun()
                if n_thr != thresh:
                    db.collection('inventory').document(item['id']).update({'threshold': n_thr})
                    st.rerun()
                    
                if st.button("Remove", key=f"del_{item['id']}"):
                    db.collection('inventory').document(item['id']).delete()
                    st.rerun()

# --- 4. LIST (Restored Logic) ---
def page_list(hh_id):
    st.markdown("## 🛒 Shopping List")
    with st.form("add_list"):
        c1, c2 = st.columns([3,1])
        txt = c1.text_input("Need anything?")
        if st.form_submit_button("Add") and txt:
            db.collection('shopping_list').add({"item_name": txt, "household_id": hh_id, "status": "Pending", "store": "General"})
            st.rerun()
            
    try:
        items = list(db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream())
        data = [{'id': i.id, **i.to_dict()} for i in items]
    except: data = []
    
    if not data: st.success("All caught up!"); return
    
    # RESTORED: Group by Store
    stores = list(set([d.get('store','General') for d in data]))
    
    for s in stores:
        st.markdown(f"#### 📍 {s}")
        store_items = [d for d in data if d.get('store')==s]
        
        for i in store_items:
            c1, c2 = st.columns([1, 6])
            if c1.button("✓", key=i['id']):
                db.collection('shopping_list').document(i['id']).update({'status': 'Bought'})
                st.rerun()
            c2.markdown(f"**{i['item_name']}**")
        st.divider()

if __name__ == "__main__":
    main()
