import networkx as nx
import plotly.graph_objects as go
import streamlit as st
import sqlite3
import json

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
        marker=dict(size=12, color='rgba(255, 102, 0, 0.5)', symbol='circle-open'),
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

def build_dungeon_map():
    data = fetch_dungeon_data()
    G, pos = compute_dungeon_layout(data)
    datasub = [(row[0], row[2]) for row in data]
    pos = compute_pos(datasub)
    G_filtered, visited_nodes, unvisited_neighbors = build_dungeon_graph(data, st.session_state.current_room_id)

    fig = visualize_dungeon_plotly(G, pos, visited_nodes, unvisited_neighbors, st.session_state.current_room_id)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, config = {'displayModeBar': False})
