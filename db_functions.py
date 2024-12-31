import sqlite3

# Database Utility Functions

# General Connection Function

def get_db_connection():
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This enables fetching rows as dictionaries
    return conn

# Rooms

def add_rooms_to_db(rooms):
    conn = get_db_connection()
    cursor = conn.cursor()
    for room in rooms:
        cursor.execute('''
            INSERT OR IGNORE INTO rooms (id, name, description, connections, visited) 
            VALUES (?, ?, ?, ?, ?)''', room)
    conn.commit()
    conn.close()

def update_room_visited(room_id, visited):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rooms SET visited = ? WHERE id = ?", (visited, room_id))
    conn.commit()
    conn.close()

def update_room_name_and_description(room_id, name, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE rooms
        SET name = CASE WHEN name = 'Unknown' OR ? != name THEN ? ELSE name END,
            description = ?
        WHERE id = ?
    """, (name, name, description, room_id))
    conn.commit()
    conn.close()

def update_room_name(room_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rooms SET name = ? WHERE id = ?", (name, room_id))
    conn.commit()
    conn.close()

def update_room_description(room_id, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rooms SET description = ? WHERE id = ?", (description, room_id))
    conn.commit()
    conn.close()

def get_room_info(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, visited, connections FROM rooms WHERE id = ?", (room_id,))
    room_info = cursor.fetchone()
    conn.close()
    if room_info:
        return dict(room_info)  # Convert the Row object to a dictionary
    return None  # Return None if no data is found

# Player

def fetch_player_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hp, attack, defense FROM player_stats WHERE id = 1")
    stats = cursor.fetchone()
    conn.close()
    if stats:
        return dict(stats)  # Convert the Row object to a dictionary
    return None  # Return None if no data is found

def update_player_hp(hp):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE player_stats SET hp = ? WHERE id = 1", (hp,))
    conn.commit()
    conn.close()

# Monsters

def add_monster_to_db(name, description, room_id, full_hp, attack):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO monsters (id, name, description, room_id, full_hp, hp, attack, defeated) 
        VALUES (NULL, ?, ?, ?, ?, ?, ?, NULL)
        ''', (name, description, room_id, full_hp, full_hp, attack))
    conn.commit()
    conn.close()

def fetch_monster_info(monster_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, full_hp, hp, attack, defeated FROM monsters WHERE id = ?", (monster_id,))
    monster_info = cursor.fetchone()
    conn.close()
    if monster_info:
        return dict(monster_info)  # Convert the Row object to a dictionary
    return None  # Return None if no data is found

def get_monsters_in_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, hp, attack, defeated FROM monsters WHERE room_id = ?", (room_id,))
    monsters = cursor.fetchall()
    conn.close()
    return [dict(monster) for monster in monsters]  # Convert each Row object to a dictionary

def update_monster_hp(monster_id, hp):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE monsters SET hp = ? WHERE id = ?", (hp, monster_id))
    conn.commit()
    conn.close()

def mark_monster_defeated(monster_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE monsters SET defeated = 1 WHERE id = ?", (monster_id,))
    conn.commit()
    conn.close()

# Items

def add_item_to_db(name, description, room_id, is_sword):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO items (id, name, description, is_sword, room_id, is_claimed) 
        VALUES (NULL, ?, ?, ?, ?, NULL)
        ''', (name, description, is_sword, room_id))
    conn.commit()
    conn.close()

def get_random_item():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.id, i.name, i.description 
        FROM items i 
        JOIN player_inventory p ON p.item_id = i.id 
        ORDER BY RANDOM() 
        LIMIT 1
        """
    )
    item = cursor.fetchone()
    conn.close()
    if item:
        return dict(item)  # Convert the Row object to a dictionary
    return None  # Return None if no data is found

def initialize_database(num_rooms=25, main_cycle_size=12, num_subcycles=3, subcycle_size_range=(3, 5)):
    conn = get_db_connection()
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
    from generators import generate_dungeon_with_cycles
    rooms = generate_dungeon_with_cycles(num_rooms, main_cycle_size, num_subcycles, subcycle_size_range)

    # Insert generated rooms into the database
    add_rooms_to_db(rooms)

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