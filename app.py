import streamlit as st
import google.genai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import json
import datetime
import uuid
import time

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="KitchenMind Pro", page_icon="🥗", layout="wide")

# --- CUSTOM CSS (THE "INSTACART" THEME) ---
def local_css():
    st.markdown("""
    <style>
        /* 1. Main Background - Force White */
        .stApp {
            background-color: #FFFFFF;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }

        /* 2. FORCE TEXT COLOR TO BLACK */
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, div, span {
            color: #333333 !important;
        }
        
        /* 3. INPUT FIELDS - Force White Background & Dark Text */
        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0 !important;
            color: #333333 !important;
            border-radius: 10px !important;
        }
        input[type="text"], input[type="password"], input[type="number"] {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
            caret-color: #333333 !important;
        }
        
        /* 4. BUTTONS - Instacart Green */
        div.stButton > button {
            background-color: #43A047 !important;
            color: white !important;
            border-radius: 20px !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
        }
        div.stButton > button:hover {
            background-color: #2E7D32 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* 5. TABS & EXPANDERS */
        button[data-baseweb="tab"] {
            color: #333333 !important;
        }
        div[data-testid="stExpander"] {
            background-color: #FAFAFA !important;
            border-radius: 10px;
        }
        
        /* 6. Clean up top spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 5rem;
        }
    </style>
    """, unsafe_allow_html=True)

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
            st.error("❌ Firebase Key not found. Check secrets or local JSON.")
            st.stop()
    firebase_admin.initialize_app(cred)

db = firestore.client()


# --- 2. AUTHENTICATION & MAIN FLOW ---

def main():
    local_css() # Apply the theme
    
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None 

    if not st.session_state.user_info:
        login_signup_screen()
    else:
        app_interface(st.session_state.user_info)

def login_signup_screen():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🥗 KitchenMind")
        st.caption("Smart Inventory for Modern Families")
        
        tab1, tab2 = st.tabs(["Login", "Create Household"])
        
        with tab1:
            with st.form("login"):
                email = st.text_input("Email").lower().strip()
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    users = db.collection('users').where('email', '==', email).where('password', '==', password).stream()
                    user = next(users, None)
                    if user:
                        data = user.to_dict()
                        st.session_state.user_info = {"email": data['email'], "household_id": data['household_id']}
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

        with tab2:
            st.write("New here?")
            new_email = st.text_input("New Email").lower().strip()
            new_pass = st.text_input("New Password", type="password")
            mode = st.radio("I want to:", ["Create New Household", "Join Existing"])
            
            if mode == "Create New Household":
                hh_name = st.text_input("Family Name (e.g. The Smiths)")
            else:
                join_id = st.text_input("Enter Household ID")

            if st.button("Get Started"):
                if not new_email or not new_pass:
                    st.error("Email and Password required.")
                    return
                
                # Check duplicate user
                if next(db.collection('users').where('email', '==', new_email).stream(), None):
                    st.error("Email already registered.")
                    return

                if mode == "Create New Household":
                    if not hh_name:
                        st.error("Enter a family name.")
                        return
                    hh_id = str(uuid.uuid4())[:6].upper()
                    db.collection('households').document(hh_id).set({"name": hh_name, "id": hh_id})
                    db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_id})
                    st.success(f"Welcome! Your Household ID is: **{hh_id}**")
                    st.info("Go to 'Login' tab to enter.")
                    
                else: # Join Mode
                    if db.collection('households').document(join_id).get().exists:
                        db.collection('users').add({"email": new_email, "password": new_pass, "household_id": join_id})
                        st.success("Joined! Please Login.")
                    else:
                        st.error("Invalid Household ID.")

# --- 3. APP INTERFACE ---

def app_interface(user):
    hh_id = user['household_id']
    
    with st.sidebar:
        st.title("🥗 Menu")
        st.caption(f"ID: {hh_id}")
        menu = st.radio("Go to", ["📸 AI Scanner", "📦 My Kitchen", "🛒 Shopping List"], label_visibility="collapsed")
        st.divider()
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.rerun()

    if menu == "📸 AI Scanner":
        page_scanner(hh_id)
    elif menu == "📦 My Kitchen":
        page_inventory(hh_id)
    elif menu == "🛒 Shopping List":
        page_shopping_list(hh_id)

