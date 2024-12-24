import streamlit as st
import json
import sqlite3
import random
from openai import OpenAI
from pydantic import BaseModel
from typing import List
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(layout="centered", page_title="Shadows of Mythlandia", menu_items=None, initial_sidebar_state="collapsed")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
st.image('Images/Shadows.png', use_column_width=True)

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

def fetch_dungeon_data():
    """Fetch room data from the database."""
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, connections, visited FROM rooms")
    data = cursor.fetchall()
    conn.close()
    return data

def compute_dungeon_layout(data):
    """Build the graph and compute a consistent layout."""
    G = nx.Graph()
    for room_id, name, connections_json, visited in data:
        connections = json.loads(connections_json)
        G.add_node(room_id, name=name, visited=visited)
        for connection in connections:
            G.add_edge(room_id, connection)

    # Compute and return the layout for consistent positioning
    pos = nx.spring_layout(G, seed=42)  # Use a seed for reproducibility
    return G, pos

@st.cache_data
def compute_pos(data_sub):
    """Build the graph and compute a consistent layout."""
    G = nx.Graph()
    for room_id, connections_json in data_sub:
        connections = json.loads(connections_json)
        G.add_node(room_id)
        for connection in connections:
            G.add_edge(room_id, connection)

    # Compute and return the layout for consistent positioning
    pos = nx.spring_layout(G, seed=42)  # Use a seed for reproducibility
    return pos


def build_dungeon_graph(data, current_room_id):
    """Filter the graph to focus on visited nodes and neighbors."""
    G = nx.Graph()
    visited_nodes = []
    unvisited_neighbors = []
    current_neighbors = []

    for room_id, name, connections_json, visited in data:
        connections = json.loads(connections_json)
        G.add_node(room_id, name=name, visited=visited)
        if visited:
            visited_nodes.append(room_id)
        if room_id == current_room_id:
            current_neighbors = connections  # Track neighbors of the current room
        for connection in connections:
            G.add_edge(room_id, connection)

    for neighbor in current_neighbors:
        if neighbor not in visited_nodes:
            unvisited_neighbors.append(neighbor)
    
    return G, visited_nodes, unvisited_neighbors

def visualize_dungeon_plotly(G, pos, visited_nodes, unvisited_neighbors, current_room_id):
    """Create an interactive Plotly visualization of the dungeon."""
    # Identify unseen nodes (not visited and not immediate neighbors)
    all_nodes = set(G.nodes())
    seen_nodes = set(visited_nodes + unvisited_neighbors)
    unseen_nodes = list(all_nodes - seen_nodes)

    # Build traces for Plotly
    traces = []

    # Edges
    edge_traces = []
        
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        if (edge[0] in visited_nodes and edge[1] in visited_nodes) or \
        (edge[0] in visited_nodes and edge[1] in unvisited_neighbors) or \
        (edge[1] in visited_nodes and edge[0] in unvisited_neighbors):
            # Edge is visible
            edge_color = "white"
            if (edge[0] in visited_nodes and edge[1] in unvisited_neighbors) or \
            (edge[1] in visited_nodes and edge[0] in unvisited_neighbors):
                line_dash = "dot"
            else:
                line_dash = "solid"
        else:
            # Edge is fully transparent
            edge_color = "rgba(255, 255, 255, 0)"
            line_dash = "solid"
        
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=1, color=edge_color, dash=line_dash),
            hoverinfo='none',
            mode='lines'
        ))
        
    traces.extend(edge_traces)

    # Visited nodes
    x_visited = [pos[node][0] for node in visited_nodes]
    y_visited = [pos[node][1] for node in visited_nodes]
    traces.append(go.Scatter(
        x=x_visited, y=y_visited,
        mode='markers',
        marker=dict(size=15, color='#b01414', symbol='circle'),
        name='Visited Rooms',
        text=[G.nodes[node]['name'] for node in visited_nodes],
        hoverinfo='text'
    ))

    # Immediate unvisited neighbors
    for visited_node in visited_nodes:
        for neighbor in G.neighbors(visited_node):
            if neighbor not in visited_nodes:
                unvisited_neighbors.append(neighbor)

    # Immediate unvisited neighbors
    x_unvisited = [pos[node][0] for node in unvisited_neighbors]
    y_unvisited = [pos[node][1] for node in unvisited_neighbors]
    traces.append(go.Scatter(
        x=x_unvisited, y=y_unvisited,
        mode='markers',
        marker=dict(size=12, color='rgba(255, 102, 0, 0.5)', symbol='circle'),
        name='Unvisited Rooms',
        text=[G.nodes[node]['name'] for node in unvisited_neighbors],
        hoverinfo='text'
    ))

    # Unseen nodes (fully transparent)
    x_unseen = [pos[node][0] for node in unseen_nodes]
    y_unseen = [pos[node][1] for node in unseen_nodes]
    traces.append(go.Scatter(
        x=x_unseen, y=y_unseen,
        mode='markers',
        marker=dict(size=12, color='rgba(0, 0, 0, 0)', symbol='circle'),
        name='Unseen Rooms',
        text=["Unseen Room"] * len(unseen_nodes),
        hoverinfo='none'  # No hover info for unseen rooms
    ))

    # Current node
    x_current = [pos[current_room_id][0]]
    y_current = [pos[current_room_id][1]]
    traces.append(go.Scatter(
        x=x_current, y=y_current,
        mode='markers',
        marker=dict(size=20, color='#f2f217', symbol='circle'),
        name='Current Room',
        text=[G.nodes[current_room_id]['name']],
        hoverinfo='text'
    ))

    # Layout for Plotly
    layout = go.Layout(
        title=" ",
        title_font=dict(color='white'),
        showlegend=True,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False)
    )

    fig = go.Figure(data=traces, layout=layout)
    return fig

