import os
import base64
import streamlit as st

def render_register():
    st.subheader("👤 회원가입 및 문의")

    kakao_channel_url = "https://pf.kakao.com/_QjxkFX"

    qr_filename = "플래닛 비즈니스 계정 qrcode_120.png"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    qr_path = os.path.join(base_dir, qr_filename)
    if not os.path.exists(qr_path):
        qr_path = os.path.join(os.getcwd(), qr_filename)

    qr_img_tag = ""
    if os.path.exists(qr_path):
        try:
            with open(qr_path, "rb") as f:
                qr_b64 = base64.b64encode(f.read()).decode("utf-8")
            qr_img_tag = f"""
            <div style="margin: 16px auto 20px auto; display: inline-block; padding: 12px; background: #FFFFFF; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #EAE5D9;">
                <img src="data:image/png;base64,{qr_b64}" width="160" height="160" style="display: block; border-radius: 8px;" alt="카카오톡 채널 QR코드"/>
                <div style="font-size: 0.85rem; color: #795548; font-weight: 600; margin-top: 8px;">스마트폰으로 QR 스캔</div>
            </div>
            """
        except Exception:
            qr_img_tag = ""

    st.markdown(f"""
    <div class="club-card" style="border-left: 4px solid #FEE500; background-color: #FFFDF0; padding: 32px 24px; text-align: center; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); max-width: 520px; margin: 0 auto;">
        <h3 style="margin-top: 0; color: #3C1E1E; font-size: 1.4rem;">💬 회원가입 및 문의</h3>
        <p style="font-size: 1.05rem; color: #3C1E1E; margin-bottom: 16px; line-height: 1.6;">
            북클럽 플래닛 회원가입 및 각종 문의사항은<br/>
            공식 <b>카카오톡 채널</b>을 통해 편하게 연락 주세요!
        </p>
        {qr_img_tag}
        <div style="margin: 16px 0;">
            <a href="{kakao_channel_url}" target="_blank" rel="noopener noreferrer" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background-color: #FEE500;
                color: #191919 !important;
                font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 1.15rem;
                font-weight: 700;
                padding: 14px 28px;
                border-radius: 14px;
                text-decoration: none !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.08);
                border: 1px solid #F0D800;
                transition: transform 0.15s ease, background-color 0.15s ease;
            ">
                💬 <span>카카오톡 채널로 문의하기</span> ↗
            </a>
        </div>
        <p style="font-size: 0.9rem; color: #8D6E63; margin-top: 16px; margin-bottom: 0;">
            * 버튼을 누르거나 스마트폰 카메라로 QR코드를 스캔하시면 1:1 채팅으로 바로 연결됩니다.
        </p>
    </div>
    """, unsafe_allow_html=True)