# --- PAGE: AI SCANNER (UPDATED WITH UNIT DETECTION) ---
def page_scanner(hh_id):
    st.title("📸 Smart Entry")
    st.write("Upload a photo. Gemini will now detect Units (kg, liters, etc).")
    
    if 'scanned_data' not in st.session_state:
        st.session_state.scanned_data = None

    img_file = st.file_uploader("", type=['jpg','png','jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("Analyze Image"):
            with st.spinner("🤖 Analyzing Items & Units..."):
                try:
                    # UPDATED PROMPT: Added 'unit'
                    prompt = """
                    Analyze this grocery image. Return a JSON list.
                    Fields: 
                    - item_name (string)
                    - quantity (float. e.g. 1.5)
                    - unit (string. e.g. 'kg', 'lbs', 'gal', 'liters', 'box', 'count'. Default to 'count' if unsure.)
                    - category (Produce, Dairy, Pantry, etc)
                    - estimated_expiry (YYYY-MM-DD. Estimate based on item type)
                    - threshold (float. Suggest minimum stock level.)
                    - suggested_store (Costco, Whole Foods, or General)
                    - storage_location (Fridge, Freezer, Pantry)
                    """
                    response = client.models.generate_content(model="gemini-flash-latest", contents=[prompt, image])
                    clean_json = response.text.replace("```json","").replace("```","").strip()
                    st.session_state.scanned_data = json.loads(clean_json)
                except Exception as e:
                    st.error(f"Error: {e}")

    # EDITABLE TABLE SECTION
    if st.session_state.scanned_data:
        st.divider()
        st.info("👇 Edit values below before saving.")
        
        edited_df = st.data_editor(
            st.session_state.scanned_data,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "item_name": "Item Name",
                "category": st.column_config.SelectboxColumn("Category", options=["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages", "Household"]),
                "quantity": st.column_config.NumberColumn("Qty", min_value=0.1, step=0.1),
                "unit": st.column_config.SelectboxColumn("Unit", options=["count", "kg", "lbs", "g", "oz", "liters", "gal", "box", "pack"]),
                "threshold": st.column_config.NumberColumn("Min Limit", min_value=0, step=1),
                "estimated_expiry": st.column_config.DateColumn("Expiry")
            }
        )

        if st.button("Confirm & Save", type="primary"):
            batch = db.batch()
            for item in edited_df:
                ref = db.collection('inventory').document()
                # Ensure correct types
                item['quantity'] = float(item.get('quantity', 1))
                item['threshold'] = float(item.get('threshold', 1))
                item['household_id'] = hh_id
                item['added_at'] = firestore.SERVER_TIMESTAMP
                batch.set(ref, item)
            batch.commit()
            st.success("✅ Saved to Kitchen!")
            st.session_state.scanned_data = None
            time.sleep(2)
            st.rerun()

# --- PAGE: INVENTORY (UPDATED: EDIT EVERYTHING) ---
def page_inventory(hh_id):
    c1, c2 = st.columns([3,1])
    c1.title("🥬 My Kitchen")
    
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    
    shop_docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    shopping_list_names = {d.to_dict()['item_name'].lower() for d in shop_docs}

    if not items:
        st.info("Kitchen is empty.")
        return

    # Sort
    items.sort(key=lambda x: x.get('item_name', ''))

    cols = st.columns(2)
    today = datetime.date.today()
    
    for idx, item in enumerate(items):
        with cols[idx % 2]:
            # --- LOGIC ENGINE ---
            current_qty = float(item.get('quantity', 1))
            user_threshold = float(item.get('threshold', 1))
            daily_usage = float(item.get('daily_usage', 0))
            
            # 1. Spoilage Days
            try:
                exp_date_obj = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
                days_to_spoil = (exp_date_obj - today).days
            except:
                days_to_spoil = 999
                exp_date_obj = today + datetime.timedelta(days=365) # Default for date picker
            
            # 2. Consumption Days
            days_to_empty = int(current_qty / daily_usage) if daily_usage > 0 else 999
            
            # 3. Minimum Days Left & Logic
            days_left = min(days_to_spoil, days_to_empty)
            is_low_stock = current_qty < user_threshold
            is_critical_time = days_left < 7
            
            # AUTO-ADD
            if (is_low_stock or is_critical_time) and item['item_name'].lower() not in shopping_list_names:
                db.collection('shopping_list').add({
                    "item_name": item['item_name'],
                    "household_id": hh_id,
                    "store": item.get('suggested_store', 'General'),
                    "status": "Pending",
                    "reason": "Auto-Refill"
                })
                shopping_list_names.add(item['item_name'].lower())
                st.toast(f"🚨 Added {item['item_name']} to list!")

            # --- UI CARD ---
            if days_left < 0: badge = "🔴 Expired"
            elif days_left < 7: badge = f"🟠 {days_left}d Left"
            else: badge = f"🟢 {days_left} days"
            
            with st.container():
                st.markdown(f"**{item['item_name']}**")
                st.caption(f"{badge} • {item.get('category','General')}")
                
                # MAIN STATS (Editable Qty & Unit)
                c_qty, c_unit = st.columns([1, 1])
                new_qty = c_qty.number_input("Qty", 0.0, step=0.5, value=current_qty, key=f"q_{item['id']}")
                # Just display unit for now to save space, or make editable in expander
                c_unit.write(f"**{item.get('unit', 'count')}**")

                # EXPANDER: EDIT ALL DETAILS
                with st.expander("Edit Details"):
                    new_unit = st.text_input("Unit", value=item.get('unit', 'count'), key=f"un_{item['id']}")
                    new_cat = st.selectbox("Category", ["Produce", "Dairy", "Meat", "Pantry", "Frozen", "Spices", "Beverages"], index=0, key=f"cat_{item['id']}")
                    new_expiry = st.date_input("Expiry Date", value=exp_date_obj, key=f"ex_{item['id']}")
                    new_thresh = st.number_input("Threshold", 0.0, value=user_threshold, key=f"t_{item['id']}")
                    new_usage = st.number_input("Daily Use", 0.0, step=0.1, value=daily_usage, key=f"u_{item['id']}")

                # Update DB on Change
                # We check if anything changed inside the expander OR the main quantity box
                updates = {}
                if new_qty != current_qty: updates['quantity'] = new_qty
                if new_unit != item.get('unit', 'count'): updates['unit'] = new_unit
                if new_expiry != exp_date_obj: updates['estimated_expiry'] = str(new_expiry)
                if new_thresh != user_threshold: updates['threshold'] = new_thresh
                if new_usage != daily_usage: updates['daily_usage'] = new_usage
                
                if updates:
                    db.collection('inventory').document(item['id']).update(updates)
                    st.rerun()

                # Buttons
                b1, b2 = st.columns(2)
                if b1.button("➕ List", key=f"ad_{item['id']}"):
                    if item['item_name'].lower() not in shopping_list_names:
                        db.collection('shopping_list').add({
                            "item_name": item['item_name'], "household_id": hh_id, "store": item.get('suggested_store', 'General'), "status": "Pending"
                        })
                        st.toast("Added!")
                
                if b2.button("🗑️", key=f"dl_{item['id']}"):
                    db.collection('inventory').document(item['id']).delete()
                    st.rerun()
            st.write("") 

# --- PAGE: SHOPPING LIST ---
def page_shopping_list(hh_id):
    st.title("🛒 Shopping List")
    
    with st.form("quick_add", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        new_item = c1.text_input("Item", placeholder="Avocados...", label_visibility="collapsed")
        store = c2.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"], label_visibility="collapsed")
        if c3.form_submit_button("Add"):
            if new_item:
                db.collection('shopping_list').add({
                    "item_name": new_item, "household_id": hh_id, "store": store, "status": "Pending"
                })
                st.rerun()
    
    st.divider()

    docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    data = [{'id': d.id, **d.to_dict()} for d in docs]
    
    if not data:
        st.success("All caught up! 🎉")
        return

    stores = list(set([d.get('store', 'General') for d in data]))
    
    for store in stores:
        st.markdown(f"#### 📍 {store}")
        store_items = [d for d in data if d.get('store') == store]
        for item in store_items:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{item['item_name']}**")
            if c2.button("✓", key=item['id']):
                db.collection('shopping_list').document(item['id']).update({"status": "Bought"})
                st.rerun()
        st.divider()

if __name__ == "__main__":
    main()





