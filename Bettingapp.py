import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from sklearn.linear_model import LogisticRegression
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook

# Initialize session state for performance tracking
if "performance_data" not in st.session_state:
    st.session_state.performance_data = pd.DataFrame(
        columns=["Slip ID", "Type", "Status", "Total Odds", "Risk Score"]
    )

# Title
st.title("Advanced Bet Slip Optimizer")

# Sidebar: File Upload
uploaded_file = st.sidebar.file_uploader("Upload Fixture Data (CSV)", type=["csv"])
if not uploaded_file:
    st.warning("Upload a CSV file.")
    st.stop()

fixtures = pd.read_csv(uploaded_file)
bet_types = [col.replace(" Odds", "") for col in fixtures.columns if " Odds" in col]

# Module 1: User Input & Prediction Interface
st.header("1. Select Fixtures & Predictions")
selected_fixtures = st.multiselect(
    "Select Fixtures", 
    fixtures["Fixture ID"].tolist(), 
    default=fixtures["Fixture ID"].tolist()[:4]
)
# Let users choose bet types for each selected fixture
primary_predictions = {}
for fid in selected_fixtures:
    fixture = fixtures[fixtures["Fixture ID"] == fid].iloc[0]
    st.subheader(f"Fixture {fid}: {fixture['Home Team']} vs {fixture['Away Team']}")
    bet = st.selectbox(
        "Choose Bet Type", 
        [col.replace(" Odds", "") for col in fixtures.columns if " Odds" in col],
        key=f"bet_{fid}"
    )
    primary_predictions[fid] = {
        "Fixture ID": fid,  # Added this line
        "Home Team": fixture["Home Team"],
        "Away Team": fixture["Away Team"],
        "Bet Type": bet,
        "Odds": fixture[f"{bet} Odds"],
        "Risk Level": "High" if fixture["Category"] == "Volatile" else "Low"
    }

# Module 2: Betslip Generator
st.header("2. Generate Slips")
num_variants = st.number_input("Variants per Slip", min_value=1, max_value=5, value=2)

if st.button("Generate Slips & Variants"):
    # Create primary slip from user selections
    primary_slip = pd.DataFrame(primary_predictions.values())
    all_slips = [{"Type": "Primary", "Slip": primary_slip}]

    # Generate variants by altering one bet type per slip
    for i in range(num_variants):
        variant = primary_slip.copy()
        row_to_change = np.random.randint(0, len(variant))
        fid = variant.iloc[row_to_change]["Fixture ID"]
        current_bet = variant.iloc[row_to_change]["Bet Type"]
        possible_bets = [bt for bt in bet_types if bt != current_bet]
        new_bet = np.random.choice(possible_bets)
        variant.at[row_to_change, "Bet Type"] = new_bet
        variant.at[row_to_change, "Odds"] = fixtures[fixtures["Fixture ID"] == fid][f"{new_bet} Odds"].values[0]
        all_slips.append({"Type": f"Variant {i+1}", "Slip": variant})

    # Store slips in session state
    st.session_state.all_slips = all_slips

    # Display slips
    st.subheader("Primary Slip")
    st.dataframe(primary_slip)

    st.subheader("Variant Slips")
    for slip in all_slips[1:]:
        st.write(slip["Type"])
        st.dataframe(slip["Slip"])

    # Module 3: Performance Tracking

# Add this after slip generation
if "all_slips" in st.session_state:
    st.header("3. Validate Results & Track Performance")
    performance_data = []

    for slip in st.session_state.all_slips:
        st.subheader(slip["Type"])
        st.dataframe(slip["Slip"])
        
        # Let users mark slips as won/lost
        status = st.selectbox(
            "Status (Won/Lost)", 
            ["Won", "Lost", "Pending"], 
            key=f"status_{slip['Type']}"
        )
        
        # Calculate metrics
        total_odds = slip["Slip"]["Odds"].prod()
        risk_score = (slip["Slip"]["Risk Level"] == "High").sum()
        performance_data.append({
            "Slip ID": slip["Type"],
            "Status": status,
            "Total Odds": total_odds,
            "Risk Score": risk_score
        })

    # Analytics Dashboard
    st.header("4. Analytics Dashboard")
    performance_df = pd.DataFrame(performance_data)
    
    # Win Rate
    win_rate = (performance_df["Status"] == "Won").mean()
    st.metric("Win Rate", f"{win_rate*100:.1f}%")
    
    # Risk-Reward Scatter Plot
    fig, ax = plt.subplots()
    ax.scatter(
        performance_df["Total Odds"], 
        performance_df["Risk Score"], 
        c=np.where(performance_df["Status"] == "Won", "green", "red")
    )
    ax.set_xlabel("Total Odds")
    ax.set_ylabel("Risk Score")
    st.pyplot(fig)

    # Module 5: Export System
 # Add this after the analytics section
st.header("4. Export Results")
if st.button("Export to Excel"):
    wb = Workbook()
    
    # Save slips
    for slip in st.session_state.all_slips:
        ws = wb.create_sheet(title=slip["Type"][:31])
        for r_idx, row in enumerate(dataframe_to_rows(slip["Slip"], index=False, header=True)):
            ws.append(row)
    
    # Save performance data
    ws = wb.create_sheet(title="Performance")
    for r_idx, row in enumerate(dataframe_to_rows(performance_df, index=False, header=True)):
        ws.append(row)
    
    del wb["Sheet"]
    wb.save("optimized_slips_with_performance.xlsx")
    st.success("Exported to Excel!")

