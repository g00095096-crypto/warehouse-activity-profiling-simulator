import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from slotting import run_slotting  # your heuristic


# ---------------------- PATHS ----------------------

BASE_DIR = Path(__file__).resolve().parent


# ---------------------- DATA HELPERS ----------------------

@st.cache_data
def load_analysis_data():
    """Load Step 2 CSV outputs (demand, clusters, associations) if present."""
    demand = clusters = assoc = None

    paths = {
        "demand": BASE_DIR / "SKU_Demand_Profile.csv",
        "clusters": BASE_DIR / "SKU_Clusters.csv",
        "assoc": BASE_DIR / "SKU_Associations.csv",
    }

    if paths["demand"].exists():
        demand = pd.read_csv(paths["demand"])
    if paths["clusters"].exists():
        clusters = pd.read_csv(paths["clusters"])
    if paths["assoc"].exists():
        assoc = pd.read_csv(paths["assoc"])

    # light standardization for demand table
    if demand is not None:
        demand = demand.rename(
            columns={
                "sku_id": "SKU_ID",
                "SKU Id": "SKU_ID",
                "SKU": "SKU_ID",
                "Weekly_Demand_units": "Weekly_Demand_units",
                "weekly_demand_units": "Weekly_Demand_units",
                "ABC": "ABC_Class",
            }
        )

    return {"demand": demand, "clusters": clusters, "associations": assoc}


def _find_sheet(xl: pd.ExcelFile, candidates):
    """Return first sheet name found in candidates (case-insensitive), else None."""
    lower_map = {s.lower(): s for s in xl.sheet_names}
    for name in candidates:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


@st.cache_data
def load_slotting_inputs_from_bytes(xls_bytes: bytes):
    """
    Load SKU, Lines, Zones tables from uploaded (or local) Excel file.
    Accepts multiple possible sheet name variants.
    """
    xl = pd.ExcelFile(io.BytesIO(xls_bytes))

    sku_sheet = _find_sheet(xl, ["SKU_Master", "SKUs"])
    lines_sheet = _find_sheet(xl, ["Lines", "OrderLines"])
    zone_sheet = _find_sheet(xl, ["Storage_Zone", "Storage_Zones", "Zones"])

    if sku_sheet is None or lines_sheet is None or zone_sheet is None:
        raise ValueError(
            f"Could not find required sheets. Found sheets: {xl.sheet_names}. "
            "Expect something like SKU_Master, Lines, Storage_Zone(s)."
        )

    sku_raw = xl.parse(sheet_name=sku_sheet)
    lines_df = xl.parse(sheet_name=lines_sheet)
    zone_raw = xl.parse(sheet_name=zone_sheet)

    # basic ID consistency checks
    problems = []

    if "Order_ID" in lines_df.columns and "Order_ID" in xl.parse(
        sheet_name=_find_sheet(xl, ["Orders", "orders"]) or lines_sheet
    ).columns:
        orders = xl.parse(sheet_name=_find_sheet(xl, ["Orders", "orders"]) or lines_sheet)
        missing_orders = set(lines_df["Order_ID"]) - set(orders["Order_ID"])
        if missing_orders:
            problems.append(f"- {len(missing_orders)} order IDs in Lines not in Orders")

    if "SKU_ID" in lines_df.columns and "SKU_ID" in sku_raw.columns:
        missing_skus = set(lines_df["SKU_ID"]) - set(sku_raw["SKU_ID"])
        if missing_skus:
            problems.append(f"- {len(missing_skus)} SKUs in Lines not in SKU_Master")

    return sku_raw, lines_df, zone_raw, problems


def load_challenge_excel(uploaded_file):
    """
    Wrapper: use uploaded file if provided, else fall back to local
    Warehouse Challenge Dataset.xlsx in the repo (for your professor).
    Returns bytes or raises FileNotFoundError.
    """
    if uploaded_file is not None:
        return uploaded_file.read()

    local_path = BASE_DIR / "Warehouse Challenge Dataset.xlsx"
    if not local_path.exists():
        raise FileNotFoundError(
            "No Excel file uploaded and local 'Warehouse Challenge Dataset.xlsx' not found."
        )
    return local_path.read_bytes()


# ---------------------- STREAMLIT CONFIG ----------------------