class RoomDetails(BaseModel):
    id: int
    name: str
    description: str

class DungeonRoomInfo(BaseModel):
    current_room: RoomDetails
    neighbors: List[RoomDetails]

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
        hp INTEGER DEFAULT 10,
        attack INTEGER DEFAULT 3,
        alive BOOLEAN DEFAULT 1,
        FOREIGN KEY (room_id) REFERENCES rooms (id)
    )
    ''')

    # Example monster entries
    monsters = [
        (1, "Goblin", "A small, green creature with sharp teeth.", 2, 10, 3, 1),
        (2, "Skeleton Warrior", "A clattering skeleton armed with a rusty sword.", 3, 15, 5, 1),
    ]
    cursor.executemany('''
    INSERT OR IGNORE INTO monsters (id, name, description, room_id, hp, attack, alive) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', monsters)

    conn.commit()
    conn.close()

if st.session_state.first_run:
    st.session_state.first_run = False
    initialize_database()

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

    if not visited:
        # Generate names and descriptions for the current room and neighbors
        name, description = generate_room_details(room_id, neighbor_ids,client)
        cursor.execute("UPDATE rooms SET visited = 1 WHERE id = ?", (room_id,))
        conn.commit()

    cursor.execute("SELECT name, description, connections, visited FROM rooms WHERE id = ?", (room_id,))
    room_data = cursor.fetchone()

    # Fetch monster data
    cursor.execute("SELECT name, description, hp, alive FROM monsters WHERE room_id = ? AND alive = 1", (room_id,))
    monster_data = cursor.fetchone()

    if room_data:
        room_name, room_description, room_connections, visited = room_data
        text = f"---{room_name}---\n{room_description}"

        if monster_data:
            monster_name, monster_description, monster_hp, alive = monster_data
            text += f"\n\nYou see a {monster_name}: {monster_description} (HP: {monster_hp})"


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

