import calendar
from datetime import date
import streamlit as st

def generate_month_calendar_html(year, month, season_start, season_end):
    # 달력의 시작을 월요일(calendar.MONDAY)로 설정
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdatescalendar(year, month)
    
    html = []
    html.append('<div class="cal-month-card">')
    html.append(f'<div class="cal-month-title">{year}년 {month}월</div>')
    
    # 요일 헤더 (월~일 순서)
    html.append('<div class="cal-weekdays-row">')
    weekdays = [
        ("월", "#5D4037"), 
        ("화", "#5D4037"), 
        ("수", "#5D4037"), 
        ("목", "#5D4037"), 
        ("금", "#5D4037"), 
        ("토", "#1E88E5"), 
        ("일", "#E53935")
    ]
    for w, color in weekdays:
        html.append(f'<span style="color:{color};">{w}</span>')
    html.append('</div>')
    
    # 날짜 그리드
    html.append('<div class="cal-days-grid">')
    
    for week in month_days:
        for d in week:
            is_current_month = (d.month == month)
            day_str = str(d.day)
            
            if not is_current_month:
                # 이전/다음 달 날짜 (흐림)
                html.append(f'<div class="cal-cell cal-cell-dimmed">{day_str}</div>')
                continue
                
            # 2609 시즌 정규 모임일 (토/일) -> 파란색 (제외일 없이 모두 인정)
            if season_start <= d <= season_end and d.weekday() in (5, 6): # 5=토, 6=일
                loc = "강남" if d.weekday() == 5 else "종각"
                html.append(
                    f'<div class="cal-cell cal-cell-meeting">'
                    f'<span class="cal-day-num">{day_str}</span>'
                    f'<span class="cal-badge-meeting">{loc}</span>'
                    f'</div>'
                )
            # 비모임일 및 평일 -> 무색
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
    2609 시즌(2026.09.05 ~ 2026.11.01) 달력 위젯
    - 월요일 시작 (월~일)
    - 9/5 ~ 11/1 사이 모든 토/일 모임일: 파란색
    - 평일: 무색
    """
    season_start = date(2026, 9, 5)
    season_end = date(2026, 11, 1)

    # 깔끔한 1줄 시즌 안내
    st.caption("🪐 **2609 시즌:** 2026.09.05(토) ~ 2026.11.01(일)")

    cal_9 = generate_month_calendar_html(2026, 9, season_start, season_end)
    cal_10 = generate_month_calendar_html(2026, 10, season_start, season_end)
    cal_11 = generate_month_calendar_html(2026, 11, season_start, season_end)

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