st.set_page_config(
    page_title="Warehouse Activity Profiling Simulator",
    layout="wide"
)

if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if "slotting_results" not in st.session_state:
    st.session_state.slotting_results = None

if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}  # name -> dict of results


# ---------------------- SPLASH SCREEN ----------------------

if not st.session_state.splash_done:
    import time

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
            <div style="font-size:18px;margin-bottom:8px;">
                Warehouse Activity Profiling Simulator
            </div>
            <div style="font-size:16px;margin-bottom:4px;">
                Developed for INE 494-5 / Senior Design Project
            </div>
            <div style="font-size:14px;color:#555;">
                Loading Slotting Simulator... Please wait.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(5)
    st.session_state.splash_done = True


# ---------------------- MAIN APP ----------------------

st.title("📦 Warehouse Activity Profiling Simulator")

st.write(
    """
    This simulator implements the course project specification with three layers:

    1. **Analytical Visualization Layer** – demand, clustering, association mining  
    2. **Optimization & Simulation Layer** – heuristic slotting minimizing Σ λⱼ · dₖ  
    3. **Reporting Layer** – KPIs, zone utilization, and exports
    """
)

# ---- Dataset upload (Excel) ----
st.sidebar.header("Dataset Import")

uploaded_excel = st.sidebar.file_uploader(
    "Upload Warehouse Challenge Excel (.xlsx)",
    type=["xlsx"],
    help="Must contain SKU_Master, Lines, Storage_Zone(s), and optionally Orders."
)

excel_bytes = None
try:
    excel_bytes = load_challenge_excel(uploaded_excel)
    excel_status = "Using uploaded Excel file." if uploaded_excel else \
                   "Using default 'Warehouse Challenge Dataset.xlsx' from the app folder."
    st.sidebar.success(excel_status)
except FileNotFoundError as e:
    st.sidebar.error(str(e))

# Load Step 2 CSVs (if present)
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

    # Demand + ABC visuals
    with col1:
        st.markdown("### 📈 SKU Demand Profile (Table)")
        if demand_df is not None:
            st.dataframe(demand_df.head(50), use_container_width=True)

            # try to plot demand by ABC or top SKUs
            demand_plot_df = demand_df.copy()
            qty_col = None
            for c in ["Weekly_Demand_units", "Weekly_Demand", "Demand"]:
                if c in demand_plot_df.columns:
                    qty_col = c
                    break

            if qty_col is not None:
                st.markdown("### 📊 Demand by ABC Class")
                if "ABC_Class" in demand_plot_df.columns:
                    abc_summary = (
                        demand_plot_df.groupby("ABC_Class")[qty_col]
                        .sum()
                        .reset_index()
                        .sort_values(qty_col, ascending=False)
                    )
                    fig_abc = px.bar(
                        abc_summary,
                        x="ABC_Class",
                        y=qty_col,
                        title="Total weekly demand by ABC class",
                    )
                    st.plotly_chart(fig_abc, use_container_width=True)

                st.markdown("### 🔟 Top 10 SKUs by demand")
                sku_col = "SKU_ID" if "SKU_ID" in demand_plot_df.columns else demand_plot_df.columns[0]
                top10 = (
                    demand_plot_df[[sku_col, qty_col]]
                    .sort_values(qty_col, ascending=False)
                    .head(10)
                )
                fig_top = px.bar(
                    top10,
                    x=sku_col,
                    y=qty_col,
                    title="Top 10 SKUs by weekly demand",
                )
                st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.warning("`SKU_Demand_Profile.csv` not found.")

    # Clusters + associations
    with col2:
        st.markdown("### 🧩 SKU Clusters (Table)")
        if clusters_df is not None:
            st.dataframe(clusters_df.head(50), use_container_width=True)

            # simple 2D scatter if we can
            numeric_cols = clusters_df.select_dtypes(include="number").columns.tolist()
            if len(numeric_cols) >= 2 and "Cluster" in clusters_df.columns:
                st.markdown("### Scatter of clusters")
                fig_cl = px.scatter(
                    clusters_df,
                    x=numeric_cols[0],
                    y=numeric_cols[1],
                    color="Cluster",
                    title="Cluster visualization (first two numeric features)",
                )
                st.plotly_chart(fig_cl, use_container_width=True)
        else:
            st.info("`SKU_Clusters.csv` not found.")

        st.markdown("### 🔗 Association Rules")
        if assoc_df is not None:
            st.dataframe(assoc_df.head(50), use_container_width=True)
        else:
            st.info("`SKU_Associations.csv` not found.")

