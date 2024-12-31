import streamlit as st
import json
import sqlite3
import random
from openai import OpenAI

from types import SimpleNamespace

# Database Utility Functions
from db_functions import get_db_connection, initialize_database
from db_functions import add_rooms_to_db, get_room_info, update_room_visited
from db_functions import fetch_player_stats, update_player_hp
from db_functions import add_monster_to_db, fetch_monster_info, update_monster_hp, mark_monster_defeated, get_monsters_in_room

# Visualization Utility Functions
from visualization import build_dungeon_graph, visualize_dungeon_plotly, compute_dungeon_layout, compute_pos, fetch_dungeon_data, build_dungeon_map

# Pydantic Models
from pydantic_types import RoomDetails, DungeonRoomInfo
from pydantic_types import MonsterInfo, MonstersInfo
from pydantic_types import ItemInfo, ItemsInfo

# AI Utility Functions
from ai_functions import chat_prompt, chat_prompt_json, get_client

# Generators
from generators import generate_dungeon_with_cycles, generate_monsters, generate_items, get_room_description

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

if st.session_state.first_run:
    st.session_state.first_run = False
    with st.spinner('Initializing Game...'):
        initialize_database()
    with st.spinner('Recruiting Monsters...'):
        generate_monsters()
    with st.spinner('Hiding Loot...'):
        generate_items()

# Initialize text area
text_placeholder = st.empty()  # Main game text display

# %% Get current room description
text = get_room_description(st.session_state.current_room_id)

# # Check for monsters in the current room
# conn = get_db_connection()
# cursor = conn.cursor()
# cursor.execute("SELECT id, name, hp, attack FROM monsters WHERE room_id = ? AND defeated = 0", (st.session_state.current_room_id,))
# monster = cursor.fetchone()
# conn.close()

# # Define the battle dialog
# @st.dialog("Battle!")
# def battle_dialog(monster_id,room_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name, full_hp, hp, attack FROM monsters WHERE id = ?", (monster_id,))
#     monster_info = cursor.fetchone()
#     if monster_info:
#         monster_name, monster_full_hp, monster_hp, monster_attack = monster_info
#     else:
#         monster_name = ""
#         monster_full_hp = 0
#         monster_hp = 0
#         monster_attack = 0

#     # Fetch player stats
#     cursor.execute("SELECT hp, attack, defense FROM player_stats WHERE id = 1")
#     player_hp, player_attack, player_defense = cursor.fetchone()
#     conn.close()

#     # Fetch item details
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, name, description FROM items WHERE room_id = ?", (room_id,))
#     item_info = cursor.fetchone()
#     if item_info:
#         item_id, item_name, item_desc = item_info
#         is_item = True
#     else:
#         item_name = ""
#         item_desc = ""
#         item_id = 0
#         is_item = False
#     item = SimpleNamespace()
#     item.name = item_name
#     item.description = item_desc
#     item.get_item = False
#     item.id = item_id
#     item.is_item = is_item

#     # Build battle stats
#     battle_stats = SimpleNamespace()
#     battle_stats.player_full_hp = 100
#     battle_stats.player_starting_hp = player_hp
#     battle_stats.player_attack = player_attack
#     battle_stats.monster_full_hp = monster_full_hp
#     battle_stats.monster_starting_hp = monster_hp
#     battle_stats.monster_attack = monster_attack

#     st.write(f"### A {monster_name} appears!")

#     hp_placeholder = st.empty()

#     with hp_placeholder.container():
#         c1, c2 = st.columns(2,border=True)
#         with c1:
#             st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
#         with c2:
#             st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")

#     # Battle options
#     if monster_hp > 0:
#         col1, col2, col3 = st.columns(3)
#         if col1.button("Attack"):
#             damage = random.randrange(player_attack-monster_attack, player_attack)  # Simple damage formula
#             monster_hp -= damage
            
#             if monster_hp <= 0:
#                 monster_hp = 0
#                 with st.spinner('Attacking!'):
#                     battle_stats.monster_damage = 0
#                     battle_stats.player_damage = damage
#                     battle_stats.player_ending_hp = player_hp
#                     battle_stats.monster_ending_hp = 0
#                     battle_stats.monster_defeated = True
#                     battle_stats.player_defeated = False
#                     item.get_item = True
#                     desc = generate_battle_descriptions(room_id,battle_stats,monster_name,item)
#                 st.write(desc)
#                 st.warning(f"You dealt {damage} damage to the {monster_name}!")
#                 st.success(f"You defeated the {monster_name}!")
#                 conn = get_db_connection()
#                 cursor = conn.cursor()
#                 cursor.execute("UPDATE monsters SET defeated = 1 WHERE id = ?", (monster_id,))
#                 if item.is_item:
#                     cursor.execute("INSERT INTO player_inventory (id, item_id) VALUES (NULL, ?)", (item.id,))
#                     cursor.execute("UPDATE items SET is_claimed = 1 WHERE id = ?", (item.id,))
#                     st.success(f"You have obtained the item: {item.name}!")
#                     if st.button("Return"):
#                         st.rerun()

