import streamlit as st

def apply_custom_css():
    st.markdown('''
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    /* 1. 모바일 반응형 여백 (컴팩트 최적화) */
    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 860px;
    }

    /* 사이드바 접기/열기 버튼 활성화 */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        width: auto !important;
        height: auto !important;
    }

    /* 2. 글로벌 배경 및 베이스 컬러 (절제된 웜 뉴트럴 톤) */
    .main {
        background-color: #FAF8F5;
    }

    /* 3. 히어로 헤더 섹션 (인위적 그라디언트 걷어내고 모던 플랫 서페이스 적용) */
    .hero-box {
        background-color: #3E2723;
        color: #FFFFFF;
        padding: 18px 20px;
        border-radius: 14px;
        margin-bottom: 18px;
        border: 1px solid #2B1B18;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
        text-align: center;
    }

    .hero-title {
        font-size: 1.65rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: -0.4px;
        line-height: 1.25;
    }

    .hero-subtitle {
        font-size: 0.88rem;
        font-weight: 500;
        color: #D7CCC8;
        margin-top: 6px;
        letter-spacing: -0.2px;
    }

    /* 4. 모바일 메뉴 홈 카드 버튼 (고대비 및 정돈된 테두리) */
    .menu-card {
        background-color: #FFFFFF;
        border: 1.5px solid #E0DCD3;
        border-radius: 14px;
        padding: 18px 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        cursor: pointer;
        transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    }
    
    .menu-card:hover {
        border-color: #6D4C41;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(62, 39, 35, 0.1);
    }

    .menu-icon {
        font-size: 2rem;
        margin-bottom: 6px;
    }

    .menu-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 4px;
        letter-spacing: -0.3px;
    }

    .menu-desc {
        font-size: 0.9rem;
        color: #4E342E;
        line-height: 1.45;
        letter-spacing: -0.2px;
    }

    /* 5. 일반 카드 컨테이너 */
    .club-card {
        background-color: #FFFFFF;
        color: #1E1E1E;
        border: 1px solid #DFD9CF;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }

    /* 6. 모임 카드 컨테이너 스타일 (st.container(border=True)) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        background-color: #FFFFFF !important;
        border: 1.5px solid #E2DDD5 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
        padding: 16px !important;
        margin-bottom: 14px !important;
    }

    /* 7. 모임 정보 행 (모바일 야외 시인성 및 WCAG 4.5:1 이상 고대비 최적화) */
    .meeting-meta-box {
        margin: 10px 0;
        padding: 10px 14px;
        background-color: #F9F8F6;
        border-radius: 10px;
        border: 1px solid #ECE7E0;
    }
    .meeting-meta-item {
        font-size: 0.96rem;
        line-height: 1.65;
        color: #1E1E1E;
        margin-bottom: 4px;
        letter-spacing: -0.2px;
    }
    .meta-strong {
        font-weight: 700;
        color: #000000;
    }

    /* 8. 컴팩트 상태 배지 (Status Chip - 채도 정돈 및 텍스트 시인성 향상) */
    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: -0.2px;
        line-height: 1.2;
    }
    .chip-available {
        background-color: #E8F5E9;
        color: #1B5E20;
        border: 1px solid #81C784;
    }
    .chip-full {
        background-color: #FFEBEE;
        color: #B71C1C;
        border: 1px solid #E57373;
    }
    .chip-wait {
        background-color: #FFF3E0;
        color: #C65102;
        border: 1px solid #FFB74D;
    }
    .chip-ended {
        background-color: #EEEEEE;
        color: #424242;
        border: 1px solid #BDBDBD;
    }

    /* 9. 기본 버튼 스타일 (크고 단정한 모바일 터치 타겟) */
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.02rem;
        padding: 12px 18px;
        min-height: 52px;
        background-color: #FFFFFF;
        color: #1A1A1A;
        border: 1.5px solid #D6D0C4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        margin-bottom: 6px;
        transition: all 0.15s ease;
    }
    
    .stButton>button:hover {
        border-color: #6D4C41;
        background-color: #F7F5F0;
        color: #3E2723;
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
    }

    

    /* 10. 카카오톡 링크 버튼 */
    .kakao-link-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #FEE500;
        color: #1E1E1E !important;
        padding: 9px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.92rem;
        text-decoration: none !important;
        margin-top: 6px;
        border: 1px solid #FBC02D;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.15s ease, background-color 0.15s ease;
    }
    .kakao-link-btn:hover {
        transform: translateY(-1px);
        background-color: #FDD835;
    }

    /* 11. Selectbox 텍스트 줄바꿈 보장 */
    div[data-baseweb="select"] div {
        white-space: normal !important;
        word-break: break-word !important;
    }
    li[role="option"] div {
        white-space: normal !important;
        word-break: break-word !important;
    }

    /* 12. 다크모드 대응 완성도 제고

     (눈부심 방지 및 반전 시 가독성 보장) */
    @media (prefers-color-scheme: dark) {
        .main {
            background-color: #161513 !important;
        }
        .hero-box {
            background-color: #271E1B !important;
            border-color: #483832 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important;
        }
        .hero-title {
            color: #FFFFFF !important;
        }
        .hero-subtitle {
            color: #BCAAA4 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #201E1B !important;
            border-color: #383430 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important;
        }
        .meeting-meta-box {
            background-color: #1A1816 !important;
            border-color: #2F2B27 !important;
        }
        .meeting-meta-item {
            color: #EDEDED !important;
        }
        .meta-strong {
            color: #FFFFFF !important;
        }
        .menu-card {
            background-color: #201E1B !important;
            border-color: #383430 !important;
        }
        .menu-title {
            color: #FFFFFF !important;
        }
        .menu-desc {
            color: #D7CCC8 !important;
        }
        .club-card {
            background-color: #201E1B !important;
            border-color: #383430 !important;
            color: #EDEDED !important;
        }
        .stButton>button {
            background-color: #242220 !important;
            color: #F5EFE6 !important;
            border-color: #3E3A36 !important;
        }
        .stButton>button:hover {
            background-color: #33302C !important;
            border-color: #8D6E63 !important;
            color: #FFFFFF !important;
        }
        .chip-available {
            background-color: #152E19 !important;
            color: #81C784 !important;
            border-color: #2E7D32 !important;
        }
        .chip-full {
            background-color: #351616 !important;
            color: #E57373 !important;
            border-color: #C62828 !important;
        }
        .chip-wait {
            background-color: #362214 !important;
            color: #FFB74D !important;
            border-color: #EF6C00 !important;
        }
        .chip-ended {
            background-color: #262626 !important;
            color: #9E9E9E !important;
            border-color: #424242 !important;
        }
    }
    </style>
    ''', unsafe_allow_html=True)
