import sqlite3
import pandas as pd
import os
from datetime import datetime

def init_db():
    """Initialize database with proper schema"""
    db_path = os.path.join(os.path.dirname(__file__), "betting_app.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Prediction Sessions
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Fixtures Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            fixture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            home_team TEXT,
            away_team TEXT,
            w1_odds REAL,
            x_odds REAL,
            w2_odds REAL,
            btts_yes_odds REAL,
            btts_no_odds REAL,
            category TEXT,
            FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
        )
    """)
    
    # Slips Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS slips (
            slip_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            slip_name TEXT,
            slip_type TEXT,
            fixture_id INTEGER,
            bet_type TEXT,
            odds REAL,
            risk_level TEXT,
            status TEXT DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id),
            FOREIGN KEY(fixture_id) REFERENCES fixtures(fixture_id)
        )
    """)
    conn.commit()
    conn.close()

def create_prediction_session(name, created_at):
    """
    Create a new prediction session in the database.
    Returns the ID of the newly created session.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    c = conn.cursor()
    c.execute("""
        INSERT INTO predictions (name, created_at)
        VALUES (?, ?)
    """, (name, created_at))
    conn.commit()
    prediction_id = c.lastrowid
    conn.close()
    return prediction_id

def get_prediction_sessions():
    """
    Retrieve all prediction sessions from the database.
    Returns a list of dictionaries with session details.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    query = "SELECT prediction_id, name, created_at FROM predictions"
    sessions = pd.read_sql(query, conn).to_dict('records')
    conn.close()
    return sessions

def get_fixtures_from_db(prediction_id=None):
    """
    Retrieve fixtures from the database.
    If prediction_id is provided, retrieve fixtures for that session only.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    if prediction_id:
        query = "SELECT * FROM fixtures WHERE prediction_id = ?"
        fixtures = pd.read_sql(query, conn, params=(prediction_id,))
    else:
        query = "SELECT * FROM fixtures"
        fixtures = pd.read_sql(query, conn)
    conn.close()
    return fixtures

def calculate_performance(prediction_id):
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    
    # Query slips for the given prediction_id
    query = """
        SELECT 
            slip_name,
            slip_type,
            status,
            odds,
            risk_level
        FROM slips
        WHERE prediction_id = ?
    """
    slips = pd.read_sql(query, conn, params=(prediction_id,))
    
    # Calculate total odds and risk score for each slip
    if not slips.empty:
        # Group by slip_name and calculate metrics
        performance_data = slips.groupby("slip_name").agg(
            total_odds=("odds", "prod"),  # Multiply odds for total odds
            risk_level=("risk_level", lambda x: x.mode()[0]),  # Most common risk level
            status=("status", lambda x: x.mode()[0]),  # Most common status
        ).reset_index()
    
    conn.close()
    return performance_data

# Save fixtures to the database
def save_fixtures_to_db(fixtures):
    """
    Save fixtures to the database.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    fixtures.to_sql("fixtures", conn, if_exists="replace", index=False)
    conn.close()


# Save slips to the database
def save_slips_to_db(slips, prediction_id):
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    c = conn.cursor()
    
    # Clear existing slips for this session to avoid duplicates
    c.execute("DELETE FROM slips WHERE prediction_id = ?", (prediction_id,))
    
    for slip in slips:
        # Extract slip metadata
        slip_type = slip["Type"]
        slip_name = slip_type  # Or generate a unique name if needed
        
        # Save each fixture in the slip
        for _, row in slip["Slip"].iterrows():
            c.execute(
                """
                INSERT INTO slips 
                (prediction_id, slip_name, slip_type, fixture_id, bet_type, odds, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction_id,
                    slip_name,
                    slip_type,
                    row["Fixture ID"],
                    row["Bet Type"],
                    row["Odds"],
                    row["Risk Level"],
                ),
            )
    conn.commit()
    conn.close()


# Retrieve slips from the database
def get_slips_from_db(prediction_id):
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    query = """
        SELECT 
            slips.*,
            fixtures.home_team,
            fixtures.away_team
            status 
        FROM slips 
        JOIN fixtures ON slips.fixture_id = fixtures.fixture_id
        WHERE prediction_id = ?
    """
    slips = pd.read_sql(query, conn, params=(prediction_id,))
    conn.close()
    return slips

# Update slip status in the database
def update_slip_status(slip_type, status):
    """
    Update the status of a slip in the database.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "betting_app.db"))
    conn.execute("""
        UPDATE slips
        SET status = ?
        WHERE slip_type = ?
    """, (status, slip_type))
    conn.commit()
    conn.close()

# Initialize the database when this script is run
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")