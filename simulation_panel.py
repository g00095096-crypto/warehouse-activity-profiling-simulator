import streamlit as st
from utils.data_loader import load_main_datasets

# --------------- SIMULATION PANEL PAGE ---------------

st.title("🧪 Simulation Panel")

st.markdown(
    """
    This panel uses the **real datasets** from your project:
    - `SKU_Demand_Profile.csv`
    - `SKU_Clusters.csv`
    - `SKU_Associations.csv`
    - `Warehouse Challenge Dataset.xlsx`
    """
)

# ---- Load all datasets using the helper from utils/data_loader.py ----
data = load_main_datasets()

demand_df = data.get("demand")
clusters_df = data.get("clusters")
assoc_df = data.get("associations")
raw_df = data.get("warehouse_raw")

st.sidebar.header("Simulation Controls")
st.sidebar.write("You can add parameters here later (e.g., # of pickers, policies, etc.).")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Demand Profile", "SKU Clusters", "SKU Associations", "Raw Warehouse Data"]
)

with tab1:
    st.subheader("SKU Demand Profile")
    if demand_df is not None:
        st.dataframe(demand_df.head())
    else:
        st.warning("Could not load `SKU_Demand_Profile.csv` from the project root.")

with tab2:
    st.subheader("SKU Clusters")
    if clusters_df is not None:
        st.dataframe(clusters_df.head())
    else:
        st.info("`SKU_Clusters.csv` not found or failed to load.")

with tab3:
    st.subheader("SKU Associations")
    if assoc_df is not None:
        st.dataframe(assoc_df.head())
    else:
        st.info("`SKU_Associations.csv` not found or failed to load.")

with tab4:
    st.subheader("Warehouse Challenge Dataset (Raw)")
    if raw_df is not None:
        st.dataframe(raw_df.head())
    else:
        st.info("`Warehouse Challenge Dataset.xlsx` not found or failed to load.")

