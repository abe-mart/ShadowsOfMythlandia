import streamlit as st
import json
import sqlite3
import random
from openai import OpenAI
from pydantic import BaseModel
from typing import List

from visualization import build_dungeon_graph, visualize_dungeon_plotly, compute_dungeon_layout, compute_pos, visualize_dungeon_plotly, fetch_dungeon_data

st.set_page_config(layout="centered", page_title="Shadows of Mythlandia", menu_items=None, initial_sidebar_state="collapsed")

# %% Session State Setup
if "current_room_id" not in st.session_state:
    st.session_state.current_room_id = 1  # Starting room ID
if "first_run" not in st.session_state:
    st.session_state.first_run = True
if "previous_room_id" not in st.session_state:
    st.session_state.previous_room_id = None


# Hide menu in production
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Logo
st.image('Images/Shadows.png', use_container_width=True)

def generate_dungeon_with_cycles(num_rooms, main_cycle_size, num_subcycles, subcycle_size_range):
    """
    Generates a dungeon layout using the cycles principle with a main cycle and smaller branching subcycles.
    
    :param num_rooms: Total number of rooms in the dungeon.
    :param main_cycle_size: Number of rooms in the main cycle.
    :param num_subcycles: Number of subcycles branching off from the main cycle.
    :param subcycle_size_range: Tuple (min_size, max_size) for subcycle sizes.
    :return: List of rooms with their connections.
    """
    if main_cycle_size > num_rooms:
        raise ValueError("Main cycle size cannot exceed total number of rooms.")
    
    # Step 1: Initialize rooms and connections
    rooms = []
    connections_map = {room_id: set() for room_id in range(1, num_rooms + 1)}
    
    # Step 2: Create the main cycle
    main_cycle = list(range(1, main_cycle_size + 1))
    for i in range(len(main_cycle)):
        room = main_cycle[i]
        next_room = main_cycle[(i + 1) % len(main_cycle)]  # Loop back to the start
        connections_map[room].add(next_room)
        connections_map[next_room].add(room)
    
    # Step 3: Add subcycles branching off the main cycle
    remaining_rooms = list(set(range(1, num_rooms + 1)) - set(main_cycle))
    for _ in range(num_subcycles):
        if not remaining_rooms:
            break
        
        subcycle_size = random.randint(*subcycle_size_range)
        if len(remaining_rooms) < subcycle_size:
            subcycle_size = len(remaining_rooms)
        
        subcycle = random.sample(remaining_rooms, subcycle_size)
        for i in range(len(subcycle)):
            room = subcycle[i]
            next_room = subcycle[(i + 1) % len(subcycle)]
            connections_map[room].add(next_room)
            connections_map[next_room].add(room)
        
        # Connect the subcycle to the main cycle at one or more points
        connection_point = random.choice(main_cycle)
        subcycle_room = random.choice(subcycle)
        connections_map[connection_point].add(subcycle_room)
        connections_map[subcycle_room].add(connection_point)
        
        # Remove used rooms from remaining_rooms
        remaining_rooms = list(set(remaining_rooms) - set(subcycle))
    
    # Step 4: Create the final room list
    for room_id in range(1, num_rooms + 1):
        connections_json = json.dumps(list(connections_map[room_id]))
        rooms.append((room_id, "", "", connections_json, 0))
    
    return rooms

class RoomDetails(BaseModel):
    id: int
    name: str
    description: str

class DungeonRoomInfo(BaseModel):
    current_room: RoomDetails
    neighbors: List[RoomDetails]



@st.cache_resource
def get_client():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    return client

