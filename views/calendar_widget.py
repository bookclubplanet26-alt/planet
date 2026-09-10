import calendar
from datetime import date
import streamlit as st

def generate_month_calendar_html(year, month, season_start, season_end, chuseok_dates):
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_days = cal.monthdatescalendar(year, month)
    
    html = []
    html.append('<div class="cal-month-card">')
    html.append(f'<div class="cal-month-title">{year}년 {month}월</div>')
    
    # Table header (일~토)
    html.append('<div class="cal-weekdays-row">')
    weekdays = [("일", "#E53935"), ("월", "#5D4037"), ("화", "#5D4037"), ("수", "#5D4037"), ("목", "#5D4037"), ("금", "#5D4037"), ("토", "#1E88E5")]
    for w, color in weekdays:
        html.append(f'<span style="color:{color};">{w}</span>')
    html.append('</div>')
    
    # Days grid
    html.append('<div class="cal-days-grid">')
    
    for week in month_days:
        for d in week:
            is_current_month = (d.month == month)
            day_str = str(d.day)
            
            if not is_current_month:
                # Dimmed cell (이전/다음 달 일자)
                html.append(f'<div class="cal-cell cal-cell-dimmed">{day_str}</div>')
                continue
                
            # 1. 추석 연휴 (9/26, 9/27) -> 빨간색 (모임 제외)
            if d in chuseok_dates:
                html.append(
                    f'<div class="cal-cell cal-cell-chuseok">'
                    f'<span class="cal-day-num">{day_str}</span>'
                    f'<span class="cal-badge-chuseok">추석</span>'
                    f'</div>'
                )
            # 2. 2609 시즌 정규 모임일 (토/일) -> 파란색
            elif season_start <= d <= season_end and d.weekday() in (5, 6): # 5=토, 6=일
                loc = "강남" if d.weekday() == 5 else "종각"
                html.append(
                    f'<div class="cal-cell cal-cell-meeting">'
                    f'<span class="cal-day-num">{day_str}</span>'
                    f'<span class="cal-badge-meeting">{loc}</span>'
                    f'</div>'
                )
            # 3. 비모임일 및 평일 -> 무색
            else:
                d_color = "#E53935" if d.weekday() == 6 else ("#1E88E5" if d.weekday() == 5 else "#2D2D2D")
                html.append(
                    f'<div class="cal-cell cal-cell-plain">'
                    f'<span style="color:{d_color};">{day_str}</span>'
                    f'</div>'
                )
    
    html.append('</div></div>')
    return "".join(html)

def render_season_calendar_2609():
    """
    2609 시즌(2026.09.12 ~ 2026.11.01) 달력 위젯
    - 토/일 모임일: 파란색
    - 추석 연휴(9/26, 9/27): 빨간색 (모임 제외)
    - 나머지 일자: 무색
    """
    season_start = date(2026, 9, 12)
    season_end = date(2026, 11, 1)
    chuseok_dates = [date(2026, 9, 26), date(2026, 9, 27)]

    # 범례 & 시즌 요약 안내 카드
    legend_html = (
        '<div class="cal-legend-card">'
        '<div style="font-weight:700; font-size:0.96rem; color:#3E2723; margin-bottom:8px;">'
        '🪐 <b>2609 시즌 일정표</b> <span style="font-size:0.85rem; color:#795548; font-weight:500;">(2026.09.12 ~ 2026.11.01, 총 8주)</span>'
        '</div>'
        '<div style="display:flex; flex-wrap:wrap; gap:10px; font-size:0.84rem; line-height:1.4;">'
        '  <div style="display:flex; align-items:center; gap:5px;">'
        '    <span class="cal-legend-badge" style="background:#E3F2FD; border:1.5px solid #1E88E5; color:#0D47A1; font-weight:700;">🟦 모임일</span>'
        '    <span><b>토(강남역) / 일(종각역)</b> 14:00~16:30</span>'
        '  </div>'
        '  <div style="display:flex; align-items:center; gap:5px;">'
        '    <span class="cal-legend-badge" style="background:#FFEBEE; border:1.5px solid #EF5350; color:#C62828; font-weight:700;">🟥 휴무</span>'
        '    <span><b>9/26(토), 9/27(일)</b> 추석 연휴</span>'
        '  </div>'
        '  <div style="display:flex; align-items:center; gap:5px;">'
        '    <span class="cal-legend-badge" style="background:#F7F7F7; border:1px solid #E0DCD3; color:#666;">⬜ 무색</span>'
        '    <span>평일 및 비모임일</span>'
        '  </div>'
        '</div>'
        '</div>'
    )
    st.markdown(legend_html, unsafe_allow_html=True)

    cal_9 = generate_month_calendar_html(2026, 9, season_start, season_end, chuseok_dates)
    cal_10 = generate_month_calendar_html(2026, 10, season_start, season_end, chuseok_dates)
    cal_11 = generate_month_calendar_html(2026, 11, season_start, season_end, chuseok_dates)

    tab_all, tab_9, tab_10, tab_11 = st.tabs(["🗓️ 3달 전체보기", "9월", "10월", "11월"])

    with tab_all:
        all_html = f'<div class="cal-months-container">{cal_9}{cal_10}{cal_11}</div>'
        st.markdown(all_html, unsafe_allow_html=True)

    with tab_9:
        st.markdown(f'<div style="max-width:380px; margin:0 auto;">{cal_9}</div>', unsafe_allow_html=True)

    with tab_10:
        st.markdown(f'<div style="max-width:380px; margin:0 auto;">{cal_10}</div>', unsafe_allow_html=True)

    with tab_11:
        st.markdown(f'<div style="max-width:380px; margin:0 auto;">{cal_11}</div>', unsafe_allow_html=True)
