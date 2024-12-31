import sqlite3
import random
import json
import streamlit as st

# Database Utility Functions
from db_functions import get_db_connection
from db_functions import get_room_info, update_room_visited, update_room_name_and_description
from db_functions import add_monster_to_db, get_monsters_in_room
from db_functions import add_item_to_db

# Pydantic Models
from pydantic_types import DungeonRoomInfo
from pydantic_types import MonstersInfo
from pydantic_types import ItemsInfo

# AI Utility Functions
from ai_functions import chat_prompt, chat_prompt_json, get_client

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

def generate_monsters():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rooms")
    num_rooms = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    prompt_text = f"""
    You are a dungeon master generating a list of monsters for a immersive text adventure game.
    The game is called Shadows of Mythlandia, and follows a hero delving deep into the mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses, forgotten tombs, tunnels, and the like.
    The monster descriptions should be a mix of more common adventure game monsters, and new ones specifically crafted for the setting. The descriptions should be palpable and vivid, but 150 characters or less.
    room_id should range from 2 to {num_rooms}.
    Not every room needs a monster. Monster hp ranges from 5-10, and monster attack ranges from 1-10.
    Make sure to include a good mix of easier and more difficult monsters.
    Do not generate numbers outside of the appropriate ranges.
    The output should be in JSON format.
    """
    
    system_prompt = "You are a dungeon master generating a list of monsters for a immersive text adventure game."
    
    monster_list = chat_prompt_json(prompt_text,system_prompt,1000,MonstersInfo)

    # Assign monsters to rooms
    available_rooms = set(range(2, num_rooms + 1))
    for monster in monster_list.monsters:
        # Randomly select a room, and remove it from the available rooms
        room_id = random.choice(list(available_rooms))
        available_rooms.discard(room_id)
        # Limit hp and attack to a maximum of 100 and 10
        full_hp = min(monster.hp, 100)
        attack = min(monster.attack, 10)
        # Insert the monster into the database
        add_monster_to_db(monster.name, monster.description, room_id, full_hp, attack)

def generate_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rooms")
    num_rooms = cursor.fetchone()[0]

    prompt_text = f"""
    You are a dungeon master generating a list of items and treasures for an immersive text adventure game.
    The game is called Shadows of Mythlandia, and follows a hero delving deep into the mysterious vaults of an ancient mountain riddles with caverns, dwarven fortresses, forgotten tombs, tunnels, and the like.
    The item descriptions should be a mix of more common adventure game items, and new ones specifically crafted for the setting. Most items should be swords of various types. The descriptions should be palpable and vivid, but 150 characters or less.
    Generate between {num_rooms/2} to {num_rooms} items.
    For most of the items, is_sword should be True.
    The output should be in JSON format.
    """
    
    prompt = {
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

    # Call OpenAI to generate items
    completion = client.beta.chat.completions.parse(**prompt, response_format=ItemsInfo)
    item_list = completion.choices[0].message.parsed

    # Assign items to rooms
    available_rooms = set(range(2, num_rooms + 1))
    for idx, item in enumerate(item_list.items):
        # Randomly select a room, and remove it from the available rooms
        room_id = random.choice(list(available_rooms))
        available_rooms.discard(room_id)
        # Insert the item into the database
        add_item_to_db(item.name, item.description, room_id, item.is_sword)
        
    conn.commit()
    conn.close()

@st.cache_data
def generate_room_details(room_id, neighbor_ids, visited, current_room_monsters, monsters):
    """Generate room names and descriptions using OpenAI JSON mode."""
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query current room and neighboring room details
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
    print('Neighbors for AI:', neighbors_for_ai)

    # Format monsters for the AI prompt
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
        f"Neighboring room information:\n{json.dumps(neighbors_for_ai, indent=4)}\n\n"
        f"Monsters in neighboring rooms:\n{json.dumps(neighbor_monsters_for_ai, indent=4)}\n\n"
        f"Provide a short but immersive room description considering these details. Don't change the room in the Neighboring room information.\n"
        "Provide output in JSON format:\n"
        "{'current_room': {'id': '', 'name': '', 'description': ''}, "
        "'neighbors': [{'id': '', 'name': '', 'description': ''}, ...], "\
    )

    system_prompt = (
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
        "Please do not change any room ids, just replace the room names and descriptions."
        "Do not generate more neighbors than exist in the Neighboring room information"
    )

    print('Prompt text:', prompt_text)

    details = chat_prompt_json(prompt_text, system_prompt, 500, DungeonRoomInfo)
    print('Chat response:', details)

    # Update the database with the new room details
    update_room_name_and_description(details.current_room.id, details.current_room.name, details.current_room.description)

    for idx, neighbor in enumerate(details.neighbors):
        if neighbors_for_ai[idx]['name'] == 'Unknown':
            update_room_name_and_description(neighbors_for_ai[idx]['id'], neighbor.name, neighbor.description)

    conn.commit()
    conn.close()

