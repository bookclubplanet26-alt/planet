import calendar
from datetime import date
import streamlit as st
from services.config import get_current_kst

def generate_month_calendar_html(year, month, season_start, season_end, chuseok_dates=None):
    if chuseok_dates is None:
        chuseok_dates = []
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
                
            # 1. 추석 연휴 (9/26, 9/27) -> 빨간색 (연휴 휴무 표시)
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
    2609 시즌(2026.09.05 ~ 2026.11.01) 달력 위젯
    - 월요일 시작 (월~일)
    - 9/5 ~ 11/1 사이 토/일 모임일: 파란색
    - 추석 연휴(9/26, 9/27): 빨간색 (휴무 표시)
    - 평일: 무색
    """
    season_start = date(2026, 9, 5)
    season_end = date(2026, 11, 1)
    chuseok_dates = [date(2026, 9, 26), date(2026, 9, 27)]

    # 깔끔한 1줄 시즌 안내
    st.caption("🪐 **2609 시즌:** 2026.09.05(토) ~ 2026.11.01(일)")

    now_kst = get_current_kst()
    cur_ym = (now_kst.year, now_kst.month)

    candidate_months = [(2026, 9), (2026, 10), (2026, 11)]
    active_months = [(y, m) for (y, m) in candidate_months if (y, m) >= cur_ym]
    if not active_months:
        active_months = [candidate_months[-1]]

    month_cals = [(m, generate_month_calendar_html(y, m, season_start, season_end, chuseok_dates)) for y, m in active_months]
    tab_titles = ["🗓️ 전체보기"] + [f"{m}월" for m, _ in month_cals]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        all_html = f'<div class="cal-months-container">{"".join([c for _, c in month_cals])}</div>'
        st.markdown(all_html, unsafe_allow_html=True)

    for idx, (m, c_html) in enumerate(month_cals, start=1):
        with tabs[idx]:
            st.markdown(f'<div style="max-width:380px; margin:0 auto;">{c_html}</div>', unsafe_allow_html=True)

def render_season_calendar_2610():
    """
    2610 시즌(2026.10.03 ~ 2026.11.29) 달력 위젯
    - 월요일 시작 (월~일)
    - 10/3 ~ 11/29 사이 토/일 정규 모임일: 파란색 (토=강남, 일=종각)
    - 평일: 무색
    """
    season_start = date(2026, 10, 3)
    season_end = date(2026, 11, 29)

    # 깔끔한 1줄 시즌 안내
    st.caption("🪐 **2610 시즌:** 2026.10.03(토) ~ 2026.11.29(일)")

    now_kst = get_current_kst()
    cur_ym = (now_kst.year, now_kst.month)

    candidate_months = [(2026, 10), (2026, 11)]
    active_months = [(y, m) for (y, m) in candidate_months if (y, m) >= cur_ym]
    if not active_months:
        active_months = candidate_months

    month_cals = [(m, generate_month_calendar_html(y, m, season_start, season_end)) for y, m in active_months]
    tab_titles = ["🗓️ 전체보기"] + [f"{m}월" for m, _ in month_cals]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        all_html = f'<div class="cal-months-container">{"".join([c for _, c in month_cals])}</div>'
        st.markdown(all_html, unsafe_allow_html=True)

    for idx, (m, c_html) in enumerate(month_cals, start=1):
        with tabs[idx]:
            st.markdown(f'<div style="max-width:380px; margin:0 auto;">{c_html}</div>', unsafe_allow_html=True)

import html

def _parse_meeting_date(date_val):
    if not date_val:
        return None
    s = str(date_val).strip()[:10].replace('.', '-').replace('/', '-')
    try:
        parts = s.split('-')
        if len(parts) == 3 and len(parts[0]) == 4:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        pass
    return None

def generate_submeeting_calendar_html(year, month, events_by_date):
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdatescalendar(year, month)
    
    html_out = []
    html_out.append('<div class="cal-month-card">')
    html_out.append(f'<div class="cal-month-title">{year}년 {month}월</div>')
    
    # 요일 헤더 (월~일 순서)
    html_out.append('<div class="cal-weekdays-row">')
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
        html_out.append(f'<span style="color:{color};">{w}</span>')
    html_out.append('</div>')
    
    # 날짜 그리드
    html_out.append('<div class="cal-days-grid">')
    
    for week in month_days:
        for d in week:
            is_current_month = (d.month == month)
            day_str = str(d.day)
            
            if not is_current_month:
                html_out.append(f'<div class="cal-cell cal-cell-dimmed">{day_str}</div>')
                continue

            events = events_by_date.get(d, [])
            d_color = "#E53935" if d.weekday() == 6 else ("#1E88E5" if d.weekday() == 5 else "#2D2D2D")

            if events:
                emojis = "".join([e['emoji'] for e in events[:3]])
                tooltip_items = [f"[{e['type_name']}] {e['title']}" for e in events]
                safe_tooltip = html.escape(f"{d.month}월 {d.day}일: " + ", ".join(tooltip_items), quote=True)
                html_out.append(
                    f'<div class="cal-cell cal-cell-submeeting" title="{safe_tooltip}">'
                    f'<span class="cal-day-num" style="color:{d_color}; font-weight:700;">{day_str}</span>'
                    f'<span class="cal-emoji-row">{emojis}</span>'
                    f'</div>'
                )
            else:
                html_out.append(
                    f'<div class="cal-cell cal-cell-plain">'
                    f'<span style="color:{d_color};">{day_str}</span>'
                    f'</div>'
                )
    
    html_out.append('</div></div>')
    return "".join(html_out)

def render_submeeting_calendar(meetings=None):
    """
    지정책(📕) 및 소모임/벙(☕) 일정 캘린더
    - 날짜 아래에 해당 일자에 개설된 모임 이모지(📕, ☕)를 표시
    """
    if meetings is None:
        meetings = []

    events_by_date = {}
    for m in meetings:
        m_dict = dict(m) if isinstance(m, dict) else getattr(m, '__dict__', {})
        m_title = str(m_dict.get('title', '')).strip()
        book_t = str(m_dict.get('book_title', '')).strip()
        m_desc = str(m_dict.get('description', '')).strip()
        max_p = m_dict.get('max_participants', 8)
        try:
            max_p = int(max_p)
        except Exception:
            max_p = 8

        is_bung = ("소모임" in m_title or "벙" in m_title or book_t == "자율 / 소모임")
        is_jijung = (
            not is_bung and (
                "지정책" in m_title or "지정" in m_title or "지정책" in book_t or
                "[책장:" in m_desc or "[카톡:" in m_desc or
                (0 < max_p < 50 and max_p != 999)
            )
        )

        if not (is_bung or is_jijung):
            continue

        d_val = _parse_meeting_date(m_dict.get('meeting_date'))
        if not d_val:
            continue

        if d_val not in events_by_date:
            events_by_date[d_val] = []

        if is_jijung:
            events_by_date[d_val].append({
                "type": "jijung",
                "type_name": "지정책",
                "emoji": "📕",
                "title": m_title
            })
        elif is_bung:
            events_by_date[d_val].append({
                "type": "bung",
                "type_name": "소모임/벙",
                "emoji": '<span class="cal-coffee-emoji">☕️</span>',
                "title": m_title
            })

    st.markdown(
        '<div class="cal-legend-caption">'
        '💡 <b>범례:</b> 📕 지정책 모임 &nbsp;|&nbsp; <span class="cal-coffee-emoji">☕️</span> 소모임 및 벙'
        '</div>',
        unsafe_allow_html=True
    )

    now_kst = get_current_kst()
    cur_ym = (now_kst.year, now_kst.month)

    candidate_months = [(2026, 9), (2026, 10), (2026, 11)]
    active_months = [(y, m) for (y, m) in candidate_months if (y, m) >= cur_ym]
    if not active_months:
        active_months = [candidate_months[-1]]

    month_cals = [(m, generate_submeeting_calendar_html(y, m, events_by_date)) for y, m in active_months]
    tab_titles = ["🗓️ 전체보기"] + [f"{m}월" for m, _ in month_cals]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        all_html = f'<div class="cal-months-container">{"".join([c for _, c in month_cals])}</div>'
        st.markdown(all_html, unsafe_allow_html=True)

    for idx, (m, c_html) in enumerate(month_cals, start=1):
        with tabs[idx]:
            st.markdown(f'<div style="max-width:380px; margin:0 auto;">{c_html}</div>', unsafe_allow_html=True)