def generate_room_details(room_id, neighbor_ids, client):
    """Generate room names and descriptions using OpenAI JSON mode."""
    # Query current room and neighboring room details
    conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, description FROM rooms WHERE id = ?", (room_id,))
    current_room_data = cursor.fetchone()

    cursor.execute("SELECT id, name, description FROM rooms WHERE id IN ({})".format(
        ",".join("?" * len(neighbor_ids))), neighbor_ids)
    neighbors = cursor.fetchall()

    # Format current room and neighbors for the AI prompt
    neighbors_for_ai = [
        {"id": r[0], "name": r[1] if r[1] else "Unknown", "description": r[2] if r[2] else "Undescribed"}
        for r in neighbors
    ]

    prompt = {
        "model": "gpt-4o-2024-08-06",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a dungeon master generating immersive room details for a text adventure game. "
                    "Given the current room and its neighbors, provide names and descriptions for each room. "
                    "Descriptions should hint at interconnections and an overarching story."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Current room: ID: {current_room_data[0]}, Name: {current_room_data[1] or 'Unknown'}, "
                    f"Description: {current_room_data[2] or 'Undescribed'}\n\n"
                    f"Neighbors:\n{json.dumps(neighbors_for_ai)}\n\n"
                    "Provide output in JSON format:\n"
                    "{'current_room': {'id': '', 'name': '', 'description': ''}, "
                    "'neighbors': [{'id': '', 'name': '', 'description': ''}, ...]}"
                ),
            },
        ],
    }

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



# %% Display current room
text, dirlist, codelist = get_room_description(st.session_state.current_room_id)

# %% UI Components
text_placeholder = st.empty()  # Main game text display

# Check for monsters in the current room
conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("SELECT id, name, hp, attack FROM monsters WHERE room_id = ? AND alive = 1", (st.session_state.current_room_id,))
monster = cursor.fetchone()
conn.close()

if monster:
    monster_id, monster_name, monster_hp, monster_attack = monster
    st.write(f"A wild {monster_name} appears! (HP: {monster_hp})")

    # Battle controls
    col1, col2, col3 = st.columns(3)
    if col1.button("Attack"):
        monster_hp -= random.randint(3, 6)  # Player attack
        if monster_hp <= 0:
            st.write(f"You defeated the {monster_name}!")
            conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE monsters SET alive = 0 WHERE id = ?", (monster_id,))
            conn.commit()
            conn.close()
            st.rerun()
        else:
            st.write(f"The {monster_name} has {monster_hp} HP left!")
            conn = sqlite3.connect("adventure_game.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE monsters SET hp = ? WHERE id = ?", (monster_hp, monster_id))
            conn.commit()
            conn.close()
    if col2.button("Defend"):
        st.write("You defend against the attack!")
    if col3.button("Flee"):
        st.session_state.current_room_id = st.session_state.previous_room_id
        st.rerun()
else:
    # Direction Buttons
    st.write("### Choose a direction:")
    cols = st.columns(len(dirlist) or 1)
    for i, d in enumerate(dirlist):
        if cols[i].button(d):
            st.session_state.previous_room_id = st.session_state.current_room_id
            st.session_state.current_room_id = codelist[i]
            st.rerun()  # Refresh the app with the new room

# Action Buttons
st.write("### Actions:")
col1, col2, col3 = st.columns(3)

# with col1:
#     if st.button("Attack!"):
#         text += "\nOw, what was that for?"
# with col2:
#     if st.button("Defend!"):
#         text += "\nBlocked!"
with col3:
    if st.button("Balloons!"):
        st.balloons()
        text += "\nHooray!"

# Update text area
with text_placeholder:
    st.text_area("text", value=text, height=150, disabled=True, label_visibility="collapsed")

data = fetch_dungeon_data()
G, pos = compute_dungeon_layout(data)
datasub = [(row[0], row[2]) for row in data]
pos = compute_pos(datasub)
G_filtered, visited_nodes, unvisited_neighbors = build_dungeon_graph(data, st.session_state.current_room_id)

fig = visualize_dungeon_plotly(G, pos, visited_nodes, unvisited_neighbors, st.session_state.current_room_id)
fig.update_layout(showlegend=False)
st.plotly_chart(fig, config = {'displayModeBar': False})

# Footer Text
st.write("The up and coming best game of 2022. - Everyone Ever")