def get_room_description(room_id):

    # Get current room's visited status and connections
    room_data = get_room_info(room_id)

    # Get the ids of neighboring rooms
    neighbor_ids = json.loads(room_data['connections'])

    # Query monsters in the current room
    current_room_monsters = get_monsters_in_room(room_id)

    # Query monsters in neighboring rooms
    neighbor_monsters = []
    for neighbor_id in neighbor_ids:
        neighbor_monsters.extend(get_monsters_in_room(neighbor_id))

    # Concatenate current room monsters and neighbor monsters
    all_monsters = current_room_monsters + neighbor_monsters

    # Generate names and descriptions for the current room and neighbors - save to database
    generate_room_details(room_id, neighbor_ids, room_data['visited'], current_room_monsters, all_monsters)
    
    # Set visited status for the current room
    update_room_visited(room_id, True)

    # Get updated room description
    room_data = get_room_info(room_id)

    # Build text for the room description
    text = f"---{room_data['name']}---\n{room_data['description']}"

    return text

def generate_battle_descriptions(room_id, battle_stats, monster_name, item):

    # Fetch room name and description for the given room_id
    room_data = get_room_info(room_id)

    player_hp_percent = (battle_stats.player_ending_hp / battle_stats.player_full_hp) * 100
    monster_hp_percent = battle_stats.monster_ending_hp / battle_stats.monster_full_hp * 100
    player_attack_percent = battle_stats.player_damage / battle_stats.player_attack * 100
    monster_attack_percent = battle_stats.monster_damage / battle_stats.monster_attack * 100

    prompt_text = f"""
    You are a dungeon master describing a battle move in an immersive text adventure game. 
    For background, the game is called Shadows of Mythlandia, and follows a hero delving deep into the 
    mysterious vaults of an ancient mountain riddled with caverns, dwarven fortresses, 
    forgotten tombs, tunnels, and the like.

    The player is attacking a monster, which is also attacking the player. Please use the following information to describe the interchange:
    - The room name is: {room_data['name']}
    - The room description is: {room_data['description']}
    - The monster name is: {monster_name}
    - The player starting hp was: {battle_stats.player_starting_hp}
    - The player ending hp is: {battle_stats.player_ending_hp}
    - The player hp percentage is: {player_hp_percent}
    - The player attack percentage is: {player_attack_percent}
    - The monster starting hp was: {battle_stats.monster_starting_hp}
    - The monster ending hp is: {battle_stats.monster_ending_hp}
    - The monster hp percentage is: {monster_hp_percent}
    - The monster attack percentage is: {monster_attack_percent}
    - The monster was defeated: {battle_stats.monster_defeated}
    - The player was defeated: {battle_stats.player_defeated}

    Please keep the description to 200 characters or less. Use the room name and description for context, but don't mention the room by name every time. 
    The descriptions of the battle should reflect the above player and monster stats. 
    For example:
    - A player_attack_percent of 0 would mean the player missed or was blocked. 
    - A low attack percent from either would mean a weak or glancing blow. 
    - Attack percentages refer to the strength of the current attack compared to the maximum possible attack. 
    - Hp percentages refer to the current hp compared to the maximum possible hp.

    Don't offer choices, or mention numbers. Focus on the action with vivid, physical, palpable descriptions of what is happening. Show, don't tell.
    """
    
    if item and battle_stats.monster_defeated:
        prompt_text = prompt_text + (
            f"After defeating the monster, the player searches the room and finds {item.name}.  The description of the item is: {item.description}"
        )

    system_prompt = "You are a dungeon master describing a battle in an immersive text adventure game.  The user will supply the details of the situation, your job is to describe the action given the information."
    
    battle_desc = chat_prompt(prompt_text, system_prompt, 200)

    return battle_desc