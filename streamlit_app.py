import streamlit as st

st.image('Images/Shadows.png',use_column_width=True)

# %% Persistent variables

# Initialize text for text box
if 'text' not in st.session_state:
    st.session_state['text'] = ""
    
# %% Process player inputs
    
def process_inputs():
    text = ""
    if st.session_state.attack:
        text = "Ow, what was that for?"
    if st.session_state.ballon:
        st.balloons()
        text = "Hooray!"
    st.session_state['text'] = text
    
# %% Main text area for game display
st.text_area('',value=st.session_state['text'],height=10,disabled=True)

# %% Buttons
col1, col2 = st.columns([0.1,0.9])

with col1:
  st.button('Attack!',key='attack',on_click=process_inputs)

with col2:
  st.button('Ballons!',key='ballon',on_click=process_inputs)
      
st.write('The up and coming best game of 2022. -Everyone Ever')