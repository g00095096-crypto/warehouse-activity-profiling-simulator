import streamlit as st
import pandas as pd
from pathlib import Path

from slotting import run_slotting

# ---------------------- PATHS & DATA LOADING ----------------------

BASE_DIR = Path(__file__).resolve().parent


@st.cache_data
def load_analysis_data():
    """
    Load the three analytical CSVs used in Step 2 (demand, clusters, associations).
    Files must sit in the SAME folder as this file:
      - SKU_Demand_Profile.csv
      - SKU_Clusters.csv
      - SKU_Associations.csv
    """
    demand = None
    clusters = None
    assoc = None

    demand_path = BASE_DIR / "SKU_Demand_Profile.csv"
    clusters_path = BASE_DIR / "SKU_Clusters.csv"
    assoc_path = BASE_DIR / "SKU_Associations.csv"

    if demand_path.exists():
        demand = pd.read_csv(demand_path)

    if clusters_path.exists():
        clusters = pd.read_csv(clusters_path)

    if assoc_path.exists():
        assoc = pd.read_csv(assoc_path)

    return {"demand": demand, "clusters": clusters, "associations": assoc}


@st.cache_data
def load_slotting_inputs():
    """
    Load the input tables needed by run_slotting() from the Excel challenge file.
    You can adjust sheet_name=... below to match your actual sheet names.
    """
    excel_path = BASE_DIR / "Warehouse Challenge Dataset.xlsx"
    if not excel_path.exists():
        raise FileNotFoundError("Warehouse Challenge Dataset.xlsx not found next to streamlit_app.py")

    # TODO: change these if your sheet names differ
    sku_raw = pd.read_excel(excel_path, sheet_name="SKUs")
    lines_df = pd.read_excel(excel_path, sheet_name="OrderLines")
    zone_raw = pd.read_excel(excel_path, sheet_name="Zones")

    return sku_raw, lines_df, zone_raw


# ---------------------- STREAMLIT APP CONFIG ----------------------

st.set_page_config(
    page_title="Warehouse Activity Profiling Simulator",
    layout="wide"
)

# ---------- SPLASH SCREEN STATE ----------
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if "slotting_results" not in st.session_state:
    st.session_state.slotting_results = None


# ---------------------- SPLASH OR MAIN ----------------------

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
        This app implements the **Warehouse Activity Profiling Simulator** with three layers,
        following the course project specification:

        1. Analytical Visualization Layer  
        2. Optimization & Simulation Layer (slotting heuristic min Σ λⱼ · dₖ)  
        3. Reporting Layer
        """
    )

    # Load analytical datasets once for all tabs
    datasets = load_analysis_data()
    demand_df = datasets["demand"]
    clusters_df = datasets["clusters"]
    assoc_df = datasets["associations"]

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
                st.dataframe(demand_df.head(50), use_container_width=True)
            else:
                st.warning("`SKU_Demand_Profile.csv` not found next to streamlit_app.py.")

            st.markdown("### 🧩 SKU Clusters")
            if clusters_df is not None:
                st.dataframe(clusters_df.head(50), use_container_width=True)
            else:
                st.info("`SKU_Clusters.csv` not found.")

        with col2:
            st.markdown("### 🔗 SKU Associations")
            if assoc_df is not None:
                st.dataframe(assoc_df.head(50), use_container_width=True)
            else:
                st.info("`SKU_Associations.csv` not found.")

            if demand_df is not None and "SKU_ID" in demand_df.columns:
                st.markdown("### Quick demand summary")
                st.write(f"Total SKUs: **{demand_df['SKU_ID'].nunique()}**")

    # ---------- TAB 2: OPTIMIZATION & SIMULATION ----------
    with tab2:
        st.subheader("Slotting Optimization & Simulation")

        st.markdown(
            """
            The heuristic implemented here assigns SKUs to zones in order of descending
            weekly demand λⱼ, to the closest compatible zone (by distance) with remaining
            capacity. This is aligned with minimizing the expected travel effort:

            \\[
            \\min \\sum_j \\lambda_j \\, d_k
            \\]

            subject to capacity and storage-type compatibility.
            """,
            unsafe_allow_html=True,
        )

        st.sidebar.header("Slotting Controls")

        run_button = st.sidebar.button("Run slotting heuristic")

        if run_button:
            try:
                sku_raw, lines_df, zone_raw = load_slotting_inputs()
                assignment_df, zone_util_df, total_travel_cost, zone_demand, heat_pivot = run_slotting(
                    sku_raw, lines_df, zone_raw
                )

                st.session_state.slotting_results = {
                    "assignment_df": assignment_df,
                    "zone_util_df": zone_util_df,
                    "total_travel_cost": total_travel_cost,
                    "zone_demand": zone_demand,
                    "heat_pivot": heat_pivot,
                }

                st.success("Slotting run completed successfully.")

            except Exception as e:
                st.error(f"Error while running slotting: {e}")

        results = st.session_state.slotting_results

        if results is None:
            st.info("Press **Run slotting heuristic** in the sidebar to execute the model.")
        else:
            assignment_df = results["assignment_df"]
            zone_util_df = results["zone_util_df"]
            total_travel_cost = results["total_travel_cost"]
            zone_demand = results["zone_demand"]
            heat_pivot = results["heat_pivot"]

            st.markdown(f"**Total expected travel cost (Σ λⱼ · dₖ)**: `{total_travel_cost:,.2f}`")

            st.markdown("### Assigned zones per SKU (first 30 rows)")
            st.dataframe(assignment_df.head(30), use_container_width=True)

            st.markdown("### Zone utilization")
            st.dataframe(zone_util_df, use_container_width=True)

            st.markdown("### Demand per zone (Σ λⱼ in each zone)")
            st.dataframe(zone_demand, use_container_width=True)

            st.markdown("### Heatmap pivot (Storage_Type × ABC_Class, Σ λⱼ)")
            st.dataframe(heat_pivot, use_container_width=True)

    # ---------- TAB 3: REPORTING LAYER ----------
    with tab3:
        st.subheader("Reporting & Summary KPIs")

        st.markdown(
            """
            This layer summarizes key performance indicators for management reporting:
            - Total expected travel cost under the current slotting
            - Zone utilization levels
            - Basic dataset overview
            """
        )

        results = st.session_state.slotting_results

        if results is None:
            st.info("Run the slotting heuristic in the **Optimization & Simulation** tab to see KPIs here.")
        else:
            total_travel_cost = results["total_travel_cost"]
            zone_util_df = results["zone_util_df"]

            st.markdown("### Key KPI")
            st.metric(
                label="Total expected travel cost (Σ λⱼ · dₖ)",
                value=f"{total_travel_cost:,.2f}",
            )

            st.markdown("### Zone utilization overview")
            st.dataframe(zone_util_df[[
                "Zone_ID",
                "Storage_Type",
                "Capacity_m3",
                "Used_Volume_m3",
                "Utilization_pct",
                "Distance_m",
            ]], use_container_width=True)

        st.markdown("### Raw challenge dataset preview")
        try:
            excel_path = BASE_DIR / "Warehouse Challenge Dataset.xlsx"
            if excel_path.exists():
                raw_df_preview = pd.read_excel(excel_path, nrows=50)
                st.dataframe(raw_df_preview, use_container_width=True)
                st.caption("First 50 rows from Warehouse Challenge Dataset.xlsx")
            else:
                st.info("`Warehouse Challenge Dataset.xlsx` not found next to streamlit_app.py.")
        except Exception as e:
            st.error(f"Could not load preview of challenge dataset: {e}")

