import streamlit as st
from database import init_db
from styles import apply_custom_css

# 뷰 모듈 임포트
from views.intro import render_intro
from views.register import render_register
from views.schedule import render_schedule
from views.attendance import render_attendance
from views.bookshelf import render_bookshelf

# 기본 설정
st.set_page_config(
    page_title="북클럽 플래닛",
    page_icon="🪐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# DB 및 스타일 초기화
init_db()
apply_custom_css()

# 세션 상태 초기화 (메인 메뉴 controller)
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# 함수: 메인 메뉴로 돌아가기
def go_to_home():
    st.session_state.current_page = "home"
    st.rerun()

# 서브 페이지일 경우 상단에 '⬅️ 메인 메뉴로 돌아가기' 바 표시
if st.session_state.current_page != "home":
    col_nav_left, col_nav_right = st.columns([1, 2])
    with col_nav_left:
        if st.button("⬅️ 메인 메뉴로", key="top_back_home_btn", use_container_width=True):
            go_to_home()
    with col_nav_right:
        st.markdown("<div style='text-align:right; font-weight:bold; color:#795548; padding-top:6px;'>🪐 북클럽 플래닛</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 8px 0 16px 0; border: 0; border-top: 1px solid #EAE5D9;'/>", unsafe_allow_html=True)

# 페이지 라우팅
page = st.session_state.current_page

if page == "home":
    # 🏠 첫페이지 (Minimalist Mobile Main Menu)
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">🪐 북클럽 플래닛</div>
    </div>
    """, unsafe_allow_html=True)

    # 1. 모임 소개 버튼
    if st.button("🏠 모임 소개", key="btn_nav_intro", use_container_width=True):
        st.session_state.current_page = "intro"
        st.rerun()

    # 2. 회원가입 및 각종 문의 버튼
    if st.button("👤 회원가입 및 문의", key="btn_nav_reg", use_container_width=True):
        st.session_state.current_page = "register"
        st.rerun()

    # 3. 모임 일정 & 신청 버튼
    if st.button("📅 모임 일정 & 신청", key="btn_nav_sch", use_container_width=True):
        st.session_state.current_page = "schedule"
        st.rerun()

    # 4. 모임 출석체크 버튼
    if st.button("📍 모임 출석체크", key="btn_nav_att", use_container_width=True):
        st.session_state.current_page = "attendance"
        st.rerun()

    # 5. 나의 서재 버튼
    if st.button("📚 나의 서재 (My Book Planet)", key="btn_nav_bs", use_container_width=True):
        st.session_state.current_page = "bookshelf"
        st.rerun()

elif page == "intro":
    render_intro()
elif page == "register":
    render_register()
elif page == "schedule":
    render_schedule()
elif page == "attendance":
    render_attendance()
elif page == "bookshelf":
    render_bookshelf()

# 서브 페이지 하단에도 메인 메뉴로 돌아가기 버튼 배치
if st.session_state.current_page != "home":
    st.markdown("<br/><hr style='border: 0; border-top: 1px dashed #DDD;'/>", unsafe_allow_html=True)
    if st.button("⬅️ 메인 메뉴로 돌아가기", key="bottom_back_home_btn", use_container_width=True):
        go_to_home()
