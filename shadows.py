import streamlit as st
import json
import sqlite3
import random
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from types import SimpleNamespace

from visualization import build_dungeon_graph, visualize_dungeon_plotly, compute_dungeon_layout, compute_pos, visualize_dungeon_plotly, fetch_dungeon_data

st.set_page_config(layout="centered", page_title="Shadows of Mythlandia", menu_items=None, initial_sidebar_state="collapsed")

# %% Session State Setup
if "current_room_id" not in st.session_state:
    st.session_state.current_room_id = 1  # Starting room ID
if "first_run" not in st.session_state:
    st.session_state.first_run = True
if "previous_room_id" not in st.session_state:
    st.session_state.previous_room_id = None
if "searching" not in st.session_state:
        st.session_state.searching = False


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

    # Create the items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            is_sword BOOLEAN DEFAULT 0,
            room_id INTEGER,
            is_claimed BOOLEAN DEFAULT 0,
            FOREIGN KEY (room_id) REFERENCES rooms (id)
    )
    ''')

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

    # Create the player_inventory table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_inventory (
        id INTEGER PRIMARY KEY,
        item_id INTEGER,
        FOREIGN KEY (item_id) REFERENCES items (id)
    )
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
                    f"Not every room needs a monster. Monster hp ranges from 5-10, and monster attack ranges from 1-10."
                    f"Make sure to include a good mix of easier and more difficult monsters."
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

    # Call OpenAI to generate monsters
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

class ItemInfo(BaseModel):
        name: str
        description: str
        is_sword: bool

class ItemsInfo(BaseModel):
    items: List[ItemInfo]

def generate_items():
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rooms")
    num_rooms = cursor.fetchone()[0]
    print(num_rooms)

    prompt_text = (
                    f"You are a dungeon master generating a list of items and treasures for an immersive text adventure game. "
                    f"The game is called Shadows of Mythlandia, and follows a hero delving deep into the "
                    f"mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses,"
                    f"forgotten tombs, tunnels, and the like."
                    f"The item descriptions should be a mix of more common adventure game items, and new ones specifically"
                    f"crafted for the setting.  Most items should be swords of various types.  The descriptions should be palpable and vivid, but 150 characters or less.",
                    f"Generate between {num_rooms/2} to {num_rooms} items."
                    f"For most of the items, is_sword should be True."
                    f"The output should be in JSON format."
                )
    
    prompt = {
        # "model": "gpt-4o-2024-08-06",
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "system",
                "content": "You are a dungeon master generating a list of items for a immersive text adventure game.",
            },
            {
                "role": "user",
                "content": prompt_text[0],
            },
        ],
        "max_tokens": 1000
    }

    client = get_client()

    # Call OpenAI to generate monsters
    completion = client.beta.chat.completions.parse(**prompt, response_format=ItemsInfo)
    item_list = completion.choices[0].message.parsed


    available_rooms = set(range(2, num_rooms + 1))
    for idx, item in enumerate(item_list.items):
        print(item)
        room_id = random.choice(list(available_rooms))
        available_rooms.discard(room_id)
        cursor.execute('''
        INSERT OR IGNORE INTO items (id, name, description, is_sword, room_id, is_claimed) 
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (idx, item.name, item.description, item.is_sword, room_id, 0))
        
    conn.commit()
    conn.close()

if st.session_state.first_run:
    st.session_state.first_run = False
    with st.spinner('Initializing Game...'):
        initialize_database()
    with st.spinner('Recruiting Monsters...'):
        generate_monsters()
    with st.spinner('Hiding Loot...'):
        generate_items()

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
                    "Make sure to replace any Unknown or Undescribed rooms with real names and descriptions."
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

