import streamlit as st
from database import init_db
from views.bookshelf import render_bookshelf
from styles import apply_custom_css

st.set_page_config(page_title="나의 서재 | 북클럽 플래닛", page_icon="📚", layout="centered")
init_db()
apply_custom_css()

render_bookshelf()