# %% Initialize database on first run
def initialize_database():
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    # Create the rooms table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        connections TEXT NOT NULL, -- JSON string of connections
        visited BOOLEAN DEFAULT 0
    )
    ''')

    # Generate 25 rooms with a random layout
    num_rooms = 25
    main_cycle_size = 12
    num_subcycles = 3
    subcycle_size_range = (3, 5)
    rooms = generate_dungeon_with_cycles(num_rooms, main_cycle_size, num_subcycles, subcycle_size_range)

    # Insert generated rooms into the database
    cursor.executemany('''
    INSERT OR IGNORE INTO rooms (id, name, description, connections, visited) 
    VALUES (?, ?, ?, ?, ?)
    ''', rooms)

    # Set the first room as the starting room
    cursor.execute("UPDATE rooms SET description = 'You enter the dungeon.' WHERE id = 1")

    # Create the monsters table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monsters (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        room_id INTEGER NOT NULL,
        full_hp INTEGER DEFAULT 10,
        hp INTEGER DEFAULT 10,
        attack INTEGER DEFAULT 3,
        defeated BOOLEAN DEFAULT 0,
        FOREIGN KEY (room_id) REFERENCES rooms (id)
    )
    ''')

    # # Example monster entries
    # monsters = [
    #     (1, "Goblin", "A small, green creature with sharp teeth.", 2, 10, 3, 0),
    #     (2, "Skeleton Warrior", "A clattering skeleton armed with a rusty sword.", 3, 15, 5, 0),
    # ]
    # cursor.executemany('''
    # INSERT OR IGNORE INTO monsters (id, name, description, room_id, hp, attack, defeated) 
    # VALUES (?, ?, ?, ?, ?, ?, ?)
    # ''', monsters)

    # Create the player_stats table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_stats (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL DEFAULT 'Hero',
        hp INTEGER DEFAULT 100,
        attack INTEGER DEFAULT 10,
        defense INTEGER DEFAULT 5
    )
    ''')

    # Initialize player stats if not already present
    cursor.execute("SELECT COUNT(*) FROM player_stats")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO player_stats (id, name, hp, attack, defense) 
        VALUES (1, 'Hero', 100, 10, 5)
        ''')

    conn.commit()
    conn.close()

class MonsterInfo(BaseModel):
        id: int
        name: str
        description: str
        room_id: int
        hp: int
        attack: int

class MonstersInfo(BaseModel):
    monsters: List[MonsterInfo]

