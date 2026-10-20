import streamlit as st

def render_register():
    st.subheader("👤 회원가입 및 문의")

    kakao_channel_url = "https://pf.kakao.com/_QjxkFX"
    qr_b64 = "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"

    st.markdown(f"""
    <div class="club-card" style="border-left: 4px solid #FEE500; background-color: #FFFDF0; padding: 32px 24px; text-align: center; border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); max-width: 520px; margin: 0 auto;">
        <h3 style="margin-top: 0; color: #3C1E1E; font-size: 1.4rem;">💬 회원가입 및 문의</h3>
        <p style="font-size: 1.05rem; color: #3C1E1E; margin-bottom: 16px; line-height: 1.6;">
            북클럽 플래닛 회원가입 및 각종 문의사항은<br/>
            공식 <b>카카오톡 채널</b>을 통해 편하게 연락 주세요!
        </p>
        <div style="margin: 16px auto 20px auto; display: inline-block; padding: 12px; background: #FFFFFF; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #EAE5D9;">
            <img src="data:image/png;base64,{qr_b64}" width="160" height="160" style="display: block; border-radius: 8px;" alt="카카오톡 채널 QR코드"/>
            <div style="font-size: 0.85rem; color: #795548; font-weight: 600; margin-top: 8px;">스마트폰으로 QR 스캔</div>
        </div>
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



