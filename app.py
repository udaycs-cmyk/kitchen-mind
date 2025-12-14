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
    page_title="Kitchen Mind Pro",
    page_icon="https://cdn-icons-png.flaticon.com/512/2921/2921822.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (PREMIUM DASHBOARD THEME) ---
def local_css():
    st.markdown("""
    <style>
        /* 1. BACKGROUND & SIDEBAR */
        .stApp {
            background-color: #0E0E0E;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
        }
        
        [data-testid="stSidebar"] {
            background-color: #050505;
            border-right: 1px solid #333;
        }

        /* 2. TYPOGRAPHY */
        h1, h2, h3 { 
            color: #D4AF37 !important; 
            font-weight: 700; 
            letter-spacing: -0.5px;
            text-transform: capitalize;
        }
        p, label, span, div { color: #E0E0E0 !important; font-size: 15px; }
        
        /* Metric Labels */
        [data-testid="stMetricLabel"] {
            color: #888888 !important;
            font-size: 14px !important;
        }
        [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* 3. INPUT FIELDS */
        div[data-baseweb="input"] {
            background-color: #1A1A1A !important;
            border: 1px solid #333333 !important;
            border-radius: 12px !important;
        }
        input, textarea {
            color: #FFFFFF !important;
            caret-color: #D4AF37 !important;
        }
        
        /* 4. BUTTONS */
        div.stButton > button {
            background-image: linear-gradient(135deg, #D4AF37 0%, #B4941F 100%);
            color: #000000 !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 700 !important;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
        }

        /* 5. ITEM CARDS */
        .item-card {
            background-color: #161616;
            border: 1px solid #2A2A2A;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
            transition: border 0.3s ease;
        }
        
        /* 6. PROGRESS BAR */
        .stProgress > div > div > div > div {
            background-color: #D4AF37;
        }

        /* 7. NEW BADGE */
        .new-badge {
            background-color: #D4AF37;
            color: #000;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.5em;
            font-weight: 800;
            vertical-align: super;
            margin-left: 5px;
        }
        
        /* 8. LANDING HERO SECTION */
        .landing-hero {
            height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            animation: fadeIn 1.5s ease-in-out;
        }
        
        .scroll-indicator {
            margin-top: 50px;
            /* Removed generic font size/color here, handled in the SVG/span directly */
            animation: bounce 2s infinite;
        }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-10px);}
            60% {transform: translateY(-5px);}
        }
        @keyframes fadeIn {
            0% {opacity: 0;}
            100% {opacity: 1;}
        }

        /* Hide default header/footer */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Custom Camera Placeholder Style */
        .camera-placeholder {
            border: 2px dashed #333;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            color: #666;
            background-color: #111;
        }
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

# --- HELPER: BARCODE ---
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

# --- MAIN NAV ---
def main():
    local_css()
    if 'user_info' not in st.session_state: st.session_state.user_info = None
    if 'current_page' not in st.session_state: st.session_state.current_page = 'home'

    if not st.session_state.user_info:
        login_signup_screen()
    else:
        sidebar_info()
        
        # PERSISTENT TOP TABS
        tab_dash, tab_scan, tab_stock, tab_cart = st.tabs([
            "🏠 Dashboard", 
            "📸 Scanner", 
            "📦 My Stock", 
            "🛒 Cart"
        ])

        with tab_dash:
             page_home_dashboard(st.session_state.user_info['household_id'])
        with tab_scan:
             page_kitchen_mind_pro(st.session_state.user_info['household_id'])
        with tab_stock:
             page_inventory(st.session_state.user_info['household_id'])
        with tab_cart:
             page_shopping_list(st.session_state.user_info['household_id'])

def sidebar_info():
    with st.sidebar:
        st.markdown("### Kitchen Mind Pro <span class='new-badge'>NEW ✨</span>", unsafe_allow_html=True)
        st.caption(f"ID: {st.session_state.user_info['household_id']}")
        st.divider()
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.rerun()

def login_signup_screen():
    # --- 1. FULL SCREEN LANDING HERO (UPDATED WITH GOLD SVG ARROW) ---
    # Replaced the blue emoji ⬇️ with a custom SVG colored #D4AF37
    st.markdown("""
        <div class="landing-hero">
            <h1 style="font-size: 4rem; margin-bottom: 0;">KITCHEN MIND PRO</h1>
            <p style="font-size: 1.2rem; opacity: 0.8; letter-spacing: 2px;">LUXURY HOME INVENTORY</p>
            <div class="scroll-indicator">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 4V20M12 20L18 14M12 20L6 14" stroke="#D4AF37" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <br>
                <span style="font-size: 12px; opacity: 0.6; color: #D4AF37;">SCROLL TO LOGIN</span>
            </div>
        </div>
        <hr style="border: 0; border-top: 1px solid #333; margin-bottom: 50px;">
    """, unsafe_allow_html=True)

    # --- 2. LOGIN FORM (Appears below) ---
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div style="text-align: center;"><h3 style="color: #D4AF37;">WELCOME BACK</h3></div>', unsafe_allow_html=True)
        st.write("")
        
        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email").lower().strip()
                password = st.text_input("Password", type="password")
                st.write("")
                if st.form_submit_button("LOGIN", use_container_width=True):
                    users = db.collection('users').where('email', '==', email).where('password', '==', password).stream()
                    user = next(users, None)
                    if user:
                        st.session_state.user_info = user.to_dict()
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            with st.form("signup_form"):
                new_email = st.text_input("New Email").lower().strip()
                new_pass = st.text_input("Password", type="password")
                mode = st.radio("Setup", ["Create New Household", "Join Existing"])
                hh_input = st.text_input("Household Name or ID")
                st.write("")
                if st.form_submit_button("CREATE ACCOUNT", use_container_width=True):
                    if not new_email or not new_pass: return
                    hh_id = str(uuid.uuid4())[:6].upper()
                    if mode == "Create New Household":
                        db.collection('households').document(hh_id).set({"name": hh_input, "id": hh_id})
                        db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_id})
                        st.success(f"Success! ID: {hh_id}")
                    else:
                        if db.collection('households').document(hh_input).get().exists:
                            db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_input})
                            st.success("Joined! Please Login.")
                        else: st.error("Invalid ID")

# --- PAGE FUNCTIONS ---

def page_home_dashboard(hh_id):
    st.markdown("## 👋 Welcome")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.markdown("#### 📸 Scan 360°")
            st.caption("AI Entry")
            if st.button("Launch", use_container_width=True): 
                st.info("Click '📸 Scanner' tab above!")
    with c2:
        with st.container(border=True):
            st.markdown("#### 📝 Add")
            st.caption("Manual")
            if st.button("Type", use_container_width=True): 
                manual_add_dialog(hh_id)
    with c3:
        with st.container(border=True):
            st.markdown("#### 📦 Stock")
            st.caption("View All")
            if st.button("View", use_container_width=True): st.info("Click '📦 My Stock' tab above!")
    with c4:
        with st.container(border=True):
            st.markdown("#### 🛒 Cart")
            st.caption("To Buy")
            if st.button("Shop", use_container_width=True): st.info("Click '🛒 Cart' tab above!")

@st.dialog("📝 Manual Add Item")
def manual_add_dialog(hh_id):
    with st.form("manual_add_form"):
        c1, c2 = st.columns([2,1])
        name = c1.text_input("Item Name")
        category = c2.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"])
        c3, c4, c5 = st.columns(3)
        qty = c3.number_input("Count", 1.0, step=0.5)
        weight = c4.number_input("Weight", 0.0, step=0.5)
        w_unit = c5.selectbox("Unit", ["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"])
        c6, c7, c8 = st.columns(3)
        threshold = c6.number_input("Alert Limit", 1.0)
        expiry = c7.date_input("Expiry", datetime.date.today() + datetime.timedelta(days=7))
        store = c8.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"])
        
        if st.form_submit_button("Save Item"):
            if name:
                db.collection('inventory').add({
                    "item_name": name, "category": category,
                    "quantity": float(qty), "initial_quantity": float(qty),
                    "weight": float(weight), "weight_unit": w_unit,
                    "threshold": float(threshold), "estimated_expiry": str(expiry),
                    "suggested_store": store, "household_id": hh_id,
                    "added_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                    "last_restocked": firestore.SERVER_TIMESTAMP,
                    "storage_location": "Pantry"
                })
                st.success(f"Saved {name}!")
                time.sleep(0.5)
                st.rerun()

# --- 5. KITCHEN MIND PRO (CLICK-TO-ACTIVATE CAMERA) ---
def page_kitchen_mind_pro(hh_id):
    st.markdown("## 📸 Kitchen Mind Pro <span class='new-badge'>NEW ✨</span>", unsafe_allow_html=True)
    st.info("Tap a block to capture that angle. AI combines them for better accuracy.")
    
    # Initialize Session State for Images and Active Camera
    if 'scanner_images' not in st.session_state:
        st.session_state.scanner_images = {'front': None, 'back': None, 'detail': None}
    if 'active_cam' not in st.session_state:
        st.session_state.active_cam = None
    if 'scanned_data' not in st.session_state:
        st.session_state.scanned_data = None

    # Helper function to render a single camera block
    def render_camera_block(label, key):
        with st.container(border=True):
            st.markdown(f"**{label}**")
            
            # STATE 1: Image already captured -> Show Preview
            if st.session_state.scanner_images[key]:
                st.image(st.session_state.scanner_images[key], use_container_width=True)
                if st.button("❌ Retake", key=f"retake_{key}", use_container_width=True):
                    st.session_state.scanner_images[key] = None
                    st.session_state.active_cam = None # Reset
                    st.rerun()
            
            # STATE 2: This block is active -> Show Camera
            elif st.session_state.active_cam == key:
                pic = st.camera_input(f"Snap {label}", key=f"cam_{key}", label_visibility="collapsed")
                if pic:
                    st.session_state.scanner_images[key] = Image.open(pic)
                    st.session_state.active_cam = None # Turn off camera
                    st.rerun()
                if st.button("Cancel", key=f"cancel_{key}", use_container_width=True):
                    st.session_state.active_cam = None
                    st.rerun()
            
            # STATE 3: Idle -> Show "Capture" button
            else:
                # Show placeholder styling
                st.markdown(
                    f"""<div class="camera-placeholder">📸<br>Tap to Scan</div>""", 
                    unsafe_allow_html=True
                )
                # Disable this button if ANOTHER camera is active (prevent multiple cams)
                disabled = st.session_state.active_cam is not None
                if st.button(f"Capture {label}", key=f"btn_{key}", disabled=disabled, use_container_width=True):
                    st.session_state.active_cam = key
                    st.rerun()

    # Layout the 3 Blocks
    c1, c2, c3 = st.columns(3)
    with c1: render_camera_block("1. Front View", "front")
    with c2: render_camera_block("2. Back (Ingredients)", "back")
    with c3: render_camera_block("3. Detail (Expiry)", "detail")

    st.divider()

    # Analyze Button (Only if at least one image exists)
    has_images = any(st.session_state.scanner_images.values())
    
    if has_images:
        if st.button("✨ Analyze Product 360°", type="primary", use_container_width=True):
            with st.spinner("🤖 AI is combining angles to extract details..."):
                try:
                    # Prepare prompt and valid images
                    prompt = """
                    Analyze these product images. Return a JSON list of items found.
                    Combine info from all angles (Front for Name, Back for Ingredients, Detail for Expiry).
                    Fields: item_name, quantity (float), weight (float), weight_unit,
                    category, estimated_expiry (YYYY-MM-DD), threshold (float), suggested_store, barcode, notes.
                    """
                    
                    valid_images = [img for img in st.session_state.scanner_images.values() if img is not None]
                    content_payload = [prompt] + valid_images
                    
                    response = client.models.generate_content(model="gemini-flash-latest", contents=content_payload)
                    clean_json = response.text.replace("```json","").replace("```","").strip()
                    ai_data = json.loads(clean_json)
                    
                    # Enrich with barcode API if found
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
                except Exception as e: st.error(f"Error: {e}")

    # Results Editor
    if st.session_state.scanned_data:
        st.markdown("#### Review AI Results")
        edited_df = st.data_editor(st.session_state.scanned_data, num_rows="dynamic", use_container_width=True)
        
        c_save, c_clear = st.columns([3, 1])
        with c_save:
            if st.button("✅ Confirm & Save to Stock", type="primary", use_container_width=True):
                batch = db.batch()
                for item in edited_df:
                    ref = db.collection('inventory').document()
                    qty = float(item.get('quantity', 1))
                    item.update({
                        'quantity': qty, 'initial_quantity': qty,
                        'weight': float(item.get('weight', 0)),
                        'weight_unit': item.get('weight_unit', 'count'),
                        'household_id': hh_id,
                        'added_at': firestore.SERVER_TIMESTAMP,
                        'last_updated': firestore.SERVER_TIMESTAMP,
                        'last_restocked': firestore.SERVER_TIMESTAMP
                    })
                    batch.set(ref, item)
                batch.commit()
                st.toast("Saved successfully!")
                # Reset
                st.session_state.scanned_data = None
                st.session_state.scanner_images = {'front': None, 'back': None, 'detail': None}
                time.sleep(1)
                st.rerun()
        with c_clear:
            if st.button("Clear All"):
                st.session_state.scanned_data = None
                st.session_state.scanner_images = {'front': None, 'back': None, 'detail': None}
                st.rerun()

def page_inventory(hh_id):
    st.markdown("## 📦 My Stock")
    
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    shop_docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    shopping_list_names = {d.to_dict()['item_name'].lower() for d in shop_docs}

    if not items:
        st.info("Your stock is empty. Use the AI Scanner or add manually.")
        return
        
    items.sort(key=lambda x: x.get('item_name', ''))
    today = datetime.date.today()
    
    for item in items:
        current_qty = float(item.get('quantity', 1))
        initial_qty = float(item.get('initial_quantity', current_qty))
        thresh = float(item.get('threshold', 1))
        daily_use = float(item.get('daily_usage', 0))
        
        try: exp_date = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
        except: exp_date = today + datetime.timedelta(days=365)
        
        days_left_spoil = (exp_date - today).days
        days_left_empty = int(current_qty/daily_use) if daily_use > 0 else 999
        days_left_real = min(days_left_spoil, days_left_empty)
        
        safe_initial = initial_qty if initial_qty > 0 else 1.0
        progress_val = min(max(current_qty / safe_initial, 0.0), 1.0)
        
        if days_left_real < 0: status_color = "🔴 Expired"
        elif days_left_real < 7: status_color = "🟠 Low"
        else: status_color = "🟢 Good"

        with st.container(border=True): 
            c_top1, c_top2 = st.columns([3, 1])
            with c_top1:
                st.markdown(f"### {item['item_name']}")
                st.caption(f"{item.get('category', 'General').upper()} • {item.get('store', 'General')}")
            with c_top2:
                st.markdown(f"**{status_color}**")
            
            st.divider()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Quantity", f"{current_qty}", delta_color="off")
            m2.metric("Days Left", f"{days_left_real} d")
            if daily_use > 0:
                empty_date = today + datetime.timedelta(days=days_left_empty)
                m3.metric("Empty By", empty_date.strftime("%b %d"))
            else:
                m3.metric("Usage", "Unknown")

            st.caption("Stock Level")
            st.progress(progress_val)
            
            with st.expander("Update / Edit"):
                ec1, ec2 = st.columns(2)
                new_q = ec1.number_input("Adjust Qty", 0.0, step=0.5, value=current_qty, key=f"q_{item['id']}")
                new_use = ec2.number_input("Daily Use", 0.0, step=0.1, value=daily_use, key=f"u_{item['id']}")
                
                if new_q != current_qty or new_use != daily_use:
                    updates = {'quantity': new_q, 'daily_usage': new_use, 'last_updated': firestore.SERVER_TIMESTAMP}
                    if new_q > current_qty: updates['last_restocked'] = firestore.SERVER_TIMESTAMP
                    db.collection('inventory').document(item['id']).update(updates)
                    st.rerun()
                
                b1, b2 = st.columns(2)
                if b1.button("🗑️ Delete", key=f"d_{item['id']}", use_container_width=True):
                    db.collection('inventory').document(item['id']).delete(); st.rerun()
                if b2.button("➕ Add to Cart", key=f"ac_{item['id']}", use_container_width=True):
                    deficit = max(1.0, thresh - current_qty)
                    db.collection('shopping_list').add({
                        "item_name": item['item_name'], "household_id": hh_id,
                        "qty_needed": deficit, "status": "Pending", "store": item.get('store', 'General')
                    })
                    st.toast("Added to Cart")

def page_shopping_list(hh_id):
    st.markdown("## 🛒 Shopping List")
    
    with st.form("quick"):
        c1,c2 = st.columns([3,1])
        it = c1.text_input("Item")
        if st.form_submit_button("Add to List", use_container_width=True) and it:
            db.collection('shopping_list').add({
                "item_name":it, "household_id":hh_id, "qty_needed": 1.0, "status":"Pending", "store":"General"
            })
            st.rerun()
    st.divider()
    
    docs = db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream()
    data = [{'id':d.id, **d.to_dict()} for d in docs]
    
    if not data: st.info("Shopping list is empty."); return

    stores = list(set([d.get('store','General') for d in data]))
    for s in stores:
        st.markdown(f"#### 📍 {s}")
        for i in [d for d in data if d.get('store')==s]:
            c1,c2 = st.columns([1,4])
            if c1.button("✓ Mark Bought", key=i['id'], use_container_width=True):
                db.collection('shopping_list').document(i['id']).update({"status":"Bought"}); st.rerun()
            c2.markdown(f"**{i['item_name']}** (Buy: {int(i.get('qty_needed',1))})")
        st.divider()

if __name__ == "__main__":
    main()
