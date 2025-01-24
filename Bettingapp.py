import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook

# # Title and description
# st.title("Betting App")
# st.write("Welcome to the Betting App. Upload your fixture data or input manually to get started.")

# Initialize session state
if "fixtures" not in st.session_state:
    st.session_state.fixtures = pd.DataFrame()
if "primary_predictions" not in st.session_state:
    st.session_state.primary_predictions = {}
if "all_slips" not in st.session_state:
    st.session_state.all_slips = []
if "performance_data" not in st.session_state:
    st.session_state.performance_data = pd.DataFrame(
        columns=["Slip ID", "Type", "Status", "Total Odds", "Risk Score"]
    )

# Sidebar: Persistent across pages
with st.sidebar:
    st.header("Input Parameters")
    
    # File Upload or Manual Input
    upload_option = st.radio("Fixture Input Method", ["Upload CSV", "Manual Input"])
    
    if upload_option == "Upload CSV":
        uploaded_file = st.file_uploader("Upload Fixture Data (CSV)", type=["csv"])
        if uploaded_file:
            st.session_state.fixtures = pd.read_csv(uploaded_file)
    else:
        st.write("Manually Input Fixtures")
        col1, col2 = st.columns(2)
        with col1:
            home_team = st.text_input("Home Team")
        with col2:
            away_team = st.text_input("Away Team")
        col3, col4, col5 = st.columns(3)
        with col3:
            w1_odds = st.number_input("W1 Odds", min_value=1.0, step=0.1)
        with col4:
            x_odds = st.number_input("X Odds", min_value=1.0, step=0.1)
        with col5:
            w2_odds = st.number_input("W2 Odds", min_value=1.0, step=0.1)
        btts_yes_odds = st.number_input("BTTS Yes Odds", min_value=1.0, step=0.1)
        btts_no_odds = st.number_input("BTTS No Odds", min_value=1.0, step=0.1)
        category = st.selectbox("Category", ["Favorite", "Moderate", "Underdog"])
        
        if st.button("Add Fixture"):
            new_fixture = pd.DataFrame([{
                "Fixture ID": len(st.session_state.fixtures) + 1,
                "Home Team": home_team,
                "Away Team": away_team,
                "W1 Odds": w1_odds,
                "X Odds": x_odds,
                "W2 Odds": w2_odds,
                "BTTS Yes Odds": btts_yes_odds,
                "BTTS No Odds": btts_no_odds,
                "Category": category
            }])
            st.session_state.fixtures = pd.concat([st.session_state.fixtures, new_fixture], ignore_index=True)
            st.success("Fixture added!")

    # Display current fixtures
    if not st.session_state.fixtures.empty:
        st.write("Current Fixtures:")
        st.write(st.session_state.fixtures)

