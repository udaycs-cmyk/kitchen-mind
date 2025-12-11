import streamlit as st
import google.genai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import json
import datetime
import uuid
import time

# --- 1. CONFIGURATION & CLOUD SETUP ---
st.set_page_config(page_title="KitchenMind Ultimate", page_icon="🥗", layout="wide")

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

# Setup Firebase Database
if not firebase_admin._apps:
    if "firebase" in st.secrets:
        # Production: Load from Streamlit Cloud Secrets
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
    else:
        # Development: Load from Local JSON file
        try:
            cred = credentials.Certificate("firebase_key.json")
        except:
            st.error("❌ Firebase Key not found. Please check your secrets or local JSON file.")
            st.stop()
            
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. AUTHENTICATION (MULTI-HOUSEHOLD) ---

def main():
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None 

    if not st.session_state.user_info:
        login_signup_screen()
    else:
        app_interface(st.session_state.user_info)

def login_signup_screen():
    st.title("🔐 KitchenMind: Login")
    
    tab1, tab2 = st.tabs(["Existing User", "New Household"])
    
    # LOGIN LOGIC
    with tab1:
        with st.form("login"):
            email = st.text_input("Email").lower().strip()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                users = db.collection('users').where('email', '==', email).where('password', '==', password).stream()
                user = next(users, None)
                if user:
                    data = user.to_dict()
                    st.session_state.user_info = {"email": data['email'], "household_id": data['household_id']}
                    st.rerun()
                else:
                    st.error("Wrong email or password.")

    # SIGNUP LOGIC
    with tab2:
        st.subheader("Create or Join")
        new_email = st.text_input("New Email").lower().strip()
        new_pass = st.text_input("New Password", type="password")
        mode = st.radio("Mode", ["Create New Household", "Join Existing"])
        
        if mode == "Create New Household":
            hh_name = st.text_input("Household Name (e.g., The Smiths)")
        else:
            join_id = st.text_input("Enter Household ID")

        if st.button("Register"):
            if not new_email or not new_pass:
                st.error("Fill all fields.")
                return
            
            # Check for existing user
            if next(db.collection('users').where('email', '==', new_email).stream(), None):
                st.error("User already exists.")
                return

            if mode == "Create New Household":
                hh_id = str(uuid.uuid4())[:6].upper()
                db.collection('households').document(hh_id).set({"name": hh_name, "id": hh_id})
                db.collection('users').add({"email": new_email, "password": new_pass, "household_id": hh_id})
                st.success(f"Created! Your Household ID is: **{hh_id}** (Share this!)")
                
            else:
                # Validate ID
                if db.collection('households').document(join_id).get().exists:
                    db.collection('users').add({"email": new_email, "password": new_pass, "household_id": join_id})
                    st.success("Joined Successfully! Please Login.")
                else:
                    st.error("Invalid Household ID.")

# --- 3. MAIN APP INTERFACE ---

