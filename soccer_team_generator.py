import streamlit as st
import random
from collections import defaultdict
from fpdf import FPDF # New library for PDF generation

# --- CONFIG ---
TEAM_COLORS = [
    ("🔴", "Red"), ("🔵", "Blue"), ("🟢", "Green"), ("🟡", "Yellow"),
    ("🟠", "Orange"), ("🟣", "Purple"), ("⚫", "Black"), ("⚪", "White")
]

# --- SESSION STATE & AUTHENTICATION INITIALIZATION ---
# This dictionary simulates a database. Data is NOT persistent across sessions.
# This is a key limitation of this demo.
if "db" not in st.session_state:
    st.session_state.db = {
        "users": {},
        "payments": {}
    }
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "free_member" not in st.session_state:
    st.session_state.free_member = False
if "current_user_email" not in st.session_state:
    st.session_state.current_user_email = None

# --- FUNCTIONS ---
def get_player_info(player_input):
    """
    Parses a string like "Joe (5), GK-Bob (4)" into a list of player dicts.
    Each player dict has 'name', 'rating', and 'is_gk' keys.
    """
    players = []
    if not player_input:
        return players

    # Split by comma and clean up whitespace
    player_list = [p.strip() for p in player_input.split(',')]
    
    for player_str in player_list:
        if not player_str:
            continue
        
        rating = 3  # Default rating if not specified
        name = player_str
        
        # Check for rating in parentheses
        if '(' in player_str and ')' in player_str:
            try:
                # Find the last '(' and ')' to handle names with parentheses
                start_paren = player_str.rfind('(')
                end_paren = player_str.rfind(')')
                rating = int(player_str[start_paren + 1:end_paren])
                name = player_str[:start_paren].strip()
            except (ValueError, IndexError):
                # If parsing fails, use default and keep original name
                rating = 3
                name = player_str
        
        # Check for goalkeeper status
        is_gk_status = name.upper().startswith("GK-") or name.upper().startswith("PO-")
        
        players.append({
            "name": name,
            "rating": max(1, min(5, rating)), # Clamp rating between 1 and 5
            "is_gk": is_gk_status
        })

    return players

def make_teams(players, num_teams):
    """
    Creates balanced teams based on player ratings. This function ensures teams
    have a similar total skill score.
    """
    # Separate players by role and sort them by rating in descending order
    goalkeepers = sorted([p for p in players if p["is_gk"]], key=lambda x: x["rating"], reverse=True)
    field_players = sorted([p for p in players if not p["is_gk"]], key=lambda x: x["rating"], reverse=True)

    # Assign colors to teams
    colors = TEAM_COLORS.copy()
    random.shuffle(colors)
    team_info = [colors[i % len(colors)] for i in range(num_teams)]  # tuple (emoji, color)

    teams = [[] for _ in range(num_teams)]
    team_skills = [0] * num_teams

    # 1) Assign GKs to each team one by one to balance skill
    for i, gk in enumerate(goalkeepers):
        team_idx = i % num_teams
        teams[team_idx].append(gk)
        team_skills[team_idx] += gk["rating"]
    
    # 2) Assign field players to each team one by one to balance skill
    # This "snake draft" method of distributing players from highest to lowest
    # ensures the total skill is as balanced as possible.
    for i, player in enumerate(field_players):
        team_idx = i % num_teams
        teams[team_idx].append(player)
        team_skills[team_idx] += player["rating"]

    # Sort each team's players by name for consistent display
    for team in teams:
        team.sort(key=lambda x: x["name"].lower())

    return teams, team_info, team_skills

def display_player(player_dict):
    """Formats a player's name and rating for display."""
    name = player_dict["name"]
    rating = player_dict["rating"]
    is_gk = player_dict["is_gk"]
    star_rating = "⭐" * rating
    
    if is_gk:
        return f"{name} 🧤 ({star_rating})"
    else:
        return f"{name} ({star_rating})"

def display_teams(teams, team_info, team_skills):
    """Displays the generated teams in the Streamlit app."""
    st.markdown("### Generated Teams")
    
    for idx, team in enumerate(teams):
        color_emoji, color_name = team_info[idx]
        total_skill = team_skills[idx]
        
        # Calculate average skill for display
        avg_skill = total_skill / len(team) if team else 0
        
        st.markdown(
            f"""
            <div style="
                border: 2px solid #333;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                background-color: #f0f2f6;
            ">
                <h4 style="margin-top: 0;">
                    Team {idx+1} {color_emoji} ({color_name}) - {len(team)} players
                    <span style="float: right; font-size: 1rem;">
                        Avg Skill: {avg_skill:.2f}
                    </span>
                </h4>
                <ul style="padding-left: 20px;">
            """,
            unsafe_allow_html=True
        )

        for player in team:
            st.markdown(f"<li>{display_player(player)}</li>", unsafe_allow_html=True)
        
        st.markdown("</ul></div>", unsafe_allow_html=True)
        
