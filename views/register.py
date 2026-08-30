import streamlit as st
import os
import base64

def render_register():
    st.subheader("👤 회원가입 및 문의")

    img_path = os.path.join(os.path.dirname(__file__), "..", "kakao_qr.png")
    img_html = ""
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
            img_html = f'<div style="margin-top: 20px; text-align: center;"><img src="data:image/png;base64,{b64_data}" style="max-width: 260px; width: 100%; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" /></div>'

    st.markdown(f"""
    <div class="club-card" style="border-left: 4px solid #FEE500; background-color: #FFFDF0; padding: 28px 24px; text-align: center; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
        <h3 style="margin-top: 0; color: #3C1E1E; font-size: 1.4rem;">💬 회원가입 및 문의</h3>
        <p style="font-size: 1.05rem; color: #3C1E1E; margin-bottom: 20px; line-height: 1.6;">
            북클럽 플래닛 회원가입 및 문의사항은 아래 카카오톡 오픈채팅 링크 또는 QR 코드를 통해 편하게 연락 주세요! (현생이슈로 좀 늦을 수 있어요ㅠ)
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
        {img_html}
    </div>
    """, unsafe_allow_html=True)
