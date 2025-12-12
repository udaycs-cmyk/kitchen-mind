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
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (MOBILE LUXURY THEME) ---
def local_css():
    st.markdown("""
    <style>
        /* 1. APP BACKGROUND */
        .stApp {
            background-color: #0E0E0E;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
        }

        /* 2. MOBILE-FIRST TYPOGRAPHY */
        h1, h2, h3 { 
            color: #D4AF37 !important; 
            font-weight: 700; 
            letter-spacing: -0.5px;
        }
        p, label, div, span { 
            color: #F5F5F7 !important; 
            font-size: 16px; 
        }

        /* 3. THUMB-FRIENDLY INPUTS */
        div[data-baseweb="input"] {
            background-color: #1C1C1E !important;
            border: 1px solid #333333 !important;
            border-radius: 16px !important; 
            height: 50px; 
            align-items: center;
        }
        input {
            color: #FFFFFF !important;
            font-size: 18px !important; 
            padding-left: 10px;
        }
        
        /* 4. BIG "TAP" BUTTONS */
        div.stButton > button {
            background-image: linear-gradient(180deg, #D4AF37 0%, #B4941F 100%);
            color: #000000 !important;
            border-radius: 25px !important;
            border: none !important;
            height: 55px !important; 
            font-size: 18px !important;
            font-weight: 700 !important;
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
        }
        div.stButton > button:active {
            transform: scale(0.98); 
        }

        /* 5. CARDS (Mobile Friendly) */
        div[data-testid="stForm"], div[data-testid="stExpander"], .stContainer {
            background-color: #151515 !important;
            border: 1px solid #222;
            border-left: 4px solid #D4AF37;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 15px;
        }

        /* 6. MEDIA QUERIES */
        @media (max-width: 640px) {
            .block-container {
                padding-top: 2rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            h1 { font-size: 28px !important; }
            h2 { font-size: 24px !important; }
            header { visibility: hidden; } 
        }

        /* 7. BADGE */
        .new-badge {
            background-color: #D4AF37;
            color: #000;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 0.7em;
            font-weight: 800;
            margin-left: 5px;
        }
        
        /* 8. TABS STYLE */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            color: #888888 !important;
            font-size: 16px;
            padding: 10px 20px;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
             color: #D4AF37 !important;
             border-bottom: 3px solid #D4AF37 !important;
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
        st.markdown("### 🥗 Menu")
        if st.button("🏠 Home Dashboard"):
            st.session_state.current_page = 'home'
            st.rerun()
        st.divider()
        st.caption(f"Household: {st.session_state.user_info['household_id']}")
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.session_state.current_page = 'home'
            st.rerun()

def login_signup_screen():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #D4AF37; margin-bottom: 5px;'>RE:STOCK</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 14px; opacity: 0.7;'>PREMIUM KITCHEN MANAGER</p>", unsafe_allow_html=True)
        st.write("")
        
        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("#### Welcome Back")
                email = st.text_input("Email").lower().strip()
                password = st.text_input("Password", type="password")
                st.write("")
                if st.form_submit_button("LOGIN"):
                    users = db.collection('users').where('email', '==', email).where('password', '==', password).stream()
                    user = next(users, None)
                    if user:
                        st.session_state.user_info = user.to_dict()
                        st.session_state.current_page = 'home'
                        st.rerun()
                    else: st.error("Invalid credentials.")

        with tab2:
            with st.form("signup_form"):
                st.markdown("#### New Account")
                new_email = st.text_input("New Email").lower().strip()
                new_pass = st.text_input("Password", type="password")
                mode = st.radio("Setup", ["Create New Household", "Join Existing"])
                hh_input = st.text_input("Household Name or ID")
                st.write("")
                
                if st.form_submit_button("CREATE ACCOUNT"):
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
                        else:
                            st.error("Invalid ID")

# --- 4. HOME DASHBOARD ---
def page_home_dashboard(hh_id):
    st.markdown("<h2>👋 Dashboard</h2>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📸 AI Scanner <span class='new-badge'>PRO</span>", unsafe_allow_html=True)
        if st.button("Scan Items"):
            st.session_state.current_page = 'kitchen_mind_pro'
            st.rerun()
    with c2:
        st.markdown("#### 📝 Manual")
        if st.button("Type Entry"):
            st.session_state.current_page = 'manual_add'
            st.rerun()
            
    st.write("")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 📦 Inventory")
        if st.button("View Stock"):
            st.session_state.current_page = 'inventory'
            st.rerun()
    with c4:
        st.markdown("#### 🛒 Cart")
        if st.button("Shopping List"):
            st.session_state.current_page = 'shopping_list'
            st.rerun()

# --- 5. KITCHEN MIND PRO (UPDATED WITH SEPARATE CAMERA/UPLOAD) ---
def page_kitchen_mind_pro(hh_id):
    st.button("← Back", on_click=lambda: st.session_state.update(current_page='home'))
    st.markdown("## 📸 AI Scanner")
    st.info("Choose Camera to snap a photo, or Upload for existing files.")
    
    with st.container(): 
        # --- NEW: SPLIT TABS FOR CAMERA VS UPLOAD ---
        tab_cam, tab_file = st.tabs(["📸 Take Photo", "📂 Upload File"])
        
        img_buffer = None
        
        with tab_cam:
            # st.camera_input creates a widget that opens the webcam/phone camera directly
            cam_pic = st.camera_input("Snap Picture")
            if cam_pic:
                img_buffer = cam_pic
                
        with tab_file:
            up_pic = st.file_uploader("Choose from Device", type=['jpg','png','jpeg'])
            if up_pic:
                img_buffer = up_pic

        # Reset state if new image is loaded
        if 'last_analyzed_image' not in st.session_state:
            st.session_state.last_analyzed_image = None
            
        if 'scanned_data' not in st.session_state:
            st.session_state.scanned_data = None

        if img_buffer:
            # If we have a new image buffer that is different from the last one we processed
            # (Streamlit re-runs scripts, so we check if button pressed to process)
            
            # Display the selected image (from either source)
            image = Image.open(img_buffer)
            # st.image(image, use_container_width=True) # Camera input already shows preview, preventing double show
            
            if st.button("Analyze This Image", type="primary"):
                with st.spinner("🤖 Processing..."):
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

        # Show Data Editor if data exists
        if st.session_state.scanned_data:
            st.divider()
            st.markdown("#### Review AI Results")
            edited_df = st.data_editor(
                st.session_state.scanned_data,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "item_name": "Item",
                    "quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                    "threshold": st.column_config.NumberColumn("Limit"),
                    "estimated_expiry": st.column_config.DateColumn("Exp")
                }
            )

            if st.button("Confirm & Save to Inventory"):
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
                st.success("Saved!")
                st.session_state.scanned_data = None
                time.sleep(1)
                st.session_state.current_page = 'inventory'
                st.rerun()

# --- 6. MANUAL ADD ---
def page_manual_add(hh_id):
    st.button("← Back", on_click=lambda: st.session_state.update(current_page='home'))
    st.markdown("## 📝 Manual Add")
    
    with st.form("manual_add"):
        name = st.text_input("Item Name")
        category = st.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"])
        
        c1, c2 = st.columns(2)
        qty = c1.number_input("Count", 1.0, step=0.5)
        init_qty = c2.number_input("Full Size", 1.0, step=0.5, value=qty)
        
        c3, c4 = st.columns(2)
        weight = c3.number_input("Weight", 0.0, step=0.5)
        w_unit = c4.selectbox("Unit", ["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"])
        
        st.divider()
        c5, c6 = st.columns(2)
        threshold = c5.number_input("Min Limit", 1.0)
        expiry = c6.date_input("Expiry", datetime.date.today() + datetime.timedelta(days=7))
        store = st.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"])
        
        notes = st.text_area("Notes")
        barcode = st.text_input("Barcode")

        if st.form_submit_button("Save Item"):
            if name:
                db.collection('inventory').add({
                    "item_name": name, "category": category,
                    "quantity": float(qty), "initial_quantity": float(init_qty),
                    "weight": float(weight), "weight_unit": w_unit,
                    "threshold": float(threshold), "estimated_expiry": str(expiry),
                    "suggested_store": store, "notes": notes, "barcode": barcode,
                    "household_id": hh_id,
                    "added_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                    "last_restocked": firestore.SERVER_TIMESTAMP,
                    "storage_location": "Pantry"
                })
                st.success(f"Saved {name}!")
                time.sleep(1)
                st.session_state.current_page = 'inventory'
                st.rerun()

# --- 7. INVENTORY ---
def page_inventory(hh_id):
    st.button("← Back", on_click=lambda: st.session_state.update(current_page='home'))
    st.markdown("## 📦 Stock")
    
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    
    shop_docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    shopping_list_names = {d.to_dict()['item_name'].lower() for d in shop_docs}

    if not items:
        st.info("No items yet.")
        if st.button("Add Item"):
            st.session_state.current_page = 'manual_add'
            st.rerun()
        return
        
    items.sort(key=lambda x: x.get('item_name', ''))
    today = datetime.date.today()
    
    for item in items:
        current_qty = float(item.get('quantity', 1))
        initial_qty = float(item.get('initial_quantity', current_qty))
        thresh = float(item.get('threshold', 1))
        daily_use = float(item.get('daily_usage', 0))
        
        try:
            exp = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
            d_spoil = (exp - today).days
        except: d_spoil = 999
        
        d_empty = int(current_qty/daily_use) if daily_use > 0 else 999
        days_left = min(d_spoil, d_empty)
        qty_deficit = max(1.0, thresh - current_qty) 
        
        is_low = current_qty < thresh
        is_urgent = days_left < 7
        
        if (is_low or is_urgent) and item['item_name'].lower() not in shopping_list_names:
            db.collection('shopping_list').add({
                "item_name": item['item_name'], "household_id": hh_id,
                "store": item.get('suggested_store', 'General'),
                "qty_needed": qty_deficit,
                "status": "Pending", "reason": "Auto-Refill"
            })
            shopping_list_names.add(item['item_name'].lower())
            st.toast(f"🚨 Added {item['item_name']}")

        if days_left < 0: badge = "🔴 Exp"
        elif days_left < 7: badge = f"🟠 {days_left}d"
        else: badge = f"🟢 {days_left}d"

        with st.container():
            c1, c2 = st.columns([2,1])
            c1.markdown(f"**{item['item_name']}**")
            c1.caption(f"{badge} • {item.get('category','Gen')}")
            
            new_q = c2.number_input("", 0.0, step=0.5, value=current_qty, key=f"q_{item['id']}", label_visibility="collapsed")
            
            with st.expander("Edit"):
                n_init = st.number_input("Full Size", 0.0, value=initial_qty, key=f"iq_{item['id']}")
                n_w = st.number_input("Weight", 0.0, value=float(item.get('weight',0)), key=f"w_{item['id']}")
                n_thr = st.number_input("Limit", 0.0, value=thresh, key=f"t_{item['id']}")
                n_use = st.number_input("Daily Use", 0.0, value=daily_use, key=f"du_{item['id']}")
                
                c_b1, c_b2 = st.columns(2)
                if c_b1.button("Delete", key=f"d_{item['id']}"):
                    db.collection('inventory').document(item['id']).delete()
                    st.rerun()
                if c_b2.button("Add to List", key=f"l_{item['id']}"):
                    needed = max(1.0, thresh - new_q)
                    db.collection('shopping_list').add({
                        "item_name": item['item_name'], "household_id": hh_id,
                        "store": item.get('suggested_store', 'General'),
                        "qty_needed": needed,
                        "status": "Pending", "reason": "Manual Add"
                    })
                    st.toast(f"Added")

            updates = {}
            if new_q != current_qty: 
                updates['quantity'] = new_q
                updates['last_updated'] = firestore.SERVER_TIMESTAMP
            if n_init != initial_qty: updates['initial_quantity'] = n_init
            if n_w != float(item.get('weight',0)): updates['weight'] = n_w
            if n_thr != thresh: updates['threshold'] = n_thr
            if n_use != daily_use: updates['daily_usage'] = n_use
            
            if updates:
                db.collection('inventory').document(item['id']).update(updates)
                st.rerun()

# --- 8. SHOPPING LIST ---
def page_shopping_list(hh_id):
    st.button("← Back", on_click=lambda: st.session_state.update(current_page='home'))
    st.markdown("## 🛒 Cart")
    
    with st.form("quick"):
        c1,c2 = st.columns([2,1])
        it = c1.text_input("Item")
        qn = c2.number_input("Qty", 1.0, step=1.0) 
        if st.form_submit_button("Add Item") and it:
            db.collection('shopping_list').add({
                "item_name":it, "household_id":hh_id, 
                "qty_needed": float(qn),
                "status":"Pending", "store":"General"
            })
            st.rerun()
    st.divider()
    
    docs = db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream()
    data = [{'id':d.id, **d.to_dict()} for d in docs]
    
    if not data:
        st.success("List is empty!")
        return

    stores = list(set([d.get('store','General') for d in data]))
    
    for s in stores:
        st.markdown(f"#### 📍 {s}")
        store_items = [d for d in data if d.get('store')==s]
        
        for i in store_items:
            c_check, c_info = st.columns([1, 4])
            with c_check:
                if st.button("✓", key=i['id']):
                    db.collection('shopping_list').document(i['id']).update({"status":"Bought"})
                    st.rerun()
            with c_info:
                qty_show = float(i.get('qty_needed', 1))
                qty_str = f"{int(qty_show)}" if qty_show.is_integer() else f"{qty_show}"
                st.markdown(f"**{i['item_name']}**")
                st.caption(f"Buy: {qty_str}")
        st.divider()

if __name__ == "__main__":
    main()
