import streamlit as st

def render_register():
    st.subheader("👤 회원가입 및 문의")

    st.markdown("""
    <div class="club-card" style="border-left: 4px solid #FEE500; background-color: #FFFDF0; padding: 24px; text-align: center;">
        <h3 style="margin-top: 0; color: #3C1E1E;">💬 회원가입 및 문의</h3>
        <p style="font-size: 1.1rem; color: #3C1E1E; margin-bottom: 20px; line-height: 1.6;">
            북클럽 플래닛 회원가입 및 문의사항은 아래 카카오톡 오픈채팅 링크로 편하게 연락 주세요!
        </p>
        <a href="https://open.kakao.com/o/sWLBJTue" target="_blank" style="
            display: inline-block;
            background-color: #FEE500;
            color: #191919;
            font-weight: bold;
            font-size: 1.1rem;
            padding: 14px 28px;
            border-radius: 12px;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        ">
            👉 카카오톡 오픈채팅 문의하기 (클릭)
        </a>
    </div>
    """, unsafe_allow_html=True)
