import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook
from backend.database import init_db, save_fixtures_to_db, get_fixtures_from_db, save_slips_to_db, get_slips_from_db, update_slip_status


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
# Initialize the database
init_db()

# Navigation Menu at the Top
st.sidebar.write("Navigation")
page = st.sidebar.radio("Go to", ["Fixture Prediction", "Bet Slips", "Bet Performance"], key="navigation_radio")

# Sidebar: Persistent across pages
with st.sidebar:
    st.header("Input Parameters")
    
# Sidebar: Persistent across pages
with st.sidebar:
    st.header("Prediction Sessions")
    
    # Create new prediction session
    new_session_name = st.text_input("New Session Name")
    if st.button("Create New Prediction"):
        if new_session_name:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            session_id = create_prediction_session(new_session_name, timestamp)
            st.session_state.current_session = session_id
            st.success(f"Created session: {new_session_name}")
    
    # Load existing sessions
    sessions = get_prediction_sessions()
    if sessions:
        selected_session = st.selectbox(
            "Select Session",
            [f"{s['name']} ({s['created_at']})" for s in sessions]
        )
        st.session_state.current_session = sessions[
            [s['name'] for s in sessions].index(selected_session.split(' (')[0])
        ]['prediction_id']
    
    st.header("Input Parameters")
    
    # File Upload or Manual Input
    upload_option = st.radio("Fixture Input Method", ["Upload CSV", "Manual Input"], key="upload_option_radio")
    
    if upload_option == "Upload CSV":
        uploaded_file = st.file_uploader("Upload Fixture Data (CSV)", type=["csv"], key="file_uploader")
        if uploaded_file:
            st.session_state.fixtures = pd.read_csv(uploaded_file)
            save_fixtures_to_db(st.session_state.fixtures)
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
            save_fixtures_to_db(st.session_state.fixtures)
            st.success("Fixture added!")

# Page 1: Fixture Prediction
def fixture_prediction_page():
    st.header("Fixture Prediction")
    st.session_state.fixtures = get_fixtures_from_db()

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
        
        # Save slips to the database
        save_slips_to_db(st.session_state.all_slips)
        st.success("Slips generated and saved! Navigate to the Bet Slips page to validate results.")
        if st.button("Go to Bet Slips"):
            page = "Bet Slips"

# Page 2: Bet Slips
def bet_slips_page():
    st.header("Bet Slips")
    if 'current_session' not in st.session_state:
        st.warning("Please create or select a prediction session first")
        return
    
    slips = get_slips_from_db(st.session_state.current_session)
    
    if slips.empty:
        st.warning("No slips generated yet. Go to the Fixture Prediction page to generate slips.")
        return
    
    for slip in slips.itertuples():
        if "Primary" in slip.slip_type:
            # Display primary slip with green header
            st.markdown(
                f"<h3 style='color: #2ecc71;'>{slip.slip_name} ({slip.slip_type})</h3>", 
                unsafe_allow_html=True
            )
            col1, col2 = st.columns([4, 1])
            with col1:
                st.dataframe(pd.DataFrame({
                    'Fixture': [slip.fixture_id],
                    'Bet Type': [slip.bet_type],
                    'Odds': [slip.odds],
                    'Risk Level': [slip.risk_level]
                }))
            with col2:
                new_status = st.selectbox(
                    "Status",
                    ["Won", "Lost", "Pending"],
                    index=["Won", "Lost", "Pending"].index(slip.status),
                    key=f"status_{slip.slip_id}"
                )
                if new_status != slip.status:
                    update_slip_status(slip.slip_id, new_status)
                    st.experimental_rerun()
        
        elif "Variant" in slip.slip_type:
            # Display variant with gray header in an expander
            with st.expander(f"🔽 {slip.slip_name} ({slip.slip_type})"):
                st.markdown(
                    f"<h4 style='color: #95a5a6;'>{slip.slip_name} ({slip.slip_type})</h4>", 
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.dataframe(pd.DataFrame({
                        'Fixture': [slip.fixture_id],
                        'Bet Type': [slip.bet_type],
                        'Odds': [slip.odds],
                        'Risk Level': [slip.risk_level]
                    }))
                with col2:
                    new_status = st.selectbox(
                        "Status",
                        ["Won", "Lost", "Pending"],
                        index=["Won", "Lost", "Pending"].index(slip.status),
                        key=f"status_{slip.slip_id}"
                    )
                    if new_status != slip.status:
                        update_slip_status(slip.slip_id, new_status)
                        st.experimental_rerun()

# Page 3: Bet Performance
def bet_performance_page():
    st.header("Bet Performance")
    if 'current_session' not in st.session_state:
        st.warning("Please create or select a prediction session first")
        return
    
    performance_data = calculate_performance(st.session_state.current_session)
    
    # Display Key Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Slips", len(performance_data))
    with col2:
        win_rate = performance_data['status'].eq('Won').mean()
        st.metric("Win Rate", f"{win_rate*100:.1f}%")
    with col3:
        avg_odds = performance_data['total_odds'].mean()
        st.metric("Average Odds", f"{avg_odds:.2f}")
    
    # Detailed Performance Table
    st.subheader("Performance Details")
    st.dataframe(performance_data)
    
    # Visualization
    st.subheader("Risk-Reward Analysis")
    fig = px.scatter(performance_data, 
                    x='total_odds', 
                    y='risk_score',
                    color='status',
                    hover_data=['slip_name'])
    st.plotly_chart(fig)

# Main App Logic
if page == "Fixture Prediction":
    fixture_prediction_page()
elif page == "Bet Slips":
    bet_slips_page()
elif page == "Bet Performance":
    bet_performance_page()