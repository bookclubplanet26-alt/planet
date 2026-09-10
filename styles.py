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
    
    /* 모임 카드 제목 및 안내글 (다크모드 가독성 완벽 지원) */
    .meeting-card-title {
        font-size: 1.18rem;
        font-weight: 700;
        color: #1A1A1A;
        letter-spacing: -0.3px;
        line-height: 1.35;
    }
    .meeting-leader-badge {
        font-size: 0.92rem;
        color: #5D4037;
        margin-bottom: 6px;
    }
    .meeting-leader-badge span {
        background-color: #F0ECE1;
        color: #3E2723;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .meeting-desc-text {
        margin-top: 4px;
        line-height: 1.55;
        word-break: break-word;
        color: #2D2D2D;
    }
    .cal-legend-title {
        font-weight: 700;
        font-size: 0.96rem;
        color: #3E2723;
        margin-bottom: 8px;
    }

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
        .meeting-card-title {
            color: #FFFFFF !important;
        }
        .meeting-leader-badge {
            color: #D7CCC8 !important;
        }
        .meeting-leader-badge span {
            background-color: #2E2724 !important;
            color: #F5EFE6 !important;
        }
        .meeting-desc-text {
            color: #EDEDED !important;
        }
        .cal-legend-title {
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
    
    /* 인스타그램 링크 버튼 (방문 후 색상 변경 및 다크모드 반전 방지 - 순백색 고정) */
    a[href*="instagram.com"],
    a[href*="instagram.com"]:visited,
    a[href*="instagram.com"]:hover,
    a[href*="instagram.com"]:active,
    a[href*="instagram.com"] div,
    a[href*="instagram.com"] b,
    a[href*="instagram.com"] span {
        color: #FFFFFF !important;
        text-decoration: none !important;
    }
    
    /* 13. 2609 시즌 캘린더 스타일 */
    .cal-legend-card {
        background-color: #FAF8F5;
        border: 1px solid #ECE7E0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 12px;
    }
    .cal-legend-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.78rem;
    }
    .cal-months-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 12px;
        margin-top: 8px;
    }
    .cal-month-card {
        background-color: #FFFFFF;
        border: 1.5px solid #E2DDD5;
        border-radius: 12px;
        padding: 12px 10px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        box-sizing: border-box;
        width: 100%;
    }
    .cal-month-title {
        text-align: center;
        font-weight: 800;
        font-size: 1.02rem;
        color: #3E2723;
        margin-bottom: 8px;
    }
    .cal-weekdays-row {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        text-align: center;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #8D6E63;
    }
    .cal-days-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 3px;
        text-align: center;
    }
    .cal-cell {
        min-height: 40px;
        border-radius: 7px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-size: 0.82rem;
    }
    .cal-cell-dimmed {
        color: #D6D0C4 !important;
        font-size: 0.78rem;
    }
    .cal-cell-plain {
        padding: 4px 1px;
    }
    .cal-cell-meeting {
        background-color: #E3F2FD !important;
        border: 1.5px solid #1E88E5 !important;
        padding: 2px 1px;
        box-shadow: 0 1px 3px rgba(30, 136, 229, 0.15);
    }
    .cal-cell-meeting .cal-day-num {
        font-weight: 800;
        color: #0D47A1 !important;
        font-size: 0.86rem;
    }
    .cal-badge-meeting {
        font-size: 0.62rem;
        background-color: #1976D2;
        color: #FFFFFF !important;
        border-radius: 3px;
        padding: 1px 3px;
        margin-top: 1px;
        font-weight: 700;
        line-height: 1.1;
    }
    .cal-cell-chuseok {
        background-color: #FFEBEE !important;
        border: 1.5px solid #EF5350 !important;
        padding: 2px 1px;
    }
    .cal-cell-chuseok .cal-day-num {
        font-weight: 800;
        color: #C62828 !important;
        font-size: 0.86rem;
    }
    .cal-badge-chuseok {
        font-size: 0.62rem;
        background-color: #C62828;
        color: #FFFFFF !important;
        border-radius: 3px;
        padding: 1px 3px;
        margin-top: 1px;
        font-weight: 700;
        line-height: 1.1;
    }

    /* 캘린더 다크모드 대응 */

    @media (prefers-color-scheme: dark) {
        .cal-legend-card {
            background-color: #1E1C1A !important;
            border-color: #383430 !important;
        }
        .cal-month-card {
            background-color: #201E1B !important;
            border-color: #383430 !important;
        }
        .cal-month-title {
            color: #FFFFFF !important;
        }
        .cal-cell-meeting {
            background-color: #0D2B45 !important;
            border-color: #1E88E5 !important;
        }
        .cal-cell-meeting .cal-day-num {
            color: #90CAF9 !important;
        }
        .cal-cell-chuseok {
            background-color: #3B1616 !important;
            border-color: #E53935 !important;
        }
        .cal-cell-chuseok .cal-day-num {
            color: #FF8A80 !important;
        }
    }
    </style>
    ''', unsafe_allow_html=True)