# import streamlit as st
# import pandas as pd
# import numpy as np
# import random
# from openpyxl.styles import PatternFill
# from openpyxl.utils.dataframe import dataframe_to_rows
# from openpyxl.workbook import Workbook

# # Title of the app
# st.title("Bet Slip Optimizer with Variants")

# # Sidebar for user inputs
# st.sidebar.header("Input Parameters")
# num_slips = st.sidebar.number_input("Number of Primary Slips", min_value=1, max_value=20, value=3)
# fixtures_per_slip = st.sidebar.number_input("Fixtures per Slip", min_value=1, max_value=10, value=4)
# max_high_risk = st.sidebar.number_input("Max High-Risk Fixtures per Slip", min_value=0, max_value=10, value=1)
# num_variants = st.sidebar.number_input("Variants per Primary Slip", min_value=1, max_value=5, value=2)

# # Load fixture data from CSV
# uploaded_file = st.sidebar.file_uploader("Upload Fixture Data (CSV)", type=["csv"])
# if uploaded_file is not None:
#     fixtures = pd.read_csv(uploaded_file)
    
#     # Extract all possible bet types (W1, X, W2, BTTS Yes, BTTS No)
#     bet_types = [col.replace(" Odds", "") for col in fixtures.columns if " Odds" in col]

#     # Categorize fixtures by risk level
#     fixtures["Risk Level"] = np.where(
#         fixtures["Category"] == "Favorite", "Low",
#         np.where(fixtures["Category"] == "Moderate", "Medium", "High")
#     )
# else:
#     st.warning("Please upload a CSV file with fixture data.")
#     st.stop()

# # Function to generate a single slip with random bet types
# def generate_slip(fixtures, fixtures_per_slip, max_high_risk, bet_types):
#     slip_fixtures = []
#     high_risk_count = 0
    
#     while len(slip_fixtures) < fixtures_per_slip:
#         # Randomly select a fixture
#         fixture = fixtures.sample(1).iloc[0]
#         if fixture["Risk Level"] == "High":
#             if high_risk_count >= max_high_risk:
#                 continue
#             high_risk_count += 1
        
#         # Randomly select a bet type for this fixture
#         selected_bet = random.choice(bet_types)
#         selected_odds = fixture[f"{selected_bet} Odds"]
        
#         slip_fixtures.append({
#             "Fixture ID": fixture["Fixture ID"],
#             "Home Team": fixture["Home Team"],
#             "Away Team": fixture["Away Team"],
#             "Bet Type": selected_bet,
#             "Odds": selected_odds,
#             "Risk Level": fixture["Risk Level"]
#         })
    
#     return pd.DataFrame(slip_fixtures)

# # Function to create variants of a slip by altering one bet type
# def create_variants(original_slip, fixtures, bet_types, num_variants):
#     variants = []
#     for _ in range(num_variants):
#         variant = original_slip.copy()
#         row_to_change = random.randint(0, len(variant)-1)
#         fixture_id = variant.iloc[row_to_change]["Fixture ID"]
        
#         # Get all possible bet types for this fixture
#         fixture_data = fixtures[fixtures["Fixture ID"] == fixture_id].iloc[0]
#         possible_bets = [bt for bt in bet_types if not pd.isna(fixture_data[f"{bt} Odds"])]
#         current_bet = variant.iloc[row_to_change]["Bet Type"]
#         new_bet = random.choice([bt for bt in possible_bets if bt != current_bet])
        
#         variant.at[row_to_change, "Bet Type"] = new_bet
#         variant.at[row_to_change, "Odds"] = fixture_data[f"{new_bet} Odds"]
#         variants.append(variant)
#     return variants

# # Generate primary slips and variants
# if st.button("Generate Slips"):
#     primary_slips = [generate_slip(fixtures, fixtures_per_slip, max_high_risk, bet_types) for _ in range(num_slips)]
#     all_slips = []
    
#     for i, slip in enumerate(primary_slips):
#         # Add primary slip
#         all_slips.append({"type": "Primary", "slip": slip, "slip_id": i+1})
#         # Generate variants
#         variants = create_variants(slip, fixtures, bet_types, num_variants)
#         for j, variant in enumerate(variants):
#             all_slips.append({"type": f"Variant {j+1}", "slip": variant, "slip_id": i+1})
    
#     # Export to Excel with color-coding
#     wb = Workbook()
#     red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
#     green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    
#     for slip_data in all_slips:
#         slip = slip_data["slip"]
#         sheet_name = f"Slip {slip_data['slip_id']} ({slip_data['type']})"
#         ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name limit
        
#         # Add DataFrame to sheet
#         for r_idx, row in enumerate(dataframe_to_rows(slip, index=False, header=True)):
#             ws.append(row)
#             if r_idx == 0:  # Header row
#                 for cell in ws[r_idx+1]:
#                     cell.fill = green_fill if slip_data["type"] == "Primary" else red_fill
        
#     # Remove default sheet and save
#     del wb["Sheet"]
#     wb.save("optimized_slips_with_variants.xlsx")
#     st.success("Slips exported to optimized_slips_with_variants.xlsx")
    
#     # Display sample slip
#     st.subheader("Sample Primary Slip")
#     st.dataframe(primary_slips[0])