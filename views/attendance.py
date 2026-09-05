import streamlit as st
import pandas as pd
from datetime import datetime, time, date
from database import (
    get_all_meetings, get_rsvps_for_meeting, 
    get_attendances_for_meeting, init_db, get_connection
)
from utils import (
    haversine_distance, render_geolocation_button, LOCATION_PRESETS, 
    fetch_google_sheet_members, fetch_google_sheet_attendances, 
    get_member_attendance_count, get_meeting_target_gps, 
    format_season_display, ATTENDANCE_WEBHOOK_URL, 
    append_attendance_to_google_sheet_async, get_club_season_code,
    get_current_kst, format_member_attendance_and_deposit_text
)

def filter_attendances_for_meeting(att_df, selected_meeting):
    """
    구글 시트 출석 데이터프레임에서 특정 모임(모임명 & 모임 일자)과 일치하는 출석 기록만 정확히 필터링
    """
    if att_df is None or att_df.empty:
        return []
        
    m_title = str(selected_meeting.get('title', '')).strip()
    m_date_str = str(selected_meeting.get('meeting_date', '')).strip()
    
    target_dt = None
    if m_date_str:
        try:
            target_dt = datetime.strptime(m_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    results = []
    for idx, row in att_df.iterrows():
        r_email = str(row.get('회원 이메일', '')).strip()
        r_name = str(row.get('회원 성함', '')).strip()
        r_meeting = str(row.get('모임명', '')).strip()
        r_checked_at = str(row.get('출석 일시 (KST)', '')).strip()
        r_book = str(row.get('도서명', '')).strip()

        # 1. 모임명 일치 검사
        is_meeting_match = (r_meeting == m_title or m_title in r_meeting or r_meeting in m_title)
        if not is_meeting_match:
            continue

        # 2. 모임 일자(날짜) 일치 검사
        is_date_match = False
        if target_dt and r_checked_at:
            r_date_part = r_checked_at.split()[0].strip()
            for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
                try:
                    att_dt = datetime.strptime(r_date_part, fmt).date()
                    if att_dt == target_dt:
                        is_date_match = True
                        break
                except Exception:
                    continue
            if not is_date_match and m_date_str in r_checked_at:
                is_date_match = True
        elif not target_dt:
            is_date_match = True

        if is_date_match:
            results.append({
                "member_name": r_name,
                "email": r_email,
                "book_read": r_book,
                "checked_at": r_checked_at
            })

    return results

def render_attendance():
    """모임 출석체크 뷰"""
    init_db()

    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h2 style="margin-bottom: 4px; font-weight: 800; color: #1E293B;">📍 모임 출석체크</h2>
        <p style="color: #64748B; font-size: 0.95rem; margin: 0;">현장 도착 후 시간 및 GPS 위치를 확인하여 출석을 완료하세요.</p>
    </div>
    """, unsafe_allow_html=True)

    # 세션 스테이트 초기화
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    google_user = st.session_state.google_user

    # 🔐 구글 시트 기반 전용 Google 이메일 본인 인증
    st.markdown("#### 🔐 Google 계정 본인 인증")

    if not google_user:
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            g_email_input = st.text_input("Google 계정 이메일 주소", placeholder="example@gmail.com", key="att_google_login_email")
        with col_g2:
            st.write("")
            st.write("")
            login_submitted = st.button("🔑 Google 인증", key="att_google_login_btn", type="primary", use_container_width=True)

        if login_submitted:
            email_str = g_email_input.strip().lower()
            if "@" not in email_str or "." not in email_str:
                st.error("올바른 Google 이메일 주소를 입력해 주세요.")
            else:
                success, df_sheet, err_msg = fetch_google_sheet_members()
                found_member = None

                if success and df_sheet is not None:
                    email_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이메일", "email", "mail"])), df_sheet.columns[1] if len(df_sheet.columns)>1 else None)
                    name_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이름", "성함", "name", "성명"])), df_sheet.columns[0] if len(df_sheet.columns)>0 else None)
                    nick_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["닉네임", "별명", "nick"])), None)
                    reg_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록", "상태", "reg", "status"])), None)
                    admin_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["운영진", "관리자", "admin"])), None)
                    season_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록시즌", "등록 시즌", "시즌"])), None)

                    if email_col:
                        matched_row = df_sheet[df_sheet[email_col].astype(str).str.strip().str.lower() == email_str]
                        if not matched_row.empty:
                            r = matched_row.iloc[0]
                            u_name = str(r[name_col]).strip() if name_col and pd.notna(r[name_col]) else "회원"
                            u_nick = str(r[nick_col]).strip() if nick_col and pd.notna(r[nick_col]) else ""
                            u_season = str(r[season_col]).strip() if season_col and pd.notna(r[season_col]) else ""
                            
                            raw_reg = str(r[reg_col]).strip() if reg_col and pd.notna(r[reg_col]) else "0"
                            reg_val = 1 if raw_reg in ["1", "등록", "승인", "True", "true", "완료"] else 0

                            raw_admin = str(r[admin_col]).strip() if admin_col and pd.notna(r[admin_col]) else "0"
                            admin_val = 1 if raw_admin in ["1", "운영진", "관리자", "True", "true"] else 0

                            found_member = {
                                "id": hash(email_str) % 100000,
                                "name": u_name,
                                "nickname": u_nick,
                                "display_name": f"{u_name} - {u_nick}" if u_nick else u_name,
                                "email": email_str,
                                "season": u_season,
                                "registered": reg_val,
                                "is_admin": admin_val
                            }

                if not found_member:
                    st.error("🚨 미등록 회원입니다. 구글 시트 등록 상태 및 이메일을 확인해 주세요.")
                    st.session_state.google_user = None
                else:
                    st.session_state.google_user = found_member
                    m_season = found_member.get('season')
                    season_label = format_season_display(m_season)
                    att_cnt = get_member_attendance_count(found_member['email'], found_member['display_name'], target_season=m_season)
                    st.success(f"✅ Google 인증 완료: 환영합니다. {found_member['name']} - {found_member['nickname']} ({found_member['email']}) (🏆 {season_label} 출석: {att_cnt}회)")
                    st.rerun()

        st.warning("⚠️ 출석체크를 진행하려면 먼저 상단에서 Google 계정 인증을 완료해 주세요.")
        return

    else:
        admin_badge = " [👑 운영진]" if google_user.get("is_admin", 0) == 1 else ""
        att_txt = format_member_attendance_and_deposit_text(google_user)
        if not att_txt:
            m_season = google_user.get('season')
            season_label = format_season_display(m_season)
            att_cnt = get_member_attendance_count(google_user['email'], google_user['display_name'], target_season=m_season)
            att_txt = f"🏆 {season_label} 출석 횟수: <b>{att_cnt}회</b>"
        
        col_box, col_logout = st.columns([4, 1])
        with col_box:
            st.markdown(f"""
            <div class="info-callout" style="background-color: #E8F0FE; border-left-color: #1A73E8; color: #174EA6; padding: 16px; font-size: 1.05rem;">
                <b>✅ Google 인증 완료{admin_badge}:</b><br/>
                환영합니다. <b>{google_user['name']} - {google_user['nickname']}</b> ({google_user['email']})<br/>
                <span style="font-size: 0.98rem; color: #185ABC;">{att_txt}</span>
            </div>
            """, unsafe_allow_html=True)

        with col_logout:
            st.write("")
            if st.button("🚪 로그아웃", key="att_google_logout_btn"):
                st.session_state.google_user = None
                st.rerun()

    st.markdown("---")

    meetings = get_all_meetings()
    if not meetings:
        st.warning("개설된 모임이 없습니다.")
        return

    today_date = get_current_kst().date()

    my_meetings = []
    is_admin = (google_user and google_user.get("is_admin", 0) == 1)

    for m in meetings:
        max_p = m.get('max_participants', 999) if isinstance(m, dict) else getattr(m, 'max_participants', 999)
        book_t = str(m.get('book_title', '') or '' if isinstance(m, dict) else getattr(m, 'book_title', '')).strip()
        m_desc = str(m.get('description', '') or '' if isinstance(m, dict) else getattr(m, 'description', ''))
        m_title = str(m.get('title', '') or '' if isinstance(m, dict) else getattr(m, 'title', ''))

        is_bung = ("소모임" in m_title or "벙" in m_title or book_t == "자율 / 소모임")
        is_regular = (
            (max_p >= 900 or "자유" in book_t or "강남 (" in m_title or "종각 (" in m_title)
            and "[책장:" not in m_desc
            and "지정" not in m_title
        )
        is_jijung = (not is_bung and not is_regular) or ("지정" in m_title or "지정" in book_t or "[책장:" in m_desc or (0 < max_p < 50))
        
        m_date_str = m['meeting_date'] if (isinstance(m, dict) and 'meeting_date' in m) else getattr(m, 'meeting_date', '')
        try:
            m_date = datetime.strptime(str(m_date_str).strip(), "%Y-%m-%d").date()
        except Exception:
            m_date = today_date

        # 지난 모임 제외 & 정규모임만 출석체크 대상 (지정책 및 소모임 완전 제외)
        if m_date >= today_date and is_regular and not is_jijung and not is_bung:
            if is_admin:
                my_meetings.append(m)
            else:
                rsvps = get_rsvps_for_meeting(m['id'])
                user_email = str(google_user.get('email', '')).strip().lower()
                user_display = str(google_user.get('display_name', '')).strip()
                user_name = str(google_user.get('name', '')).strip()
                
                has_rsvp = any(
                    (user_email and str(r.get('member_phone', '')).strip().lower() == user_email) or
                    (user_display and str(r.get('member_name', '')).strip() == user_display) or
                    (user_name and str(r.get('member_name', '')).strip() == user_name)
                    for r in rsvps
                )
                if has_rsvp:
                    my_meetings.append(m)

    if not my_meetings:
        if is_admin:
            st.info("📌 현재 예정된 정규모임이 없습니다.")
        else:
            st.info(f"📌 [{google_user['display_name']}] 님은 현재 참가 신청한 예정된 정규모임이 없습니다. 먼저 **'모임 일정 & 신청'** 메뉴에서 정규모임 신청을 진행해 주세요.")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("📅 '모임 일정 & 신청' 바로가기", key="att_goto_sched_btn", type="primary", use_container_width=True):
                    st.session_state.current_page = "schedule"
                    try:
                        st.switch_page("pages/3_📅_모임_일정_및_신청.py")
                    except Exception:
                        st.rerun()
            with col_b2:
                if st.button("⬅️ 메인 메뉴로 돌아가기", key="att_goto_home_btn", use_container_width=True):
                    st.session_state.current_page = "home"
                    try:
                        st.switch_page("app.py")
                    except Exception:
                        st.rerun()
        return

    meeting_dict = {f"[{m['meeting_date']}] {m['title']}\n📍 {m['location_name']}": m for m in my_meetings}
    selected_meeting_label = st.selectbox("출석체크할 모임 선택", list(meeting_dict.keys()), key="att_meeting_select")
    selected_meeting = meeting_dict[selected_meeting_label]

    # 👑 운영진 전용 시간/위치 제한 해제 체크박스 (모임 선택 즉시 최상단 노출)
    bypass_time = False
    if is_admin:
        st.markdown("""
        <div style="background-color: #FFFDF5; border: 1px solid #FFE082; border-radius: 10px; padding: 10px 14px; margin: 8px 0 12px 0;">
            <b style="color: #B78103;">👑 운영진 모드:</b> 출석체크 시간/위치 제한 해제 및 사전 신청 여부와 무관한 즉시 출석체크가 가능합니다.
        </div>
        """, unsafe_allow_html=True)
        bypass_time = st.checkbox("🔓 [운영진] 출석체크 조건(시간/위치 제한) 해제하기", value=True, key="att_admin_bypass_time_top")

    rsvps = get_rsvps_for_meeting(selected_meeting['id'])
    user_email = str(google_user.get('email', '')).strip().lower()
    user_display = str(google_user.get('display_name', '')).strip()
    user_name = str(google_user.get('name', '')).strip()
    user_nick = str(google_user.get('nickname', '')).strip()
    
    my_rsvp = next((
        r for r in rsvps
        if (user_email and str(r.get('member_phone', '')).strip().lower() == user_email) or
           (user_display and str(r.get('member_name', '')).strip() == user_display) or
           (user_name and str(r.get('member_name', '')).strip() == user_name)
    ), None)

    # 구글 시트에서 실시간 출석 기록 조회
    ok_att, att_df = fetch_google_sheet_attendances()
    gs_attendances = filter_attendances_for_meeting(att_df, selected_meeting)

    if not my_rsvp:
        if is_admin:
            # 운영진은 사전 참가신청(RSVP)이 없더라도 현장 출석체크 및 모니터링이 가능하도록 자동 허용
            my_rsvp = {
                "id": 9999,
                "meeting_id": selected_meeting['id'],
                "member_id": google_user['id'],
                "member_name": google_user['display_name'],
                "member_phone": google_user['email'],
                "participation_type": "운영진"
            }
            st.info(f"👑 **운영진 권한**: [{selected_meeting['title']}] 모임에 사전 신청 내역이 없으나, 운영진 권한으로 즉시 출석체크 및 실시간 명단 조회가 가능합니다.")
        else:
            st.warning("⚠️ 현재 선택하신 모임은 참가 신청 내역이 없어 출석체크를 진행할 수 없습니다.")
            return

    # 시간 체크 로직 (해당 모임 날짜의 16:00 ~ 17:00 KST, 여유 버퍼 15:50 ~ 17:30 허용)
    now_kst = get_current_kst()
    today_str = now_kst.strftime("%Y-%m-%d")

    is_correct_day = (today_str == selected_meeting['meeting_date'])
    is_correct_time = (time(15, 50) <= now_kst.time() <= time(17, 30))
    is_valid_time_window = is_correct_day and is_correct_time

    # 이미 출석 완료했는지 판단
    already_checked_in = False
    for att in gs_attendances:
        att_email = str(att.get('email', '')).strip().lower()
        att_name = str(att.get('member_name', '')).strip()
        
        match_email = (user_email and att_email == user_email)
        match_name = (
            (user_display and user_display == att_name) or
            (user_name and user_name == att_name) or
            (user_nick and user_nick in att_name) or
            (user_name and user_name in att_name)
        )
        if match_email or match_name:
            already_checked_in = True
            break

    if "checked_meetings" not in st.session_state:
        st.session_state.checked_meetings = set()

    if selected_meeting['id'] in st.session_state.checked_meetings:
        already_checked_in = True
    else:
        local_atts = get_attendances_for_meeting(selected_meeting['id'])
        m_date_str = str(selected_meeting.get('meeting_date', '')).strip()
        for a in local_atts:
            a_dict = dict(a)
            a_checked = str(a_dict.get('checked_at', ''))
            if (a_dict.get('member_name') == my_rsvp['member_name'] or a_dict.get('member_id') == google_user['id']):
                if not m_date_str or m_date_str in a_checked:
                    already_checked_in = True
                    break

    target_name, target_lat, target_lng = get_meeting_target_gps(selected_meeting)

    if already_checked_in:
        st.info(f"✅ [{selected_meeting['meeting_date']}] {selected_meeting['title']} 출석체크가 완료되었습니다!")
    else:
        att_choice = st.radio(
            "📌 출석 유형 선택", 
            ["📖 정규모임", "🛋️ 라운징"], 
            horizontal=True, 
            key="att_type_radio_choice"
        )

        current_att_choice = st.session_state.get("att_type_radio_choice", att_choice)
        att_type_name = "라운징" if "라운징" in str(current_att_choice) else "정규모임"

        book_read_input = st.text_input("📖 지참 책 제목", placeholder="예: 데미안, 사피엔스 등", key="att_book_read_input")
        book_author_input = st.text_input("✍️ 저자 / 작가 (선택)", placeholder="예: 헤르만 헤세 (선택)", key="att_book_author_input")
        rating_val = st.radio("⭐ 도서 별점 (선택)", [5, 4, 3, 2, 1], format_func=lambda x: "⭐" * x + f" ({x}점)", horizontal=True, key="att_rating_input")
        book_review_input = st.text_area("💬 책에 대한 간단한 감상평 (선택)", placeholder="책을 읽고 느낀 점이나 공유하고 싶은 한 줄 생각을 적어주세요 (선택)", key="att_book_review_input", height=80)

        if not is_valid_time_window and not bypass_time:
            st.warning(f"⏱️ **출석체크 가능 시간 안내**: **{selected_meeting['meeting_date']} 모임 당일 16:00 ~ 17:00**에만 출석체크가 가능합니다.")

        if st.button("✅ 출석체크 완료하기", type="primary", use_container_width=True, key="att_confirm_btn"):
            u_lat, u_lng = target_lat, target_lng
            dist_m = haversine_distance(u_lat, u_lng, target_lat, target_lng)
            is_within_200m = (dist_m <= 200)

            book_title_val = book_read_input.strip()
            book_author_val = book_author_input.strip()
            book_review_val = book_review_input.strip()
            if att_type_name == "정규모임" and not book_title_val:
                st.error("⚠️ 정규모임 출석체크를 완료하려면 지참 책 제목을 입력해 주세요.")
            elif not is_within_200m and not bypass_time:
                st.error("⚠️ 위치를 확인해주세요.")
            elif not is_valid_time_window and not bypass_time:
                st.error(f"⚠️ 모임 시간을 확인해주세요. ({selected_meeting['meeting_date']} 모임 당일 16:00 ~ 17:00만 출석체크 가능)")
            else:
                with st.spinner("🔄 출석 처리 중입니다... 잠시만 기다려 주세요."):
                    st.session_state.checked_meetings.add(selected_meeting['id'])
                    is_lounging_val = 1 if att_type_name == "라운징" else 0
                    record_book_text = book_title_val if book_title_val else ("라운징" if is_lounging_val == 1 else "자유책")

                    now_sync = get_current_kst()
                    now_str = now_sync.strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                        INSERT OR REPLACE INTO attendance (meeting_id, member_id, member_name, latitude, longitude, distance_m, checked_at, book_read, is_lounging)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (selected_meeting['id'], google_user['id'], my_rsvp['member_name'], target_lat, target_lng, 0.0, now_str, record_book_text, is_lounging_val))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass

                    season_code = get_club_season_code(now_sync)
                    append_attendance_to_google_sheet_async(
                        ATTENDANCE_WEBHOOK_URL,
                        checked_at=now_str,
                        email=google_user.get('email', ''),
                        name=my_rsvp['member_name'],
                        year=f"{now_sync.year}년",
                        season=season_code,
                        meeting_name=selected_meeting['title'],
                        book_read=record_book_text,
                        book_review=book_review_val,
                        is_lounging=is_lounging_val,
                        book_author=book_author_val,
                        rating=rating_val
                    )
                    st.balloons()
                    st.success("✅ 출석체크가 정상적으로 완료되었습니다!")
                    st.rerun()

    if is_admin:
        st.markdown("---")
        st.markdown(f"#### 📋 [{selected_meeting['meeting_date']}] {selected_meeting['title']} 출석 완료 명단 [👑 운영진 전용]")
        if gs_attendances:
            for att in gs_attendances:
                t_str = str(att['checked_at']).split()[1][:5] if ' ' in str(att['checked_at']) else str(att['checked_at'])[:5]
                raw_b = str(att.get('book_read', ''))
                pure_b = raw_b.split(" (💬 ")[0].strip() if " (💬 " in raw_b else raw_b
                b_str = f" (📖 {pure_b})" if pure_b else ""
                st.write(f"• **{att['member_name']}**{b_str} - {t_str} 출석완료")
        else:
            st.info("아직 출석 완료한 부원이 없습니다.")
