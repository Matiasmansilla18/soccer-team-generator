import streamlit as st
import random
from collections import defaultdict

# --- CONFIG ---
TEAM_COLORS = [
    ("🔴", "Red"), ("🔵", "Blue"), ("🟢", "Green"), ("🟡", "Yellow"),
    ("🟠", "Orange"), ("🟣", "Purple"), ("⚫", "Black"), ("⚪", "White")
]

# --- SESSION STATE INITIALIZATION ---
# This dictionary simulates a database. Data is not persistent.
if "db" not in st.session_state:
    st.session_state.db = {
        "users": {},
        "payments": {}
    }

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
                # If rating parsing fails, use default and keep original name
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
    Creates balanced teams based on player ratings.
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
    # We distribute the highest-rated players first, alternating teams
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

# --- APP LAYOUT ---
st.set_page_config(
    page_title="Soccer Team Balancer",
    layout="wide"
)

st.title("⚽ Soccer Team Generator")
st.markdown("---")

st.sidebar.header("User & Payment Status (Demo)")

with st.sidebar.form(key="profile_form"):
    st.subheader("Create/Update Profile")
    st.markdown("This is a demo. Data is not stored persistently.")
    
    user_name = st.text_input("First Name")
    surname = st.text_input("Surname")
    email = st.text_input("Email Address")
    phone = st.text_input("Phone Number")
    
    submit_button = st.form_submit_button(label="Save Profile")
    
    if submit_button and email:
        st.session_state.db["users"][email] = {
            "name": user_name,
            "surname": surname,
            "phone": phone
        }
        st.success(f"Profile for {email} saved!")

st.sidebar.markdown("---")
st.sidebar.subheader("Payment Status")

if st.session_state.db["users"]:
    user_emails = list(st.session_state.db["users"].keys())
    selected_user = st.sidebar.selectbox("Select a user to update payment:", user_emails)
    
    if st.sidebar.checkbox(f"Mark {selected_user} as Paid?", key=f"paid_{selected_user}"):
        st.session_state.db["payments"][selected_user] = True
    else:
        st.session_state.db["payments"][selected_user] = False

st.sidebar.markdown("---")
st.sidebar.subheader("Current Members")
for email, profile in st.session_state.db["users"].items():
    paid_status = st.session_state.db["payments"].get(email, False)
    payment_emoji = "✅ Paid" if paid_status else "❌ Not Paid"
    st.sidebar.write(f"- **{profile['name']} {profile['surname']}**: {payment_emoji}")

st.markdown("## Team Creation Settings")

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

        st.markdown("---")
        st.markdown("### Matchup Suggestion")
        match_teams = random.sample(range(1, num_teams+1), 2)
        st.info(f"🏟️ First match: Team {match_teams[0]} vs Team {match_teams[1]}")

