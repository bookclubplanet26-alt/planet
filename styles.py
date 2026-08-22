import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    /* 모바일 반응형 padding 조정 */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 900px;
    }

    /* 사이드바 접기/열기 버튼 활성화 */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        width: auto !important;
        height: auto !important;
    }

    /* 배경 및 타이틀 스타일링 */
    .main {
        background-color: #FAF8F5;
    }

    /* 모바일 메뉴 홈 카드 버튼 */
    .menu-card {
        background-color: #FFFFFF;
        border: 2px solid #EAE5D9;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }
    
    .menu-card:hover {
        border-color: #8D6E63;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(141, 110, 99, 0.15);
    }

    .menu-icon {
        font-size: 2.2rem;
        margin-bottom: 8px;
    }

    .menu-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #3E2723;
        margin-bottom: 4px;
    }

    .menu-desc {
        font-size: 0.9rem;
        color: #6D4C41;
        line-height: 1.4;
    }

    /* 일반 카드 컨테이너 */
    .club-card {
        background-color: #FFFFFF;
        color: #262626;
        border: 1px solid #EAE5D9;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.03);
    }

    /* 다크모드 대처 */
    @media (prefers-color-scheme: dark) {
        .main {
            background-color: transparent;
        }
        .club-card {
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: inherit !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }
        .menu-card {
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }
        .menu-title {
            color: #F5EFE6 !important;
        }
        .menu-desc {
            color: #D7CCC8 !important;
        }
    }

    /* 배지 스타일 */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .status-approved {
        background-color: #E8F5E9;
        color: #2E7D32;
        border: 1px solid #C8E6C9;
    }
    .status-pending {
        background-color: #FFF8E1;
        color: #F57F17;
        border: 1px solid #FFE082;
    }
    .status-deducted {
        background-color: #FFEBEE;
        color: #C62828;
        border: 1px solid #FFCDD2;
    }

    /* 히어로 섹션 */
    .hero-box {
        background: linear-gradient(135deg, #4A3525 0%, #6D4C41 100%);
        color: #FFFFFF;
        padding: 20px 16px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 6px 16px rgba(74, 53, 37, 0.15);
        text-align: center;
    }

    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        color: #FFF8E7;
    }

    /* 버튼 스타일 (크고 깨끗한 모바일 터치 버튼) */
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.05rem;
        padding: 14px 20px;
        min-height: 54px;
        border: 1px solid #E0DCD3;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-bottom: 6px;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        border-color: #8D6E63;
        background-color: #F5EFE6;
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)