def generate_monsters():
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rooms")
    num_rooms = cursor.fetchone()[0]
    print(num_rooms)

    prompt_text = (
                    f"You are a dungeon master generating a list of monsters for a immersive text adventure game. "
                    f"The game is called Shadows of Mythlandia, and follows a hero delving deep into the "
                    f"mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses,"
                    f"forgotten tombs, tunnels, and the like."
                    f"The monster descriptions should be a mix of more common adventure game monsters, and new ones specifically"
                    f"crafted for the setting.  The descriptions should be palpable and vivid, but 150 characters or less.",
                    f"room_id should range from 2 to {num_rooms}."
                    f"Not every room needs a monster. Monster hp ranges from 5-100, and monster attack ranges from 1-10."
                    f"Do not generate numbers outside of the appropriate ranges."
                    f"The output should be in JSON format."
                )
    
    prompt = {
        # "model": "gpt-4o-2024-08-06",
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "system",
                "content": "You are a dungeon master generating a list of monsters for a immersive text adventure game.",
            },
            {
                "role": "user",
                "content": prompt_text[0],
            },
        ],
        "max_tokens": 1000
    }

    client = get_client()

    # Call OpenAI to generate room details
    completion = client.beta.chat.completions.parse(**prompt, response_format=MonstersInfo)
    monster_list = completion.choices[0].message.parsed


    available_rooms = set(range(2, num_rooms + 1))
    for monster in monster_list.monsters:
        print(monster)
        room_id = random.choice(list(available_rooms))
        available_rooms.discard(room_id)
        hp = min(monster.hp, 100)
        attack = min(monster.attack, 10)
        cursor.execute('''
        INSERT OR IGNORE INTO monsters (id, name, description, room_id, full_hp, hp, attack, defeated) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (monster.id, monster.name, monster.description, room_id, hp, hp, attack, 0))
        
    conn.commit()
    conn.close()

if st.session_state.first_run:
    st.session_state.first_run = False
    with st.spinner('Initializing game...'):
        initialize_database()
        generate_monsters()

# %% Get room description function
def get_room_description(room_id):
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()

    # Get current room's visited status and connections
    print('Trying to get room ID')
    print(room_id)
    cursor.execute("SELECT visited, connections FROM rooms WHERE id = ?", (room_id,))
    room_data = cursor.fetchone()
    if not room_data:
        print("Room not found!")
        return

    visited, connections_json = room_data
    neighbor_ids = json.loads(connections_json)

    # Query monsters in the current room
    cursor.execute("SELECT name, description, hp, defeated FROM monsters WHERE room_id = ?", (room_id,))
    current_room_monsters = cursor.fetchall()

    # Query monsters in neighboring rooms
    neighbor_monsters = []
    for neighbor_id in neighbor_ids:
        cursor.execute("SELECT name, description, hp, defeated FROM monsters WHERE room_id = ?", (neighbor_id,))
        neighbor_monsters.extend(cursor.fetchall())

    all_monsters = current_room_monsters + neighbor_monsters

    # if not visited:
    # Generate names and descriptions for the current room and neighbors
    name, description = generate_room_details(room_id, neighbor_ids, visited, current_room_monsters, all_monsters)
    cursor.execute("UPDATE rooms SET visited = 1 WHERE id = ?", (room_id,))
    conn.commit()

    cursor.execute("SELECT name, description, connections, visited FROM rooms WHERE id = ?", (room_id,))
    room_data = cursor.fetchone()

    # Fetch monster data
    cursor.execute("SELECT name, description, hp, defeated FROM monsters WHERE room_id = ?", (room_id,))
    monster_data = cursor.fetchone()

    if room_data:
        room_name, room_description, room_connections, visited = room_data
        text = f"---{room_name}---\n{room_description}"

        if monster_data:
            monster_name, monster_description, monster_hp, defeated = monster_data


        dirlist = []  # Directions to display
        codelist = []  # Room IDs for the directions

        connections = json.loads(room_connections)
        for conn_id in connections:
            cursor.execute("SELECT name FROM rooms WHERE id = ?", (conn_id,))
            connected_room = cursor.fetchone()
            if connected_room:
                connected_room_name = connected_room[0]
                dirlist.append(connected_room_name)
                codelist.append(conn_id)

        conn.close()
        return text, dirlist, codelist

    conn.close()
    return "Room not found!", [], []

@st.cache_data
def generate_room_details(room_id, neighbor_ids, visited, current_room_monsters, monsters):
    """Generate room names and descriptions using OpenAI JSON mode."""
    # Query current room and neighboring room details
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, description FROM rooms WHERE id = ?", (room_id,))
    current_room_data = cursor.fetchone()

    cursor.execute("SELECT id, name, description FROM rooms WHERE id IN ({})".format(
        ",".join("?" * len(neighbor_ids))), neighbor_ids)
    neighbors = cursor.fetchall()

    # Query monsters in the current room
    cursor.execute("SELECT name, description, hp, defeated, attack, description FROM monsters WHERE room_id = ?", (room_id,))
    current_room_monsters = cursor.fetchall()

    # Query monster states
    alive_monsters = [m for m in current_room_monsters if not m[3]]  # 'defeated' is at index 3 in the tuple
    defeated_monsters = [m for m in current_room_monsters if m[3]]  # 'defeated' is at index 3 in the tuple

    # Query monsters in neighboring rooms
    neighbor_monsters = []
    for neighbor_id in neighbor_ids:
        cursor.execute("SELECT name, description, hp, defeated, attack, description FROM monsters WHERE room_id = ?", (neighbor_id,))
        neighbor_monsters.extend(cursor.fetchall())

    # Format current room and neighbors for the AI prompt
    neighbors_for_ai = [
        {"id": r[0], "name": r[1] if r[1] else "Unknown", "description": r[2] if r[2] else "Undescribed"}
        for r in neighbors
    ]

    # Format monsters for the AI prompt
    current_room_monsters_for_ai = [
        {"name": r[0], "description": r[1], "hp": r[2], "defeated": r[3], "attack": r[4], "description": r[5]}
        for r in current_room_monsters
    ]
    alive_monsters_for_ai = [
        {"name": r[0], "description": r[1], "hp": r[2], "defeated": r[3], "attack": r[4], "description": r[5]}
        for r in alive_monsters
    ]
    defeated_monsters_for_ai = [
        {"name": r[0], "description": r[1], "hp": r[2], "defeated": r[3], "attack": r[4], "description": r[5]}
        for r in defeated_monsters
    ]
    neighbor_monsters_for_ai = [
        {"name": r[0], "description": r[1], "hp": r[2], "defeated": r[3], "attack": r[4], "description": r[5]}
        for r in neighbor_monsters
    ]

    prompt_text = (
        f"Current room: ID: {current_room_data[0]}, Name: {current_room_data[1] or 'Unknown'}, "
        f"visited: {visited}\n"
        f"Description: {current_room_data[2] or 'Undescribed'}\n\n"
        f"Alive monsters in current room:\n{json.dumps(alive_monsters_for_ai, indent=4)}\n\n"
        f"Defeated monsters in current room:\n{json.dumps(defeated_monsters_for_ai, indent=4)}\n\n"
        f"Neighbors:\n{json.dumps(neighbors_for_ai, indent=4)}\n\n"
        f"Monsters in neighboring rooms:\n{json.dumps(neighbor_monsters_for_ai, indent=4)}\n\n"
        f"Provide a short but immersive room description considering these details. Feel free to alter details of the existing description.\n"
        "Provide output in JSON format:\n"
        "{'current_room': {'id': '', 'name': '', 'description': ''}, "
        "'neighbors': [{'id': '', 'name': '', 'description': ''}, ...], "\
    )

    print(prompt_text)

    prompt = {
        # "model": "gpt-4o-2024-08-06",
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a dungeon master generating immersive room details for a text adventure game. "
                    "Given the current room, its neighbors, and the monsters within, "
                    "provide names and descriptions for each room. Make sure to take into account if the player already defeated the monsters or not."
                    "Descriptions should hint at interconnections and an overarching story."
                    "The game is called Shadows of Mythlandia, and follows a hero delving deep into the "
                    "mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses,"
                    "forgotten tombs, tunnels, and the like."
                    "The room descriptions should be palpable and vivid, as if you were there yourself."
                    "To make the game more atmospheric and immersive, room descriptions should use information"
                    "from the surrounding rooms and the monsters within them to create a sense of surroundings."
                    "When there is a monster present, make sure to focus the description on the monster, and make it clear that it's there."
                    "Remember that not every room has to be an iconic location, sometimes there are just passageways or tunnels."
                    "Keep responses to 500 characters or less"
                ),
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ],
        "max_tokens": 500
    }

    client = get_client()

    # Call OpenAI to generate room details
    completion = client.beta.chat.completions.parse(**prompt, response_format=DungeonRoomInfo)
    details = completion.choices[0].message.parsed
    print(details)

    # Update the database with the new room details
    cursor.execute(
        "UPDATE rooms SET name = ?, description = ? WHERE id = ?",
        (details.current_room.name, details.current_room.description, details.current_room.id),
    )

    for neighbor in details.neighbors:
        cursor.execute(
            "UPDATE rooms SET name = ?, description = ? WHERE id = ?",
            (neighbor.name, neighbor.description, neighbor.id),
        )

    conn.commit()
    conn.close()

    return details.current_room.name, details.current_room.description

def generate_battle_descriptions(room_id, player_hp_percent,player_attack_percent,monster_hp_percent,monster_attack_percent,monster_name):

    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()

    # Fetch room name and description for the given room_id
    cursor.execute("SELECT name, description FROM rooms WHERE id = ?", (room_id,))
    room_data = cursor.fetchone()
    conn.close()

    if room_data:
        room_name, room_description = room_data
    else:
        room_name, room_description = None, None


    prompt_text = (
                    f"You are a dungeon master describing a battle move in an immersive text adventure game. "
                    f"For background, the game is called Shadows of Mythlandia, and follows a hero delving deep into the "
                    f"mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses,"
                    f"forgotten tombs, tunnels, and the like."
                    f"The player is attacking a monster, which is also attacking the player.  Please use the following information to describe the interchange:"
                    f"The room name is: {room_name}"
                    f"The room description is: {room_description}"
                    f"The monster name is: {monster_name}"
                    f"The player hp percentage is: {player_hp_percent}"
                    f"The player attack percentage is: {player_attack_percent}"
                    f"The monster hp percentage is: {monster_hp_percent}"
                    f"The monster attack percentage is: {monster_attack_percent}"
                    f"Please keep the description to 150 characters or less.  Use the room name and description for context, but don't mention the room by name every time."
                    f"The descriptions of the battle should reflect the above player and monster stats."
                    f"Don't offer choices, focus on the action, with vivid, physical, palpable descriptions of what is happening.  Show don't tell"
                )
    
    prompt = {
        # "model": "gpt-4o-2024-08-06",
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "system",
                "content": "You are a dungeon master describing a battle in an immersive text adventure game.  The user will supply the details of the situation, your job is to describe the action given the information.",
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ],
        "max_tokens": 200
    }

    client = get_client()

    # Call OpenAI to generate room details
    completion = client.chat.completions.create(**prompt)
    battle_desc = completion.choices[0].message.content
    return battle_desc

# %% Display current room
text, dirlist, codelist = get_room_description(st.session_state.current_room_id)

# %% UI Components
text_placeholder = st.empty()  # Main game text display

# Check for monsters in the current room
conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("SELECT id, name, hp, attack FROM monsters WHERE room_id = ? AND defeated = 0", (st.session_state.current_room_id,))
monster = cursor.fetchone()
conn.close()

# Define the battle dialog
@st.dialog("Battle Time!")
def battle_dialog(monster_id,room_id):
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT name, full_hp, hp, attack FROM monsters WHERE id = ?", (monster_id,))
    monster_info = cursor.fetchone()
    if monster_info:
        monster_name, monster_full_hp, monster_hp, monster_attack = monster_info
    else:
        monster_name = ""
        monster_full_hp = 0
        monster_hp = 0
        monster_attack = 0

    # Fetch player stats
    cursor.execute("SELECT hp, attack, defense FROM player_stats WHERE id = 1")
    player_hp, player_attack, player_defense = cursor.fetchone()
    conn.close()

    st.write(f"### A {monster_name} appears!")

    hp_placeholder = st.empty()

    with hp_placeholder.container():
        st.write(f"**HP:** {monster_hp} | **Attack:** {monster_attack}")
        st.write(f"**Your HP:** {player_hp} | **Your Attack:** {player_attack}")

    # Battle options
    col1, col2, col3 = st.columns(3)
    if col1.button("Attack"):
        damage = random.randrange(player_attack-monster_attack, player_attack)  # Simple damage formula
        monster_hp -= damage
        
        if monster_hp <= 0:
            player_hp_percent = (player_hp / 100) * 100
            monster_hp_percent = monster_hp / monster_full_hp * 100
            player_attack_percent = damage / player_attack * 100
            monster_attack_percent = 0
            with st.spinner('Attacking!'):
                desc = generate_battle_descriptions(room_id,player_hp_percent,player_attack_percent,monster_hp_percent,monster_attack_percent,monster_name)
            st.write(desc)
            st.warning(f"You dealt {damage} damage to the {monster_name}!")
            st.success(f"You defeated the {monster_name}!")
            conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE monsters SET defeated = 1 WHERE id = ?", (monster_id,))
            conn.commit()
            conn.close()
            st.rerun()
        else:
            # Monster attacks back
            monster_damage = random.randrange(1,monster_attack-player_defense)
            player_hp -= monster_damage
            player_hp_percent = (player_hp / 100) * 100
            monster_hp_percent = monster_hp / monster_full_hp * 100
            player_attack_percent = damage / player_attack * 100
            monster_attack_percent = monster_damage / monster_attack * 100
            with st.spinner('Attacking!'):
                desc = generate_battle_descriptions(room_id,player_hp_percent,player_attack_percent,monster_hp_percent,monster_attack_percent,monster_name)
            st.write(desc)
            st.warning(f"You dealt {damage} damage to the {monster_name}!")
            st.error(f"The {monster_name} attacked you for {monster_damage} damage!")
            with hp_placeholder.container():
                st.write(f"**HP:** {monster_hp} | **Attack:** {monster_attack}")
                st.write(f"**Your HP:** {player_hp} | **Your Attack:** {player_attack}")
            if player_hp <= 0:
                st.error("You have been defeated! Game Over.")
                st.stop()
            else:
                conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("UPDATE monsters SET hp = ? WHERE id = ?", (monster_hp, monster_id))
                cursor.execute("UPDATE player_stats SET hp = ? WHERE id = 1", (player_hp,))
                conn.commit()
                conn.close()

    if col2.button("Defend"):
        st.info("You brace yourself and defend against the attack!")

if monster:
    monster_id, monster_name, monster_hp, monster_attack = monster

    # Battle controls
    col1, col2, col3 = st.columns(3)
    if col1.button("Fight!"):
        battle_dialog(monster_id,st.session_state.current_room_id)
    if col2.button("Flee"):
        st.session_state.current_room_id = st.session_state.previous_room_id
        st.rerun()
else:
    # Direction Buttons
    st.write("### Choose a direction:")
    cols = st.columns(len(dirlist) or 1)
    for i, d in enumerate(dirlist):
        if cols[i].button(d, key=i):
            st.session_state.previous_room_id = st.session_state.current_room_id
            st.session_state.current_room_id = codelist[i]
            st.rerun()  # Refresh the app with the new room

# Action Buttons
# st.write("### Actions:")
# col1, col2, col3 = st.columns(3)

# with col1:
#     if st.button("Attack!"):
#         text += "\nOw, what was that for?"
# with col2:
#     if st.button("Defend!"):
#         text += "\nBlocked!"
# with col3:
#     if st.button("Balloons!"):
#         st.balloons()
#         text += "\nHooray!"

# Update text area
with text_placeholder:
    st.text_area("text", value=text, height=170, disabled=True, label_visibility="collapsed")

# @st.dialog("Dungeon Map")
def build_dungeon_map():
    data = fetch_dungeon_data()
    G, pos = compute_dungeon_layout(data)
    datasub = [(row[0], row[2]) for row in data]
    pos = compute_pos(datasub)
    G_filtered, visited_nodes, unvisited_neighbors = build_dungeon_graph(data, st.session_state.current_room_id)

    fig = visualize_dungeon_plotly(G, pos, visited_nodes, unvisited_neighbors, st.session_state.current_room_id)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, config = {'displayModeBar': False})

# if st.button("Dungeon Map"):
with st.container(border=True):
    build_dungeon_map()


# Footer Text
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.write('#')
st.divider()
cols = st.columns(3)
with cols[0]:
    st.image('Images/badge.jpeg')
with cols[1]:
    st.image('Images/badge2.jpeg')
with cols[2]:
    st.image('Images/badge3.jpeg')
# %%