def generate_battle_descriptions(room_id, battle_stats, monster_name, item):

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

    player_hp_percent = (battle_stats.player_ending_hp / battle_stats.player_full_hp) * 100
    monster_hp_percent = battle_stats.monster_ending_hp / battle_stats.monster_full_hp * 100
    player_attack_percent = battle_stats.player_damage / battle_stats.player_attack * 100
    monster_attack_percent = battle_stats.monster_damage / battle_stats.monster_attack * 100

    prompt_text = (
                    f"You are a dungeon master describing a battle move in an immersive text adventure game. "
                    f"For background, the game is called Shadows of Mythlandia, and follows a hero delving deep into the "
                    f"mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses,"
                    f"forgotten tombs, tunnels, and the like."
                    f"The player is attacking a monster, which is also attacking the player.  Please use the following information to describe the interchange:"
                    f"The room name is: {room_name}"
                    f"The room description is: {room_description}"
                    f"The monster name is: {monster_name}"
                    f"The player starting hp was: {battle_stats.player_starting_hp}"
                    f"The player ending hp is: {battle_stats.player_ending_hp}"
                    f"The player hp percentage is: {player_hp_percent}"
                    f"The player attack percentage is: {player_attack_percent}"
                    f"The monster starting hp was: {battle_stats.monster_starting_hp}"
                    f"The monster ending hp is: {battle_stats.monster_ending_hp}"
                    f"The monster hp percentage is: {monster_hp_percent}"
                    f"The monster attack percentage is: {monster_attack_percent}"
                    f"The monster was defeated: {battle_stats.monster_defeated}"
                    f"The player was defeated: {battle_stats.player_defeated}"
                    f"Please keep the description to 200 characters or less.  Use the room name and description for context, but don't mention the room by name every time."
                    f"The descriptions of the battle should reflect the above player and monster stats."
                    f"For example, a player_attack_percent of 0 would mean the player missed or was blocked.  A low attack percent from either would mean a weak or glancing blow."
                    f"Attack percentages refer to the strength of the current attack compared to the maximum possible attack."
                    f"Hp percentages refer to the current hp compared to the maximum possible hp."
                    f"Don't offer choices, or mention numbers, focus on the action, with vivid, physical, palpable descriptions of what is happening.  Show don't tell"
                )
    
    if item.get_item and item.is_item:
        prompt_text = prompt_text + (
            f"After defeating the monster, the player searches the room and finds {item.name}.  The description of the item is: {item.description}"
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
@st.dialog("Battle!")
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

    # Fetch item details
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM items WHERE room_id = ?", (room_id,))
    item_info = cursor.fetchone()
    if item_info:
        item_id, item_name, item_desc = item_info
        is_item = True
    else:
        item_name = ""
        item_desc = ""
        item_id = 0
        is_item = False
    item = SimpleNamespace()
    item.name = item_name
    item.description = item_desc
    item.get_item = False
    item.id = item_id
    item.is_item = is_item

    # Build battle stats
    battle_stats = SimpleNamespace()
    battle_stats.player_full_hp = 100
    battle_stats.player_starting_hp = player_hp
    battle_stats.player_attack = player_attack
    battle_stats.monster_full_hp = monster_full_hp
    battle_stats.monster_starting_hp = monster_hp
    battle_stats.monster_attack = monster_attack

    st.write(f"### A {monster_name} appears!")

    hp_placeholder = st.empty()

    with hp_placeholder.container():
        c1, c2 = st.columns(2,border=True)
        with c1:
            st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
        with c2:
            st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")

    # Battle options
    if monster_hp > 0:
        col1, col2, col3 = st.columns(3)
        if col1.button("Attack"):
            damage = random.randrange(player_attack-monster_attack, player_attack)  # Simple damage formula
            monster_hp -= damage
            
            if monster_hp <= 0:
                monster_hp = 0
                with st.spinner('Attacking!'):
                    battle_stats.monster_damage = 0
                    battle_stats.player_damage = damage
                    battle_stats.player_ending_hp = player_hp
                    battle_stats.monster_ending_hp = 0
                    battle_stats.monster_defeated = True
                    battle_stats.player_defeated = False
                    item.get_item = True
                    desc = generate_battle_descriptions(room_id,battle_stats,monster_name,item)
                st.write(desc)
                st.warning(f"You dealt {damage} damage to the {monster_name}!")
                st.success(f"You defeated the {monster_name}!")
                conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("UPDATE monsters SET defeated = 1 WHERE id = ?", (monster_id,))
                if item.is_item:
                    cursor.execute("INSERT INTO player_inventory (id, item_id) VALUES (NULL, ?)", (item.id,))
                    cursor.execute("UPDATE items SET is_claimed = 1 WHERE id = ?", (item.id,))
                    st.success(f"You have obtained the item: {item.name}!")
                    if st.button("Return"):
                        st.rerun()

                conn.commit()
                conn.close()
                
                with hp_placeholder.container():
                    c1, c2 = st.columns(2,border=True)
                    with c1:
                        st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
                    with c2:
                        st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")
            else:
                # Monster attacks back
                monster_damage = random.randrange(1,monster_attack-player_defense)
                player_hp -= monster_damage
                with st.spinner('Attacking!'):
                    battle_stats.monster_damage = monster_damage
                    battle_stats.player_damage = damage
                    battle_stats.player_ending_hp = player_hp
                    battle_stats.monster_ending_hp = monster_hp
                    battle_stats.monster_defeated = False
                    if player_hp <= 0:
                        battle_stats.player_defeated = True
                    else:
                        battle_stats.player_defeated = False
                    desc = generate_battle_descriptions(room_id,battle_stats,monster_name,item)
                st.write(desc)
                st.warning(f"You dealt {damage} damage to the {monster_name}!")
                st.error(f"The {monster_name} attacked you for {monster_damage} damage!")
                with hp_placeholder.container():
                    c1, c2 = st.columns(2,border=True)
                    with c1:
                        st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
                    with c2:
                        st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")
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

        conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM player_inventory")
        item_count = cursor.fetchone()[0]
        conn.close()

        if item_count > 0:
            if col2.button("Use Item"):
                conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT item_id FROM player_inventory ORDER BY RANDOM() LIMIT 1")
                item_id = cursor.fetchone()[0]
                cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
                item = cursor.fetchone()
                item = ItemInfo(*item)
                conn.close()

    # if col2.button("Defend"):
    #     st.info("You brace yourself and defend against the attack!")

if monster:
    monster_id, monster_name, monster_hp, monster_attack = monster

    if monster_hp > 0:
        # Battle controls
        col1, col2, col3 = st.columns(3)
        if col1.button("Fight!"):
            battle_dialog(monster_id,st.session_state.current_room_id)
        if col2.button("Flee"):
            st.session_state.current_room_id = st.session_state.previous_room_id
            st.rerun()
    else:
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
    if st.button("FORGE", type="primary",key='forge', use_container_width=True):
        st.write('FORGING')

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
