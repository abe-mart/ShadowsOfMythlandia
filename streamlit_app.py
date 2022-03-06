import streamlit as st

st.title('Shadows of Mythlandia: The Forge and the Fire')

st.write('The up and coming best game of 2022. -Everyone Ever')

text = ""

b1 = st.button('Attack!')

b2 = st.button('Snow?')

b3 = st.button('Ballons!')

if b1:
  text = "Ow, what was that for?"
  
if b2:
  text = 'Let it snow, let it snow'
  st.snow()
  
if b3:
  text = 'Hooray!'
  st.balloons()
  
st.text_area('',value=text,height=10,disabled=True)
