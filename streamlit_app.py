import streamlit as st
import glob
import json
import random
import os

# Hide menu in production
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

# Logo
st.image('Images/Shadows.png',use_column_width=True)

# %% Persistent variables go here
# if 'FirstRun' not in st.session_state:
#     st.session_state['FirstRun'] = True
    
if 'folder' not in st.session_state:
    st.session_state['folder'] = random.choice(glob.glob("Procedural/Rooms/*"))
folder = st.session_state['folder']
    
if 'room' not in st.session_state:
    st.session_state['room'] = random.choice(glob.glob(folder+'/*'))
room = st.session_state['room']

# %% Get description of current room
with open(room) as json_data:
    room_data = json.load(json_data)
text = ""
text += '---'+room_data['IdentificationComponent']['m_name']+'---'
text += '\n'
text += room_data['RoomComponent']['m_description']
dirlist = []
codelist = []
for door in room_data['m_doors']:
    dirlist.append(door['dir'])
    codelist.append(door['code'])

# %% Save a spot for the main game text display
text_placeholder = st.empty() # Fill this in after processing buttons

# %% Buttons
# Direction buttons
cols = st.columns(8)
d_button = []
for i, d in enumerate(dirlist):
    k = cols[i].button(d)
    d_button.append(k)
    
col1, col2, col3 = st.columns([0.12,0.12,0.5])

# if st.session_state['FirstRun']:
#     st.button('Enter the mountain')
#     attack = False
#     defend = False
#     ballon = False
    
# else:
with col1:
  attack = st.button('Attack!')
  
with col2:
  defend = st.button('Defend!')

with col3:
  ballon = st.button('Ballons!')
      
      
st.write('The up and coming best game of 2022. -Everyone Ever')

# %% Process player inputs
if attack:
    text = text + "\nOw, what was that for?"
if defend:
    text = "Blocked?"
if ballon:
    st.balloons()
    text = "Hooray!"
# if st.session_state['FirstRun']:
#     text = 'The door of the forbidden mountain looms before you.'
    
for i, d in enumerate(dirlist):
    if d_button[i]:
        newCode = codelist[i]
        st.session_state['room'] = os.path.join(folder,newCode+'.json')
        
# %% Update main display
with text_placeholder:
    st.text_area('',value=text,height=10,disabled=True)
    
# %% Additional logic
st.session_state['FirstRun'] = False