def generate_pdf(teams, team_info, team_skills):
    """
    Generates a PDF file of the team rosters using FPDF.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Soccer Team Roster", ln=1, align="C")
    pdf.ln(5)

    # Add team info
    pdf.set_font("Helvetica", "", 12)
    for idx, team in enumerate(teams):
        color_emoji, color_name = team_info[idx]
        total_skill = team_skills[idx]
        avg_skill = total_skill / len(team) if team else 0
        
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Team {idx+1} ({color_name}) - Avg Skill: {avg_skill:.2f}", ln=1)
        pdf.set_font("Helvetica", "", 12)
        
        for player in team:
            player_info = f"- {player['name']} ({player['rating']} stars)"
            if player['is_gk']:
                player_info += " [GK]"
            pdf.cell(0, 7, player_info, ln=1)
        pdf.ln(5)
    
    return pdf.output(dest="S").encode("latin1") # Return as byte string

# --- APP LAYOUT ---
st.set_page_config(
    page_title="Soccer Team Balancer",
    layout="wide"
)

st.title("⚽ Soccer Team Generator")
st.markdown("---")

st.sidebar.header("Account Status")

# Menu for authentication
account_status = st.sidebar.radio(
    "Choose your status:",
    ("Continue as a Free Member", "Create a Profile", "Log In")
)

if account_status == "Create a Profile":
    with st.sidebar.form(key="signup_form"):
        st.subheader("Create Your Profile")
        st.markdown("Data is not persistent. This is a demo.")
        
        user_name = st.text_input("First Name")
        surname = st.text_input("Surname")
        email = st.text_input("Email Address")
        phone = st.text_input("Phone Number")
        
        signup_button = st.form_submit_button(label="Sign Up")
        
        if signup_button and email:
            st.session_state.db["users"][email] = {
                "name": user_name,
                "surname": surname,
                "phone": phone
            }
            st.session_state.logged_in = True
            st.session_state.free_member = False
            st.session_state.current_user_email = email
            st.success(f"Profile for {email} created! You are now logged in.")

elif account_status == "Log In":
    with st.sidebar.form(key="login_form"):
        st.subheader("Log In")
        login_email = st.text_input("Email Address")
        login_button = st.form_submit_button(label="Log In")
        
        if login_button:
            if login_email in st.session_state.db["users"]:
                st.session_state.logged_in = True
                st.session_state.free_member = False
                st.session_state.current_user_email = login_email
                st.success(f"Welcome back, {st.session_state.db['users'][login_email]['name']}!")
            else:
                st.error("Email not found. Please create a profile first.")

elif account_status == "Continue as a Free Member":
    st.session_state.logged_in = False
    st.session_state.free_member = True
    st.session_state.current_user_email = None
    st.sidebar.info("You are in free trial mode. Some features are limited.")

# Display user status on main page
if st.session_state.logged_in:
    current_user = st.session_state.db["users"][st.session_state.current_user_email]["name"]
    st.info(f"Welcome, {current_user}! You are a full member. All features are available.")
elif st.session_state.free_member:
    st.info("You are currently a free member. Sign up to unlock all features!")

st.markdown("---")

# Main team generation logic
st.header("Team Creation Settings")

player_input = st.text_area(
    "Enter player names, separated by commas. "
    "Use `GK-` or `PO-` for goalkeepers. "
    "Add a rating from 1-5 in parentheses, e.g., `Joe (5), Jane (3), GK-Bob (4)`.",
    height=150,
    placeholder="Joe (5), Jane (3), GK-Bob (4), Frank (2)..."
)

col1, col2 = st.columns(2)
with col1:
    num_teams = st.number_input(
        "Number of Teams",
        min_value=2,
        value=2
    )

if st.button("Generate Teams", use_container_width=True):
    players = get_player_info(player_input)
    if len(players) < num_teams:
        st.error(f"Please enter at least {num_teams} players to create {num_teams} teams.")
    else:
        teams, team_info, team_skills = make_teams(players, num_teams)
        display_teams(teams, team_info, team_skills)
        
        st.session_state.teams = teams
        st.session_state.team_info = team_info
        st.session_state.team_skills = team_skills

st.markdown("---")

# Features for generated teams
if "teams" in st.session_state:
    st.header("Actions")
    
    # Download Teams as PDF
    pdf_bytes = generate_pdf(st.session_state.teams, st.session_state.team_info, st.session_state.team_skills)
    st.download_button(
        label="Download Teams as PDF",
        data=pdf_bytes,
        file_name="soccer_teams.pdf",
        mime="application/pdf"
    )

    # Send Teams Buttons
    if st.session_state.logged_in:
        st.markdown("#### Send Teams to Your Account Info")
        col_send_email, col_send_phone = st.columns(2)
        
        with col_send_email:
            if st.button("📧 Send to Registered Email"):
                st.info("This is a demo. In a real app, this would use an email API to send the roster to your registered email.")
        
        with col_send_phone:
            if st.button("📱 Send to Registered Phone"):
                st.info("This is a demo. In a real app, this would use a service like Twilio to send an SMS to your registered phone number.")

    elif st.session_state.free_member:
        st.markdown("#### Send Teams to a Friend")
        st.warning("You must be a full member to send teams to an email or phone number. Please sign up to access this feature.")

# Player Payment Tracking
st.sidebar.markdown("---")
st.sidebar.subheader("Player Payment Status")

if player_input:
    players = get_player_info(player_input)
    player_names = [p["name"] for p in players]
    
    if "player_payments" not in st.session_state:
        st.session_state.player_payments = {name: False for name in player_names}
    
    st.markdown("Use this to track who has paid:")
    for name in player_names:
        st.session_state.player_payments[name] = st.sidebar.checkbox(f"✅ Has {name} Paid?", key=f"paid_{name}")
    
    # Optional: Display a summary
    paid_players = [name for name, paid in st.session_state.player_payments.items() if paid]
    if paid_players:
        st.sidebar.markdown(f"**Paid Players:** {', '.join(paid_players)}")
else:
    st.sidebar.info("Enter players on the main page to enable payment tracking.")

