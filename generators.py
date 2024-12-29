import sqlite3
import random
import json

# Database Utility Functions
from db_functions import add_monster_to_db

# Pydantic Models
from pydantic_types import RoomDetails, DungeonRoomInfo
from pydantic_types import MonsterInfo, MonstersInfo
from pydantic_types import ItemInfo, ItemsInfo

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
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rooms")
    num_rooms = cursor.fetchone()[0]
    conn.commit()
    conn.close()

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