import streamlit as st

def render_intro():
    st.subheader("📖 모임 소개")
    
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">🪐 북클럽 플래닛</div>
        <div class="hero-subtitle">느슨한 지식 교류 모임 Since 2017</div>
    </div>
    """, unsafe_allow_html=True)

    # 소개 인사말
    st.markdown("""
    책을 좋아하시는 분들과 같이 책도 읽고, 사람들과 이야기 나누며 지식을 넓혀봐요.<br/>
    저희 모임은 2017년부터 꾸준히 진행해온 독서 모임입니다.<br/>
    <b>책 속에서 찾는 소확행, 우리 함께 나눠봐요 많관부! ❤️</b>
    <br/><br/>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📔 모집대상")
        st.markdown("""
        - 📖 **책을 사랑하는 분들!**
        - 💡 이 책을 나 혼자서만 읽기 아깝다고 생각하시는 분들
        - 🎯 혹은 이번 기회에 독서습관을 길러야겠다고 생각하시는 분들
        - ✨ **별도의 나이제한 없이** 책을 사랑하는 분이라면 언제나 환영합니다!
        """)

        st.markdown("---")

        st.markdown("### 📗 모임 시간 및 장소")
        st.markdown("""
        저희는 주말에 모임을 가져요. 자주 오실 수 있는 모임으로 신청하시면 됩니다.<br/>
        • <b>✔ 토요일</b>: 강남역 인근 카페 / 14:00 ~ 16:30<br/>
        • <b>✔ 일요일</b>: 종각역 인근 카페 / 14:00 ~ 16:30
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 📓 활동기간")
        st.markdown("""
        저희 모임은 시즌별 운영으로 **2달을 1시즌**으로 운영합니다.<br/>
        ⭐⭐ <i>처음 오시면 오리엔테이션으로 간단히 모임 소개해 드립니다.</i>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 📕 모임 특징")
        st.markdown("""
        - 저희 모임은 대학생 외에도 취준생, 직장인 등 다양한 분들이 모입니다.
        - 모임의 평화를 위해 정치 및 종교에 대한 이야기는 자제해 주세요.
        - 기본적으로 자유책으로 모임이 진행됩니다. 심도 있는 토론을 위해 지정책도 있습니다.
        - 서로 존중하는 토론 문화를 위해 나이와 상관없이 존댓말을 사용해요.
        - 독서 모임 외에도 다양한 소모임과 영화벙 등이 있습니다.
        - 뒤풀이 참여는 자유롭게 진행합니다.
        - 이성을 만나려고 오시는 분도 자제 부탁드려요. 😅😅
        """)

        st.markdown("---")

        st.markdown("### 📒 예치금 안내")
        st.markdown("""
        시즌 활동기간을 통틀어 <b>20,000원</b>을 받습니다.<br/><br/>
        🎉 <b>열심히 참여하시면 예치금 100% 돌려드려요!</b><br/>
        • <b>첫 시즌</b>: 4회 출석 시 환급<br/>
        • <b>다음 시즌부터</b>: 3회 출석 시 환급
        """, unsafe_allow_html=True)

    st.markdown("<br/><hr style='margin: 20px 0;'/>", unsafe_allow_html=True)

    # 📸 플래닛 인스타그램 링크 버튼 (페이지 맨 하단)
    st.markdown("""
    <a href="https://www.instagram.com/bookclubplanet/" target="_blank" style="text-decoration: none;">
        <div style="background: linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045); padding: 14px 20px; border-radius: 12px; color: white; font-weight: bold; text-align: center; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 4px 14px rgba(253, 29, 29, 0.25); font-size: 1.05rem;">
            📸 <b>북클럽 플래닛 공식 인스타그램 구경하기</b> (@bookclubplanet) 🔗
        </div>
    </a>
    """, unsafe_allow_html=True)
