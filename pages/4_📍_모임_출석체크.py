import streamlit as st
from database import init_db
from views.attendance import render_attendance
from styles import apply_custom_css

st.set_page_config(page_title="모임 출석체크 | 북클럽 플래닛", page_icon="📍", layout="centered")
init_db()
apply_custom_css()

render_attendance()
