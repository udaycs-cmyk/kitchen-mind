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
            with st.spinner("Reading labels..."):
                try:
                    # 1. SEND TO GEMINI (Real API Call)
                    prompt = """
                    Analyze these images of food products. Return a JSON list of items found.
                    For each item extract: 
                    - item_name (be specific, e.g. 'Heinz Ketchup')
                    - quantity (default to 1)
                    - weight (float, look for net weight)
                    - weight_unit (g, kg, oz, lbs, ml, L)
                    - category (Produce, Dairy, Meat, Pantry, Frozen, Snacks, Beverages, Household)
                    - estimated_expiry (YYYY-MM-DD format if visible, else null)
                    - barcode (string, if visible)
                    - suggested_store (Costco, Whole Foods, General)
                    """
                    response = client.models.generate_content(
                        model="gemini-flash-latest", 
                        contents=[prompt] + valid
                    )
                    
                    # 2. PARSE JSON
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    ai_data = json.loads(clean_text)
                    
                    # 3. ENHANCE WITH BARCODE DATABASE
                    for item in ai_data:
                        bc = item.get('barcode', '')
                        if bc:
                            db_data = fetch_barcode_data(bc)
                            if db_data:
                                if db_data.get('item_name'): item['item_name'] = db_data['item_name']
                                if db_data.get('weight'): item['weight'] = db_data['weight']

                    st.session_state.data = ai_data
                except Exception as e:
                    st.error(f"Could not analyze. Try again. Error: {e}")

    if st.session_state.data:
        df = st.data_editor(st.session_state.data, num_rows="dynamic")
        if st.button("Save to Pantry"):
            batch=db.batch()
            for i in df:
                ref=db.collection('inventory').document()
                batch.set(ref,{**i,"household_id":hh_id,"initial_quantity":i.get('quantity',1)})
            batch.commit(); st.session_state.data=None; st.rerun()