#                 conn.commit()
#                 conn.close()
                
#                 with hp_placeholder.container():
#                     c1, c2 = st.columns(2,border=True)
#                     with c1:
#                         st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
#                     with c2:
#                         st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")
#             else:
#                 # Monster attacks back
#                 monster_damage = random.randrange(1,monster_attack-player_defense)
#                 player_hp -= monster_damage
#                 with st.spinner('Attacking!'):
#                     battle_stats.monster_damage = monster_damage
#                     battle_stats.player_damage = damage
#                     battle_stats.player_ending_hp = player_hp
#                     battle_stats.monster_ending_hp = monster_hp
#                     battle_stats.monster_defeated = False
#                     if player_hp <= 0:
#                         battle_stats.player_defeated = True
#                     else:
#                         battle_stats.player_defeated = False
#                     desc = generate_battle_descriptions(room_id,battle_stats,monster_name,item)
#                 st.write(desc)
#                 st.warning(f"You dealt {damage} damage to the {monster_name}!")
#                 st.error(f"The {monster_name} attacked you for {monster_damage} damage!")
#                 with hp_placeholder.container():
#                     c1, c2 = st.columns(2,border=True)
#                     with c1:
#                         st.write(f"**Monster HP:** {monster_hp} | **Attack:** {monster_attack}")
#                     with c2:
#                         st.write(f"**Hero HP:** {player_hp} | **Attack:** {player_attack}")
#                 if player_hp <= 0:
#                     st.error("You have been defeated! Game Over.")
#                     st.stop()
#                 else:
#                     conn = get_db_connection()
#                     cursor = conn.cursor()
#                     cursor.execute("UPDATE monsters SET hp = ? WHERE id = ?", (monster_hp, monster_id))
#                     cursor.execute("UPDATE player_stats SET hp = ? WHERE id = 1", (player_hp,))
#                     conn.commit()
#                     conn.close()

#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT COUNT(*) FROM player_inventory")
#         item_count = cursor.fetchone()[0]
#         conn.close()

#         if item_count > 0:
#             if col2.button("Use Item"):
#                 conn = get_db_connection()
#                 cursor = conn.cursor()
#                 cursor.execute("SELECT item_id FROM player_inventory ORDER BY RANDOM() LIMIT 1")
#                 item_id = cursor.fetchone()[0]
#                 cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
#                 item = cursor.fetchone()
#                 item = ItemInfo(*item)
#                 conn.close()

#     # if col2.button("Defend"):
#     #     st.info("You brace yourself and defend against the attack!")

# if monster:
#     monster_id, monster_name, monster_hp, monster_attack = monster

#     if monster_hp > 0:
#         # Battle controls
#         col1, col2, col3 = st.columns(3)
#         if col1.button("Fight!"):
#             battle_dialog(monster_id,st.session_state.current_room_id)
#         if col2.button("Flee"):
#             st.session_state.current_room_id = st.session_state.previous_room_id
#             st.rerun()
#     else:
#         st.rerun()
# else:
# Get neighboring rooms
room_data = get_room_info(st.session_state.current_room_id)
neighbor_ids = json.loads(room_data['connections'])
neighbors = [get_room_info(neighbor_id) for neighbor_id in neighbor_ids]
print(neighbors)

# Direction Buttons
st.write("### Choose a direction:")
cols = st.columns(len(neighbors))
for i, neighbor in enumerate(neighbors):
    print(neighbor)
    if cols[i].button(neighbor['name'], key=i):
        st.session_state.previous_room_id = st.session_state.current_room_id
        st.session_state.current_room_id = neighbor_ids[i]
        st.rerun()  # Refresh the app with the new room

# Forging Controls
if st.button("FORGE", type="primary",key='forge', use_container_width=True):
    st.write('FORGING')

# Update text area
with text_placeholder:
    st.text_area("text", value=text, height=170, disabled=True, label_visibility="collapsed")

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
