import streamlit as st

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
if 'FirstRun' not in st.session_state:
    st.session_state['FirstRun'] = True

# %% Save a spot for the main game text display
text_placeholder = st.empty() # Fill this in after processing buttons

# %% Buttons
col1, col2, col3 = st.columns([0.11,0.12,0.87])

with col1:
  attack = st.button('Attack!')
  
with col2:
  defend = st.button('Defend!')

with col3:
  ballon = st.button('Ballons!')
      
st.write('The up and coming best game of 2022. -Everyone Ever')

# %% Process player inputs
text = ""
if attack:
    text = "Ow, what was that for?"
if defend:
    text = "Blocked?"
if ballon:
    st.balloons()
    text = "Hooray!"
if st.session_state['FirstRun']:
    text = 'The door of the forbidden mountain looms before you.'

# %% Update main display
with text_placeholder:
    st.text_area('',value=text,height=10,disabled=True)
    
# %% Additional logic
st.session_state['FirstRun'] = False