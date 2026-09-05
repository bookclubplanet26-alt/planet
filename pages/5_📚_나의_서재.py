import streamlit as st
from database import init_db
from views.bookshelf import render_bookshelf
from styles import apply_custom_css

st.set_page_config(page_title="나의 서재 | 북클럽 플래닛", page_icon="📚", layout="centered")
init_db()
apply_custom_css()

col_nav_left, col_nav_right = st.columns([1, 2])
with col_nav_left:
    if st.button("⬅️ 메인 메뉴로", key="p5_top_back_home_btn", use_container_width=True):
        st.session_state.current_page = "home"
        try:
            st.switch_page("app.py")
        except Exception:
            st.rerun()
with col_nav_right:
    st.markdown("<div style='text-align:right; font-weight:bold; color:#795548; padding-top:6px;'>🪐 북클럽 플래닛</div>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 8px 0 16px 0; border: 0; border-top: 1px solid #EAE5D9;'/>", unsafe_allow_html=True)

render_bookshelf()

st.markdown("<br/><hr style='border: 0; border-top: 1px dashed #DDD;'/>", unsafe_allow_html=True)
if st.button("⬅️ 메인 메뉴로 돌아가기", key="p5_bottom_back_home_btn", use_container_width=True):
    st.session_state.current_page = "home"
    try:
        st.switch_page("app.py")
    except Exception:
        st.rerun()