def app_interface(user):
    hh_id = user['household_id']
    st.sidebar.title("🥗 KitchenMind")
    st.sidebar.info(f"Household: {hh_id}")
    
    menu = st.sidebar.radio("Menu", ["📸 AI Scanner", "📦 Inventory", "🛒 Shopping List"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user_info = None
        st.rerun()

    if menu == "📸 AI Scanner":
        page_scanner(hh_id)
    elif menu == "📦 Inventory":
        page_inventory(hh_id)
    elif menu == "🛒 Shopping List":
        page_shopping_list(hh_id)

# --- PAGE: AI SCANNER (THE BRAIN) ---
def page_scanner(hh_id):
    st.header("📸 Smart Entry")
    st.caption("Upload a photo of items or receipts. Gemini will categorize them.")
    
    img_file = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("Analyze Image"):
            with st.spinner("🤖 Analyzing brand, expiry, and quantity..."):
                try:
                    # PROMPT: Includes logic for Store and Storage Location
                    prompt = """
                    Analyze this grocery image. Identify items.
                    Return a JSON list. For each item:
                    - item_name (string)
                    - quantity (int)
                    - category (Produce, Dairy, Pantry, Frozen, Spices)
                    - estimated_expiry (YYYY-MM-DD. Estimate based on item type. e.g. Milk=7d)
                    - suggested_store (Costco, Whole Foods, or General. Guess based on brand if visible.)
                    - storage_location (Fridge, Freezer, or Pantry. Guess based on type.)
                    """
                    
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=[prompt, image])
                    data = json.loads(response.text.replace("```json","").replace("```","").strip())
                    
                    st.success(f"Identified {len(data)} items!")
                    
                    with st.form("save_scan"):
                        st.json(data)
                        if st.form_submit_button("Save to Inventory"):
                            batch = db.batch()
                            for item in data:
                                ref = db.collection('inventory').document()
                                item['household_id'] = hh_id
                                item['added_at'] = firestore.SERVER_TIMESTAMP
                                batch.set(ref, item)
                            batch.commit()
                            st.toast("Saved!")
                            time.sleep(1)
                            st.rerun()
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- PAGE: INVENTORY (BUSINESS LOGIC CENTER) ---
def page_inventory(hh_id):
    st.header("📦 Inventory Management")
    
    # 1. FETCH & FILTER
    docs = db.collection('inventory').where('household_id', '==', hh_id).stream()
    items = [{'id': d.id, **d.to_dict()} for d in docs]
    
    if not items:
        st.info("Inventory empty.")
        return

    # 2. LOGIC: Sort by Expiry Date (Urgent stuff first)
    today = datetime.date.today()
    items.sort(key=lambda x: x.get('estimated_expiry', '2099-12-31'))

    # 3. DISPLAY GRID
    for item in items:
        # CALCULATION: Days Left
        try:
            exp_date = datetime.datetime.strptime(item.get('estimated_expiry', '2099-12-31'), "%Y-%m-%d").date()
            days_left = (exp_date - today).days
        except:
            days_left = 999

        # LOGIC: Status Flags
        if days_left < 0:
            color = "🔴"
            status = "EXPIRED"
        elif days_left <= 3:
            color = "🟠"
            status = "USE SOON"
        else:
            color = "🟢"
            status = "OK"

        # UI CARD
        with st.expander(f"{color} {item['item_name']} (Qty: {item['quantity']})"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Expires:** {days_left} days")
            c2.write(f"**Loc:** {item.get('storage_location', 'Pantry')}")
            c3.write(f"**Store:** {item.get('suggested_store', 'General')}")
            
            # ACTION: Add to Shopping List (Logic: checks if already added)
            if st.button("Add to Shopping List", key=f"shop_{item['id']}"):
                db.collection('shopping_list').add({
                    "item_name": item['item_name'],
                    "household_id": hh_id,
                    "store": item.get('suggested_store', 'General'),
                    "status": "Pending",
                    "reason": "Restock"
                })
                st.toast("Added to list!")

            # ACTION: Consume/Delete (Database Write)
            if st.button("Mark Consumed (Delete)", key=f"del_{item['id']}"):
                db.collection('inventory').document(item['id']).delete()
                st.rerun()

# --- PAGE: SHOPPING LIST (STORE OPTIMIZED) ---
def page_shopping_list(hh_id):
    st.header("🛒 Shopping List")
    
    # MANUAL ENTRY
    with st.form("quick_add"):
        c1, c2 = st.columns([3, 1])
        new_item = c1.text_input("Add Item")
        store_pref = c2.selectbox("Store", ["Costco", "Whole Foods", "Trader Joe's", "General"])
        if st.form_submit_button("Add"):
            db.collection('shopping_list').add({
                "item_name": new_item,
                "household_id": hh_id,
                "store": store_pref,
                "status": "Pending"
            })
            st.rerun()

    st.divider()

    # LOGIC: Group by Store (Efficient Shopping)
    docs = db.collection('shopping_list').where('household_id', '==', hh_id).where('status', '==', 'Pending').stream()
    data = [{'id': d.id, **d.to_dict()} for d in docs]
    
    # Get unique stores
    stores = list(set([d.get('store', 'General') for d in data]))
    
    if not data:
        st.success("All caught up! No shopping needed.")
    
    for store in stores:
        st.subheader(f"🏬 {store}")
        store_items = [d for d in data if d.get('store', 'General') == store]
        
        for item in store_items:
            c1, c2 = st.columns([4, 1])
            c1.write(f"- {item['item_name']}")
            if c2.button("Done", key=item['id']):
                db.collection('shopping_list').document(item['id']).update({"status": "Bought"})
                st.rerun()

if __name__ == "__main__":
    main()