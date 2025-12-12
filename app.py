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
# --- API & DATABASE SETUP ---
# Setup Gemini AI (Handles both Cloud Secrets and Local Key)
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    # REPLACE THIS IF RUNNING ON LAPTOP
    GEMINI_API_KEY = "PASTE_YOUR_LOCAL_KEY_HERE" 

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.warning(f"⚠️ Gemini API Warning: {e}")

    # Setup Firebase

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
    """Fetches details from OpenFoodFacts. Returns structured dict or None."""
    if not barcode or len(barcode) < 5: return None
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('status') == 1:
            p = data['product']
            
            # Smart Weight Parsing (e.g. "500 g" -> 500, 'g')
            raw_qty = p.get('quantity', '') # e.g. "330ml"
            weight_val = 0.0
            unit_val = 'count'
            
            if raw_qty:
                # Regex to find number and text
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
    except:
        return None
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

# --- 5. KITCHEN MIND PRO (AI + WEIGHT LOGIC) ---
def page_kitchen_mind_pro(hh_id):
    st.button("← Back Home", on_click=lambda: st.session_state.update(current_page='home'))
    st.title("📸 KitchenMind Pro")
    st.info("AI Priority: Gemini Data first. Barcode Data used only if AI is empty.")

    if 'scanned_data' not in st.session_state:
        st.session_state.scanned_data = None

    img_file = st.file_uploader("", type=['jpg','png','jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("Analyze Image"):
            with st.spinner("🤖 Analyzing Items, Weights & Barcodes..."):
                try:
                    # PROMPT: Specifically asking for weight separate from quantity
                    prompt = """
                    Analyze image. If barcode visible, read digits accurately.
                    Return JSON list. Fields: 
                    - item_name (string)
                    - quantity (float. Count of items e.g. 2 bottles. Default 1)
                    - weight (float. Net weight per item e.g. 16.5)
                    - weight_unit (string. e.g. oz, g, kg, lbs, ml. Default 'count' if N/A)
                    - category, estimated_expiry (YYYY-MM-DD)
                    - threshold (float), suggested_store, storage_location, barcode (string), notes
                    """
                    response = client.models.generate_content(model="gemini-flash-latest", contents=[prompt, image])
                    clean_json = response.text.replace("```json","").replace("```","").strip()
                    ai_data = json.loads(clean_json)
                    
                    # --- PRIORITY LOGIC ---
                    for item in ai_data:
                        bc = item.get('barcode', '')
                        
                        # 1. Fetch Barcode Data (Backup)
                        db_data = fetch_barcode_data(bc) if bc else None
                        
                        if db_data:
                            # 2. Apply ONLY if AI field is missing/empty
                            if not item.get('item_name'): 
                                item['item_name'] = db_data['item_name']
                                st.toast(f"Used Barcode Name for {bc}")
                            
                            if not item.get('notes'): 
                                item['notes'] = db_data['notes']
                                
                            # Weight Fallback
                            ai_weight = item.get('weight', 0)
                            if (ai_weight is None or ai_weight == 0) and db_data['weight'] > 0:
                                item['weight'] = db_data['weight']
                                item['weight_unit'] = db_data['weight_unit']
                                st.toast(f"Used Barcode Weight for {bc}")

                    st.session_state.scanned_data = ai_data
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.scanned_data:
        st.divider()
        st.write("👇 **Review Details (AI & Barcode Merged)**")
        edited_df = st.data_editor(
            st.session_state.scanned_data,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item_name": "Item Name",
                "quantity": st.column_config.NumberColumn("Count (Qty)", min_value=1, step=1),
                "weight": st.column_config.NumberColumn("Weight", min_value=0.0, step=0.1, format="%.1f"),
                "weight_unit": st.column_config.SelectboxColumn("Unit", options=["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"]),
                "threshold": st.column_config.NumberColumn("Min Limit"),
                "estimated_expiry": st.column_config.DateColumn("Expiry"),
                "barcode": "Barcode"
            }
        )

        if st.button("Confirm & Save", type="primary"):
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

# --- 6. PAGE: MANUAL ADD (WITH WEIGHT) ---
def page_manual_add(hh_id):
    st.button("← Back Home", on_click=lambda: st.session_state.update(current_page='home'))
    st.title("📝 Add to Inventory")
    
    with st.form("manual_add"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Item Name")
        category = c2.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"])
        
        # New Weight Section
        st.markdown("#### Quantity & Weight")
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        qty = r1_c1.number_input("Count (e.g. 2 bottles)", min_value=1.0, step=1.0, value=1.0)
        weight = r1_c2.number_input("Weight (per item)", min_value=0.0, step=0.5)
        w_unit = r1_c3.selectbox("Unit", ["count", "oz", "lbs", "g", "kg", "ml", "L", "gal"])
        
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        threshold = r2_c1.number_input("Min Limit", 1.0)
        expiry = r2_c2.date_input("Expiry", datetime.date.today() + datetime.timedelta(days=7))
        store = r2_c3.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"])
        
        notes = st.text_area("Notes")
        barcode = st.text_input("Barcode")

        if st.form_submit_button("Save Item", type="primary"):
            if name:
                db.collection('inventory').add({
                    "item_name": name, "category": category,
                    "quantity": float(qty), "initial_quantity": float(qty),
                    "weight": float(weight), "weight_unit": w_unit, # Saved separately
                    "threshold": float(threshold),
                    "estimated_expiry": str(expiry), "suggested_store": store,
                    "notes": notes, "barcode": barcode,
                    "household_id": hh_id,
                    "added_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                    "last_restocked": firestore.SERVER_TIMESTAMP,
                    "storage_location": "Pantry"
                })
                st.success(f"Added {name}!")
                time.sleep(1)
                st.session_state.current_page = 'inventory'
                st.rerun()

# --- 7. PAGE: INVENTORY (DISPLAY WEIGHT) ---
def page_inventory(hh_id):
    st.button("← Back Home", on_click=lambda: st.session_state.update(current_page='home'))
    st.title("🥬 My Kitchen")
    
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    if not items:
        st.info("Empty.")
        return
        
    items.sort(key=lambda x: x.get('item_name', ''))
    cols = st.columns(2)
    today = datetime.date.today()
    
    for idx, item in enumerate(items):
        with cols[idx % 2]:
            current_qty = float(item.get('quantity', 1))
            initial_qty = float(item.get('initial_quantity', current_qty))
            thresh = float(item.get('threshold', 1))
            daily_use = float(item.get('daily_usage', 0))
            
            # ETA Logic
            try:
                exp = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
                d_spoil = (exp - today).days
            except: d_spoil = 999
            
            d_empty = int(current_qty/daily_use) if daily_use > 0 else 999
            days_left = min(d_spoil, d_empty)
            
            if days_left < 0: badge = "🔴 Expired"
            elif days_left < 7: badge = f"🟠 {days_left}d"
            else: badge = f"🟢 {days_left}d"

            with st.container():
                st.markdown(f"**{item['item_name']}**")
                # SHOW WEIGHT IN SUBTITLE
                weight_txt = f"{item.get('weight', 0)} {item.get('weight_unit', '')}" if item.get('weight', 0) > 0 else ""
                st.caption(f"{badge} • {item.get('category','General')} • {weight_txt}")
                
                c_q, c_u = st.columns([1,1])
                new_q = c_q.number_input("Count", 0.0, step=1.0, value=current_qty, key=f"q_{item['id']}")
                
                # Manual Weight Edit in Expander
                with st.expander("Edit Details"):
                    n_w = st.number_input("Weight", 0.0, value=float(item.get('weight', 0)), key=f"w_{item['id']}")
                    n_wu = st.text_input("Unit", value=item.get('weight_unit', 'count'), key=f"wu_{item['id']}")
                    n_thr = st.number_input("Threshold", 0.0, value=thresh, key=f"t_{item['id']}")
                    n_note = st.text_input("Notes", value=item.get('notes',''), key=f"nt_{item['id']}")
                
                # Updates
                updates = {}
                if new_q != current_qty: 
                    updates['quantity'] = new_q
                    updates['last_updated'] = firestore.SERVER_TIMESTAMP
                if n_w != float(item.get('weight', 0)): updates['weight'] = n_w
                if n_wu != item.get('weight_unit', ''): updates['weight_unit'] = n_wu
                if n_thr != thresh: updates['threshold'] = n_thr
                if n_note != item.get('notes',''): updates['notes'] = n_note
                
                if updates:
                    db.collection('inventory').document(item['id']).update(updates)
                    st.rerun()

                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("➕ List", key=f"l_{item['id']}"):
                    db.collection('shopping_list').add({"item_name": item['item_name'], "household_id": hh_id, "status": "Pending", "store": "General"})
                    st.toast("Added")
                if c_btn2.button("🗑️", key=f"d_{item['id']}"):
                    db.collection('inventory').document(item['id']).delete()
                    st.rerun()
            st.write("")

# --- 8. SHOPPING LIST ---
def page_shopping_list(hh_id):
    st.button("← Back Home", on_click=lambda: st.session_state.update(current_page='home'))
    st.title("🛒 Cart")
    with st.form("quick"):
        c1,c2 = st.columns([3,1])
        it = c1.text_input("Item")
        if c2.form_submit_button("Add") and it:
            db.collection('shopping_list').add({"item_name":it, "household_id":hh_id, "status":"Pending", "store":"General"})
            st.rerun()
    st.divider()
    docs = db.collection('shopping_list').where('household_id','==',hh_id).where('status','==','Pending').stream()
    data = [{'id':d.id, **d.to_dict()} for d in docs]
    stores = list(set([d.get('store','General') for d in data]))
    for s in stores:
        st.markdown(f"#### {s}")
        for i in [d for d in data if d.get('store')==s]:
            c1,c2 = st.columns([4,1])
            c1.write(f"- {i['item_name']}")
            if c2.button("✓", key=i['id']):
                db.collection('shopping_list').document(i['id']).update({"status":"Bought"})
                st.rerun()

if __name__ == "__main__":
    main()
