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

        /* 2. FORCE TEXT COLOR TO BLACK (Fixes the invisible text issue) */
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
        input[type="text"], input[type="password"] {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important; /* Safari/Chrome fix */
            caret-color: #333333 !important; /* Cursor color */
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

        /* 5. TABS - Fix text visibility in tabs */
        button[data-baseweb="tab"] {
            color: #333333 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #43A047 !important;
            border-bottom-color: #43A047 !important;
        }

        /* 6. Fix Login Form Labels specifically */
        .stTextInput > label {
            color: #333333 !important;
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
    
    # Sidebar
    with st.sidebar:
        st.title("🥗 Menu")
        st.caption(f"ID: {hh_id}")
        menu = st.radio("Go to", ["📸 AI Scanner", "📦 My Kitchen", "🛒 Shopping List"], label_visibility="collapsed")
        st.divider()
        if st.button("Log Out"):
            st.session_state.user_info = None
            st.rerun()

    # Routing
    if menu == "📸 AI Scanner":
        page_scanner(hh_id)
    elif menu == "📦 My Kitchen":
        page_inventory(hh_id)
    elif menu == "🛒 Shopping List":
        page_shopping_list(hh_id)

# --- PAGE: AI SCANNER ---
def page_scanner(hh_id):
    st.title("📸 Smart Entry")
    st.write("Upload receipts or photos of groceries.")
    
    img_file = st.file_uploader("", type=['jpg','png','jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("Analyze & Add"):
            with st.spinner("🤖 Analyzing freshness & brands..."):
                try:
                    prompt = """
                    Analyze this grocery image. Return a JSON list.
                    Fields: item_name, quantity (int), category (Produce, Dairy, Pantry, etc),
                    estimated_expiry (YYYY-MM-DD), suggested_store (Costco, Whole Foods, General),
                    storage_location (Fridge, Freezer, Pantry).
                    """
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=[prompt, image])
                    data = json.loads(response.text.replace("```json","").replace("```","").strip())
                    
                    st.success(f"Found {len(data)} items!")
                    st.json(data)
                    
                    # Auto-Save
                    batch = db.batch()
                    for item in data:
                        ref = db.collection('inventory').document()
                        item['household_id'] = hh_id
                        item['added_at'] = firestore.SERVER_TIMESTAMP
                        batch.set(ref, item)
                    batch.commit()
                    st.toast("Saved to Kitchen!")
                    time.sleep(2)
                    
                except Exception as e:
                    st.error(f"Error: {e}")

# --- PAGE: INVENTORY (GRID LAYOUT) ---
def page_inventory(hh_id):
    c1, c2 = st.columns([3,1])
    c1.title("🥬 My Kitchen")
    
    # Fetch
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    
    if not items:
        st.info("Kitchen is empty.")
        return

    # Sort by Expiry
    items.sort(key=lambda x: x.get('estimated_expiry', '2099-12-31'))

    # GRID DISPLAY (3 Columns)
    cols = st.columns(3)
    today = datetime.date.today()
    
    for idx, item in enumerate(items):
        with cols[idx % 3]: # Cycle through columns 0, 1, 2
            # Calculate Expiry
            try:
                exp = datetime.datetime.strptime(item.get('estimated_expiry', ''), "%Y-%m-%d").date()
                days = (exp - today).days
            except:
                days = 999
            
            # Badge Logic
            if days < 0: badge = "🔴 Expired"
            elif days <= 3: badge = "🟠 Use Soon"
            else: badge = f"🟢 {days} days"
            
            # CARD UI
            with st.container():
                st.markdown(f"**{item['item_name']}**")
                st.caption(f"{badge} • {item.get('storage_location','Pantry')}")
                st.write(f"Qty: {item.get('quantity', 1)}")
                
                # Buttons row
                b1, b2 = st.columns(2)
                if b1.button("➕ List", key=f"add_{item['id']}"):
                    db.collection('shopping_list').add({
                        "item_name": item['item_name'],
                        "household_id": hh_id,
                        "store": item.get('suggested_store', 'General'),
                        "status": "Pending"
                    })
                    st.toast("Added to list")
                
                if b2.button("🗑️", key=f"del_{item['id']}"):
                    db.collection('inventory').document(item['id']).delete()
                    st.rerun()
            st.write("") # Spacer

# --- PAGE: SHOPPING LIST ---
def page_shopping_list(hh_id):
    st.title("🛒 Shopping List")
    
    # Quick Add Bar
    with st.form("quick_add", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        new_item = c1.text_input("Item", placeholder="Milk, Eggs...", label_visibility="collapsed")
        store = c2.selectbox("Store", ["General", "Costco", "Whole Foods", "Trader Joe's"], label_visibility="collapsed")
        if c3.form_submit_button("Add"):
            if new_item:
                db.collection('shopping_list').add({
                    "item_name": new_item,
                    "household_id": hh_id, 
                    "store": store, 
                    "status": "Pending"
                })
                st.rerun()
    
    st.divider()

    # List Display
    docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    data = [{'id': d.id, **d.to_dict()} for d in docs]
    
    if not data:
        st.success("All caught up! 🎉")
        return

    # Group by Store
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





