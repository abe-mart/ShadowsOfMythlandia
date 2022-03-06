import streamlit as st

st.title('Shadows of Mythlandia: The Forge and the Fire')

st.write('The up and coming best game of 2022. -Everyone Ever')

text = ""

col1, col2 = st.columns(2)

with col1:
  b1 = st.button('Attack!')

with col2:
  b2 = st.button('Ballons!')

if b1:
  text = "Ow, what was that for?"
  
if b2:
  text = 'Hooray!'
  st.balloons()
  
st.text_area('',value=text,height=10,disabled=True)