# ---------- TAB 2: OPTIMIZATION & SIMULATION ----------
with tab2:
    st.subheader("Slotting Optimization & What-If Simulation")

    st.markdown(
        """
        The heuristic assigns SKUs in order of descending weekly demand λⱼ to the closest
        compatible zone (by distance) with remaining capacity, approximating:

        \\[
        \\min \\sum_j \\lambda_j \\, d_k
        \\]

        subject to capacity and storage-type compatibility.
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("What-If Controls")

    demand_multiplier = st.sidebar.slider(
        "Demand multiplier (λⱼ)",
        min_value=0.5,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="Scale weekly demand up/down to simulate different demand levels.",
    )

    capacity_multiplier = st.sidebar.slider(
        "Capacity multiplier (all zones)",
        min_value=0.5,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="Scale zone capacities to simulate layout changes.",
    )

    run_slotting_button = st.sidebar.button("Run slotting heuristic")

    if excel_bytes is None:
        st.warning("Upload or provide the Warehouse Challenge Excel file in the sidebar.")
    else:
        if run_slotting_button:
            try:
                sku_raw, lines_df, zone_raw, problems = load_slotting_inputs_from_bytes(excel_bytes)

                # apply what-if multipliers
                if "Weekly_Demand_units" in sku_raw.columns:
                    sku_raw = sku_raw.copy()
                    sku_raw["Weekly_Demand_units"] *= demand_multiplier

                if "Capacity" in zone_raw.columns:
                    zone_raw = zone_raw.copy()
                    zone_raw["Capacity"] = zone_raw["Capacity"] * capacity_multiplier

                assignment_df, zone_util_df, total_travel_cost, zone_demand, heat_pivot = run_slotting(
                    sku_raw, lines_df, zone_raw
                )

                st.session_state.slotting_results = {
                    "assignment_df": assignment_df,
                    "zone_util_df": zone_util_df,
                    "total_travel_cost": total_travel_cost,
                    "zone_demand": zone_demand,
                    "heat_pivot": heat_pivot,
                    "demand_multiplier": demand_multiplier,
                    "capacity_multiplier": capacity_multiplier,
                }

                if problems:
                    st.warning(
                        "Data consistency issues detected:\n" + "\n".join(problems)
                    )
                st.success("Slotting run completed.")

            except Exception as e:
                st.error(f"Error while running slotting: {e}")

        results = st.session_state.slotting_results

        if results is None:
            st.info("Adjust the what-if sliders and click **Run slotting heuristic** to see results.")
        else:
            assignment_df = results["assignment_df"]
            zone_util_df = results["zone_util_df"]
            total_travel_cost = results["total_travel_cost"]
            zone_demand = results["zone_demand"]
            heat_pivot = results["heat_pivot"]

            st.markdown(
                f"**Total expected travel cost (Σ λⱼ · dₖ)**: `{total_travel_cost:,.2f}`  "
                f"(λ multiplier = {results['demand_multiplier']}, "
                f"capacity multiplier = {results['capacity_multiplier']})"
            )

            st.markdown("### Assigned zones per SKU (first 30 rows)")
            st.dataframe(assignment_df.head(30), use_container_width=True)

            st.markdown("### Zone utilization")
            st.dataframe(zone_util_df, use_container_width=True)

            # Charts
            col_z1, col_z2 = st.columns(2)

            with col_z1:
                st.markdown("#### Demand per zone (Σ λⱼ)")
                if not zone_demand.empty:
                    fig_bar = px.bar(
                        zone_demand,
                        x="Assigned_Zone",
                        y="Total_Lambda_in_Zone",
                        color="Storage_Type",
                        title="Total weekly demand by zone",
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No zone demand data to plot.")

            with col_z2:
                st.markdown("#### Heatmap: Storage_Type × ABC_Class (Σ λⱼ)")
                if not heat_pivot.empty:
                    fig_heat = px.imshow(
                        heat_pivot,
                        labels=dict(x="ABC_Class", y="Storage_Type", color="Σ λⱼ"),
                        title="Demand concentration by Storage Type and ABC Class",
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
                else:
                    st.info("No heatmap data to display.")

            # Scenario saving
            st.markdown("### Save Scenario")
            scenario_name = st.text_input(
                "Scenario name (e.g., Baseline, High Demand, Reduced Capacity)",
                value="Baseline",
            )
            if st.button("Save current scenario"):
                st.session_state.scenarios[scenario_name] = results
                st.success(f"Saved scenario '{scenario_name}'.")

            if st.session_state.scenarios:
                st.markdown("### Scenario Comparison (travel cost)")
                comp_rows = []
                for name, res in st.session_state.scenarios.items():
                    zutil = res["zone_util_df"]
                    avg_util = zutil["Utilization_pct"].mean() if "Utilization_pct" in zutil.columns else None
                    comp_rows.append(
                        {
                            "Scenario": name,
                            "Travel_Cost": res["total_travel_cost"],
                            "Avg_Utilization_pct": avg_util,
                            "λ_multiplier": res.get("demand_multiplier", 1.0),
                            "Cap_multiplier": res.get("capacity_multiplier", 1.0),
                        }
                    )
                comp_df = pd.DataFrame(comp_rows)
                st.dataframe(comp_df, use_container_width=True)

# ---------- TAB 3: REPORTING LAYER ----------
with tab3:
    st.subheader("Reporting & Summary KPIs")

    results = st.session_state.slotting_results

    if results is None:
        st.info("Run the slotting heuristic in the **Optimization & Simulation** tab to see KPIs here.")
    else:
        assignment_df = results["assignment_df"]
        zone_util_df = results["zone_util_df"]
        total_travel_cost = results["total_travel_cost"]
        zone_demand = results["zone_demand"]
        heat_pivot = results["heat_pivot"]

        st.markdown("### Key KPI")
        st.metric(
            label="Total expected travel cost (Σ λⱼ · dₖ)",
            value=f"{total_travel_cost:,.2f}",
        )

        if "Utilization_pct" in zone_util_df.columns:
            avg_util = zone_util_df["Utilization_pct"].mean()
            st.metric(
                label="Average zone utilization (%)",
                value=f"{avg_util:.1f}",
            )

        st.markdown("### Zone utilization overview")
        cols_to_show = [c for c in [
            "Zone_ID",
            "Storage_Type",
            "Capacity_m3",
            "Used_Volume_m3",
            "Utilization_pct",
            "Distance_m",
        ] if c in zone_util_df.columns]
        st.dataframe(zone_util_df[cols_to_show], use_container_width=True)

        # Download results as Excel
        st.markdown("### Download Results")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            assignment_df.to_excel(writer, sheet_name="SKU_Assignments", index=False)
            zone_util_df.to_excel(writer, sheet_name="Zone_Utilization", index=False)
            zone_demand.to_excel(writer, sheet_name="Category_Level_KPIs", index=False)

            summary = pd.DataFrame(
                [
                    {
                        "Total_Travel_Cost": total_travel_cost,
                        "Avg_Utilization_pct": zone_util_df["Utilization_pct"].mean()
                        if "Utilization_pct" in zone_util_df.columns
                        else None,
                        "Num_Zones": zone_util_df.shape[0],
                        "Num_SKUs": assignment_df["SKU_ID"].nunique()
                        if "SKU_ID" in assignment_df.columns
                        else assignment_df.shape[0],
                    }
                ]
            )
            summary.to_excel(writer, sheet_name="Summary_Report", index=False)

        st.download_button(
            label="Download Excel report",
            data=buffer.getvalue(),
            file_name="Warehouse_Slotting_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown("### Raw challenge dataset preview")
    try:
        if excel_bytes is not None:
            xl = pd.ExcelFile(io.BytesIO(excel_bytes))
            first_sheet = xl.sheet_names[0]
            raw_preview = xl.parse(sheet_name=first_sheet, nrows=50)
            st.dataframe(raw_preview, use_container_width=True)
            st.caption(f"Preview: first 50 rows from sheet '{first_sheet}'")
        else:
            st.info("No Excel file available to preview.")
    except Exception as e:
        st.error(f"Could not load preview of challenge dataset: {e}")
