import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------- PATHS & DATA LOADING ----------------------

BASE_DIR = Path(__file__).resolve().parent


def _safe_read_csv(filename: str):
    path = BASE_DIR / filename
    if path.exists():
        return pd.read_csv(path)
    return None


def _safe_read_excel(filename: str):
    path = BASE_DIR / filename
    if path.exists():
        return pd.read_excel(path)
    return None


def load_main_datasets():
    """
    Loads all main datasets from the SAME folder as this file.

    Expected files:
      - SKU_Demand_Profile.csv
      - SKU_Clusters.csv
      - SKU_Associations.csv
      - Warehouse Challenge Dataset.xlsx
    """
    data = {}
    data["demand"] = _safe_read_csv("SKU_Demand_Profile.csv")
    data["clusters"] = _safe_read_csv("SKU_Clusters.csv")
    data["associations"] = _safe_read_csv("SKU_Associations.csv")
    data["warehouse_raw"] = _safe_read_excel("Warehouse Challenge Dataset.xlsx")
    return data


# ---------------------- STREAMLIT APP LAYOUT ----------------------

st.set_page_config(
    page_title="Warehouse Activity Profiling Simulator",
    layout="wide"
)

# ---------- SPLASH SCREEN STATE ----------
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if not st.session_state.splash_done:
    st.markdown(
        """
        <div style="
            width:100%;
            height:100%;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            font-family:sans-serif;
            padding-top:80px;
        ">
            <div style="font-size:28px;font-weight:700;margin-bottom:4px;">
                American University of Sharjah
            </div>
            <div style="font-size:20px;margin-bottom:2px;">
                Industrial Engineering Department
            </div>
            <div style="font-size:18px;margin-bottom:32px;">
                Warehouse Activity Profiling Simulator
            </div>
            <div style="font-size:14px;color:#555;">
                Click the button below to enter the dashboard.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Enter Simulator"):
        st.session_state.splash_done = True
        st.experimental_rerun()

else:
    # ---------------- MAIN DASHBOARD ----------------
    st.title("📦 Warehouse Activity Profiling Simulator")

    st.write(
        """
        Welcome to the **Warehouse Activity Profiling Simulator**.

        Use the tabs below to explore:
        - Analytical visualizations of demand, clusters, and associations
        - A basic simulation panel
        - Reporting and raw dataset views
        """
    )

    # Load data once for all tabs
    data = load_main_datasets()
    demand_df = data.get("demand")
    clusters_df = data.get("clusters")
    assoc_df = data.get("associations")
    raw_df = data.get("warehouse_raw")

    tab1, tab2, tab3 = st.tabs(
        [
            "Analytical Visualization Layer",
            "Optimization & Simulation Layer",
            "Reporting Layer",
        ]
    )

    # ---------- TAB 1: ANALYTICAL VISUALIZATION ----------
    with tab1:
        st.subheader("Demand, Clustering, and Association Mining")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📈 SKU Demand Profile")
            if demand_df is not None:
                st.dataframe(demand_df.head())
            else:
                st.warning("`SKU_Demand_Profile.csv` not found in the app folder.")

            st.markdown("### 🧩 SKU Clusters")
            if clusters_df is not None:
                st.dataframe(clusters_df.head())
            else:
                st.info("`SKU_Clusters.csv` not found in the app folder.")

        with col2:
            st.markdown("### 🔗 SKU Associations")
            if assoc_df is not None:
                st.dataframe(assoc_df.head())
            else:
                st.info("`SKU_Associations.csv` not found in the app folder.")

    # ---------- TAB 2: OPTIMIZATION & SIMULATION ----------
    with tab2:
        st.subheader("Simulation Panel")

        st.markdown(
            """
            Here you will integrate your **slotting optimization** and **simulation** logic.

            For now, this tab:
            - Shows how you could add controls (e.g., # of pickers, policy options)
            - Uses the loaded datasets for interactive experiments
            """
        )

        st.sidebar.header("Simulation Controls")
        num_pickers = st.sidebar.slider("Number of pickers", min_value=1, max_value=20, value=5)
        policy = st.sidebar.selectbox(
            "Storage policy",
            ["Dedicated storage", "Random storage", "Class-based storage"]
        )

        st.write(f"**Selected number of pickers:** {num_pickers}")
        st.write(f"**Selected storage policy:** {policy}")

        if demand_df is not None:
            st.markdown("#### Example: Top 10 SKUs by demand")
            if "SKU" in demand_df.columns and "Daily_Demand" in demand_df.columns:
                top10 = demand_df.sort_values("Daily_Demand", ascending=False).head(10)
                st.dataframe(top10)
            else:
                st.info("Demand dataset loaded, but columns `SKU` and `Daily_Demand` were not found.")
        else:
            st.info("Demand data is not loaded, so simulation examples are limited.")

    # ---------- TAB 3: REPORTING LAYER ----------
    with tab3:
        st.subheader("Reporting & Raw Data View")

        st.markdown(
            """
            This layer is intended for:
            - Management-level KPIs
            - Summary statistics
            - Exportable tables
            """
        )

        if raw_df is not None:
            st.markdown("### 🧾 Warehouse Challenge Dataset (first 50 rows)")
            st.dataframe(raw_df.head(50))
            st.markdown(f"**Total rows in dataset:** {len(raw_df)}")
        else:
            st.info("`Warehouse Challe

