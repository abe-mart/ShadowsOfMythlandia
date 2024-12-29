import sqlite3

# Database Utility Functions

# General Connection Function

def get_db_connection():
    return sqlite3.connect("adventure_game.db", check_same_thread=False)

# Player

def fetch_player_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hp, attack, defense FROM player_stats WHERE id = 1")
    stats = cursor.fetchone()
    conn.close()
    return stats

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
    cursor.execute("SELECT name, full_hp, hp, attack FROM monsters WHERE id = ?", (monster_id,))
    monster_info = cursor.fetchone()
    conn.close()
    return monster_info

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

def add_item_to_db(name, description, room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO items (name, description, is_sword, room_id, is_claimed) 
        VALUES (NULL, ?, ?, ?, ?, ?, ?)
        ''', (idx, item.name, item.description, item.is_sword, room_id, 0))
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
    return item