import time
import streamlit as st

st.set_page_config(
    page_title="Warehouse Activity Profiling Simulator",
    layout="wide"
)

# -------------- SPLASH SCREEN CONTROL --------------
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
            padding-top:80px;
            font-family:sans-serif;
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
            <span style="font-size:14px;color:#555;">
                Click below to load the dashboard
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("Enter Simulator"):
        st.session_state.splash_done = True
        st.experimental_rerun()

else:
    # ---------------- MAIN HOME PAGE ----------------
    st.title("📦 Warehouse Activity Profiling Simulator")

    st.write(
        """
        Welcome to the **Warehouse Activity Profiling Simulator**.

        Use the navigation sidebar to access:
        - **Simulation Panel** (pages/simulation_panel.py)
        - Other modules you will develop later
        """
    )

