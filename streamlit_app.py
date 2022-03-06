import streamlit as st

st.title('Shadows of Mythlandia: The Forge and the Fire')

st.write('The up and coming best game of 2022. -Everyone Ever')

text = ''

b1 = st.button('Attack!')

if b1:
  text = 'Ow, what was that for?'
  
st.text_area(value=text,height=10,disabled=True)