# Page 1: Input & Slip Generation
def input_page():
    st.header("Input & Slip Generation")
    
    if st.session_state.fixtures.empty:
        st.warning("Please upload a CSV or manually input fixtures.")
        return
    
    # Define bet_types based on the fixtures DataFrame
    bet_types = [col.replace(" Odds", "") for col in st.session_state.fixtures.columns if " Odds" in col]
    
    # Let users select fixtures and make predictions
    selected_fixtures = st.multiselect(
        "Select Fixtures", 
        st.session_state.fixtures["Fixture ID"].tolist(), 
        default=st.session_state.fixtures["Fixture ID"].tolist()[:4]
    )
    
    for fid in selected_fixtures:
        fixture = st.session_state.fixtures[st.session_state.fixtures["Fixture ID"] == fid].iloc[0]
        st.subheader(f"Fixture {fid}: {fixture['Home Team']} vs {fixture['Away Team']}")
        bet = st.selectbox(
            "Choose Bet Type", 
            [col.replace(" Odds", "") for col in st.session_state.fixtures.columns if " Odds" in col],
            key=f"bet_{fid}"
        )
        st.session_state.primary_predictions[fid] = {
            "Fixture ID": fid,
            "Home Team": fixture["Home Team"],
            "Away Team": fixture["Away Team"],
            "Bet Type": bet,
            "Odds": fixture[f"{bet} Odds"],
            "Risk Level": "High" if fixture["Category"] == "Underdog" else "Low"
        }
    
    # Generate slips
    num_slips = st.number_input("Number of Primary Slips", min_value=1, max_value=20, value=3)
    num_variants = st.number_input("Variants per Slip", min_value=1, max_value=5, value=2)
    
    if st.button("Generate Slips"):
        # Create primary slip
        primary_slip = pd.DataFrame(st.session_state.primary_predictions.values())
        st.session_state.all_slips = [{"Type": "Primary", "Slip": primary_slip}]
        
        # Generate variants
        for i in range(num_variants):
            variant = primary_slip.copy()
            row_to_change = np.random.randint(0, len(variant))
            fid = variant.iloc[row_to_change]["Fixture ID"]
            current_bet = variant.iloc[row_to_change]["Bet Type"]
            possible_bets = [bt for bt in bet_types if bt != current_bet]
            new_bet = np.random.choice(possible_bets)
            variant.at[row_to_change, "Bet Type"] = new_bet
            variant.at[row_to_change, "Odds"] = st.session_state.fixtures[st.session_state.fixtures["Fixture ID"] == fid][f"{new_bet} Odds"].values[0]
            st.session_state.all_slips.append({"Type": f"Variant {i+1}", "Slip": variant})
        
        st.success("Slips generated! Navigate to the Performance page to validate results.")

# Page 2: Performance Tracking
def performance_page():
    st.header("Performance Tracking")
    
    if not st.session_state.all_slips:
        st.warning("No slips generated yet. Go to the Input page to generate slips.")
        return
    
    for slip in st.session_state.all_slips:
        st.subheader(slip["Type"])
        st.dataframe(slip["Slip"])
        
        # Let users mark slips as won/lost
        status = st.selectbox(
            f"Status for {slip['Type']}", 
            ["Won", "Lost", "Pending"], 
            key=f"status_{slip['Type']}"
        )
        
        # Calculate metrics
        total_odds = slip["Slip"]["Odds"].prod()
        risk_score = (slip["Slip"]["Risk Level"] == "High").sum()
        
        # Add performance data using pd.concat()
        new_row = pd.DataFrame([{
            "Slip ID": slip["Type"],
            "Type": slip["Type"],
            "Status": status,
            "Total Odds": total_odds,
            "Risk Score": risk_score
        }])
        st.session_state.performance_data = pd.concat(
            [st.session_state.performance_data, new_row], 
            ignore_index=True
        )
    
    st.write("Performance Data:")
    st.write(st.session_state.performance_data)

# Page 3: Analytics Dashboard
def analytics_page():
    st.header("Analytics Dashboard")
    
    if st.session_state.performance_data.empty:
        st.warning("No performance data yet. Validate slips on the Performance page.")
        return
    
    # Win Rate
    win_rate = (st.session_state.performance_data["Status"] == "Won").mean()
    st.metric("Win Rate", f"{win_rate*100:.1f}%")
    
    # Risk-Reward Scatter Plot
    fig, ax = plt.subplots()
    ax.scatter(
        st.session_state.performance_data["Total Odds"], 
        st.session_state.performance_data["Risk Score"], 
        c=np.where(st.session_state.performance_data["Status"] == "Won", "green", "red")
    )
    ax.set_xlabel("Total Odds")
    ax.set_ylabel("Risk Score")
    st.pyplot(fig)

# Main App Logic
page = st.sidebar.selectbox("Navigate", ["Input", "Performance", "Analytics"])

if page == "Input":
    input_page()
elif page == "Performance":
    performance_page()
elif page == "Analytics":
    analytics_page()

# Custom CSS for styling
st.markdown("""
    <style>
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .stButton>button {
        color: white;
        background-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)