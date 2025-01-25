import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook

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

# Navigation Menu at the Top
st.sidebar.write("Navigation")
page = st.sidebar.radio("Go to", ["Fixture Prediction", "Bet Slips", "Bet Performance"])

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
        home_team = st.text_input("Home Team")
        away_team = st.text_input("Away Team")
        w1_odds = st.number_input("W1 Odds", min_value=1.0, step=0.1)
        x_odds = st.number_input("X Odds", min_value=1.0, step=0.1)
        w2_odds = st.number_input("W2 Odds", min_value=1.0, step=0.1)
        btts_yes_odds = st.number_input("BTTS Yes Odds", min_value=1.0, step=0.1)
        btts_no_odds = st.number_input("BTTS No Odds", min_value=1.0, step=0.1)
        category = st.selectbox("Category", ["Favorite", "Moderate", "Volatile"])
        
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

# Page 1: Fixture Prediction
def fixture_prediction_page():
    st.header("Fixture Prediction")
    
    if st.session_state.fixtures.empty:
        st.warning("Please upload a CSV or manually input fixtures.")
        return
    
    # Display current fixtures
    st.subheader("Current Fixtures")
    st.write(st.session_state.fixtures)
    
    # Bet Strategy Section
    st.header("Bet Strategy")
    num_slips = st.number_input("Number of Primary Slips", min_value=1, max_value=20, value=3)
    fixtures_per_slip = st.number_input("Fixtures per Slip", min_value=1, max_value=10, value=4)
    num_variants = st.number_input("Variants per Slip", min_value=1, max_value=5, value=2)
    
    # Define bet_types based on the fixtures DataFrame
    bet_types = [col.replace(" Odds", "") for col in st.session_state.fixtures.columns if " Odds" in col]
    
    # Let users select fixtures and make predictions
    selected_fixtures = st.multiselect(
        "Select Fixtures", 
        st.session_state.fixtures["Fixture ID"].tolist(), 
        default=st.session_state.fixtures["Fixture ID"].tolist()  # Allow selecting all fixtures
    )
    st.header("Make Predictions")
    for fid in selected_fixtures:
        fixture = st.session_state.fixtures[st.session_state.fixtures["Fixture ID"] == fid].iloc[0]
        st.subheader(f"Fixture {fid}: {fixture['Home Team']} vs {fixture['Away Team']}")
        bet = st.selectbox(
            "Choose Bet Type", 
            bet_types,  # Use the defined bet_types
            key=f"bet_{fid}"
        )
        st.session_state.primary_predictions[fid] = {
            "Fixture ID": fid,
            "Home Team": fixture["Home Team"],
            "Away Team": fixture["Away Team"],
            "Bet Type": bet,
            "Odds": fixture[f"{bet} Odds"],
            "Risk Level": "High" if fixture["Category"] == "Volatile" else "Low"
        }
    
    if st.button("Generate Slips"):
        st.session_state.all_slips = []
        all_fixtures = list(st.session_state.primary_predictions.values())
        
        for slip_id in range(num_slips):
            # Shuffle fixtures and select the first `fixtures_per_slip`
            np.random.shuffle(all_fixtures)
            selected_fixtures_for_slip = all_fixtures[:fixtures_per_slip]
            
            # Create primary slip
            primary_slip = pd.DataFrame(selected_fixtures_for_slip)
            st.session_state.all_slips.append({"Type": f"Primary {slip_id+1}", "Slip": primary_slip})
            
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
                st.session_state.all_slips.append({"Type": f"Variant {i+1} (Primary {slip_id+1})", "Slip": variant})
        
        st.success("Slips generated! Navigate to the Bet Slips page to validate results.")
        if st.button("Go to Bet Slips"):
            page = "Bet Slips"

# Page 2: Bet Slips
def bet_slips_page():
    st.header("Bet Slips")
    
    if not st.session_state.all_slips:
        st.warning("No slips generated yet. Go to the Fixture Prediction page to generate slips.")
        return
    
    for slip in st.session_state.all_slips:
        if "Primary" in slip["Type"]:
            # Display primary slip with green header
            st.markdown(
                f"<h3 style='color: #000000;'>{slip['Type']}</h3>", 
                unsafe_allow_html=True
            )
            col1, col2 = st.columns([4, 1])
            with col1:
                st.dataframe(
                    slip["Slip"].style.map(
                        lambda x: f"background-color: {'green' if x == 'Low' else 'yellow' if x == 'Medium' else 'red'}",
                        subset=["Risk Level"]
                    )
                )
            with col2:
                status = st.selectbox(
                    f"Status for {slip['Type']}", 
                    ["Won", "Lost", "Pending"], 
                    key=f"status_{slip['Type']}"
                )
        elif "Variant" in slip["Type"]:
            # Display variant with gray header in an expander
            with st.expander(f"🔽 {slip['Type']}"):
                st.markdown(
                    f"<h4 style='color: #95a5a6;'>{slip['Type']}</h4>", 
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.dataframe(
                        slip["Slip"].style.map(
                            lambda x: f"background-color: {'green' if x == 'Low' else 'yellow' if x == 'Medium' else 'red'}",
                            subset=["Risk Level"]
                        )
                    )
                with col2:
                    status = st.selectbox(
                        f"Status for {slip['Type']}", 
                        ["Won", "Lost", "Pending"], 
                        key=f"status_{slip['Type']}"
                    )

# Page 3: Bet Performance
def bet_performance_page():
    st.header("Bet Performance")
    
    if st.session_state.performance_data.empty:
        st.warning("No performance data yet. Validate slips on the Bet Slips page.")
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
if page == "Fixture Prediction":
    fixture_prediction_page()
elif page == "Bet Slips":
    bet_slips_page()
elif page == "Bet Performance":
    bet_performance_page()