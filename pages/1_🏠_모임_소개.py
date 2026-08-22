import streamlit as st
from database import init_db
from views.intro import render_intro
from styles import apply_custom_css

st.set_page_config(page_title="모임 소개 | 북클럽 플래닛", page_icon="📖", layout="wide")
init_db()
apply_custom_css()

render_intro()
