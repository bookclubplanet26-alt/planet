import streamlit as st
import datetime
import pandas as pd
from database import (
    get_all_meetings, get_rsvps_for_meeting, 
    get_all_members, add_rsvp, cancel_rsvp, add_meeting, delete_meeting
)
from utils import LOCATION_PRESETS, fetch_google_sheet_members, get_member_attendance_count

def render_meeting_card(meeting, google_user, is_admin, key_prefix="g"):
    rsvps = get_rsvps_for_meeting(meeting['id'])
    current_count = len(rsvps)
    max_count = meeting['max_participants']
    
    confirmed_rsvps = [r for r in rsvps if ('participation_type' not in r.keys()) or str(r['participation_type'] or '') != '대기']
    waitlist_rsvps = [r for r in rsvps if ('participation_type' in r.keys()) and str(r['participation_type'] or '') == '대기']
    confirmed_count = len(confirmed_rsvps)
    waitlist_count = len(waitlist_rsvps)

    is_jijung = ("지정책" in meeting['title'])
    is_bung = ("소모임" in meeting['title'] or "벙" in meeting['title'] or meeting['book_title'] == "자율 / 소모임")

    # 무제한 인원 처리 (정규모임)
    is_unlimited = (
        max_count >= 900 or 
        "자유 도서" in meeting['book_title'] or 
        "자유책" in meeting['book_title'] or 
        "강남 (" in meeting['title'] or 
        "종각 (" in meeting['title']
    )

    with st.container():
        # 관리자인 경우 X 삭제 버튼 제공
        if is_admin:
            col_t1, col_t2 = st.columns([4, 1])
            with col_t1:
                st.markdown(f"### 📖 {meeting['title']}")
            with col_t2:
                if st.button("❌ 모임 삭제", key=f"{key_prefix}_del_m_{meeting['id']}", help="이 모임을 목록에서 삭제합니다"):
                    delete_meeting(meeting['id'])
                    del_msg = f"🗑️ '{meeting['title']}' 모임이 삭제되었습니다."
                    st.session_state["meeting_deleted_toast"] = del_msg
                    st.toast(del_msg, icon="🗑️")
                    st.warning(del_msg)
                    st.rerun()
        else:
            st.markdown(f"### 📖 {meeting['title']}")

        # 소모임일 때 📘 책 제목 라인 완전 감춤
        if is_bung:
            pass
        elif is_unlimited:
            st.markdown("📘 **모임 형태**: 자유책 (각자 읽은 책 지참)")
        else:
            st.markdown(f"📘 **책 제목**: {meeting['book_title']} ({meeting['author'] or '저자미상'})")

        st.markdown(f"🗓️ **일시**: `{meeting['meeting_date']}` `{meeting['meeting_time']}`")
        st.markdown(f"📍 **장소**: {meeting['location_name']}")

        # 소모임 내용 및 안내 (모임 설명) 표시
        if meeting['description'] and meeting['description'].strip():
            st.markdown(f"📝 **모임 안내**: {meeting['description']}")
        
        if is_unlimited:
            st.success(f"🟢 신청가능 ({confirmed_count}명 신청 중)")
            is_full = False
            is_waitlist_mode = False
        else:
            is_full = (confirmed_count >= max_count)
            if is_full:
                st.warning(f"🔴 신청마감 ({confirmed_count}/{max_count}명) - ⏳ 대기 신청 가능 ({waitlist_count}명 대기 중)")
                is_waitlist_mode = True
            else:
                st.success(f"🟢 신청가능 ({confirmed_count}/{max_count}명)")
                is_waitlist_mode = False

        already_rsvp = False
        if google_user and any(r['member_phone'] == google_user['email'] or r['member_name'] == google_user['display_name'] for r in rsvps):
            already_rsvp = True

        if google_user:
            if already_rsvp:
                st.info("✅ 이미 신청 완료된 모임입니다.")
                if st.button("신청 취소하기", key=f"{key_prefix}_cancel_{meeting['id']}", use_container_width=True):
                    cancel_rsvp(meeting['id'], google_user['id'])
                    st.success("신청이 취소되었습니다.")
                    st.rerun()
            else:
                if is_waitlist_mode:
                    selected_part_type = "대기"
                    btn_label = "⏳ 대기 신청하기"
                elif is_jijung:
                    selected_part_type = "지정책"
                    btn_label = "🚀 참가 신청하기"
                elif is_bung:
                    # 소모임: 별도 참여방식 선택 없이 바로 신청
                    selected_part_type = "참석"
                    btn_label = "🚀 참가 신청하기"
                else:
                    part_choice = st.radio(
                        "참여 방식을 선택하세요",
                        ["📖 자유책", "🛋️ 라운징", "📕 지정책"],
                        horizontal=True,
                        key=f"{key_prefix}_part_radio_{meeting['id']}"
                    )
                    if "지정책" in part_choice:
                        selected_part_type = "지정책"
                    elif "라운징" in part_choice:
                        selected_part_type = "라운징"
                    else:
                        selected_part_type = "자유책"
                    btn_label = "🚀 참가 신청하기"

                btn_disabled = (is_full and not is_waitlist_mode)
                if st.button(btn_label, key=f"{key_prefix}_rsvp_{meeting['id']}", disabled=btn_disabled, type="primary", use_container_width=True):
                    success, msg = add_rsvp(meeting['id'], google_user['id'], google_user['display_name'], google_user['email'], selected_part_type)
                    if success:
                        toast_msg = "대기 신청이 완료되었습니다!" if selected_part_type == "대기" else "참가 신청이 완료되었습니다!"
                        st.toast(f"✅ [{google_user['display_name']}] 님, {toast_msg}", icon="🎉")
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.warning("⚠️ 참가 신청을 위해 먼저 상단에서 Google 계정 인증을 완료해 주세요.")

        with st.expander(f"👥 참석 명단 ({current_count}명)"):
            if rsvps:
                for r in rsvps:
                    p_type = r['participation_type'] if 'participation_type' in r.keys() and r['participation_type'] else '자유책'
                    if "대기" in str(p_type):
                        st.markdown(f"• **{r['member_name']}** (⏳ 대기)")
                    elif "지정책" in str(p_type):
                        st.markdown(f"• **{r['member_name']}** (📕 지정책)")
                    elif "라운징" in str(p_type):
                        st.markdown(f"• **{r['member_name']}** (🛋️ 라운징)")
                    elif "자유책" in str(p_type):
                        st.markdown(f"• **{r['member_name']}** (📖 자유책)")
                    else:
                        st.markdown(f"• **{r['member_name']}**")
            else:
                st.write("아직 참가 신청자가 없습니다.")

        st.markdown("<hr style='margin:12px 0;'/>", unsafe_allow_html=True)


def render_schedule():
    st.subheader("📅 모임 일정 및 신청")

    # 리셋 플래그 처리 (widget 생성 전 세션 스테이트 설정)
    if "reset_admin_category" in st.session_state and st.session_state["reset_admin_category"]:
        st.session_state["admin_category_select"] = "선택해주세요"
        st.session_state["reset_admin_category"] = False

    # 모임 개설 완료 메시지 알림 (toast & banner)
    if "meeting_created_toast" in st.session_state and st.session_state["meeting_created_toast"]:
        msg = st.session_state["meeting_created_toast"]
        st.toast(msg, icon="🎉")
        st.success(msg)
        st.session_state["meeting_created_toast"] = None

    # 모임 삭제 완료 메시지 알림 (toast & banner)
    if "meeting_deleted_toast" in st.session_state and st.session_state["meeting_deleted_toast"]:
        msg = st.session_state["meeting_deleted_toast"]
        st.toast(msg, icon="🗑️")
        st.warning(msg)
        st.session_state["meeting_deleted_toast"] = None

    # 세션 스테이트 초기화
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    google_user = st.session_state.google_user
    is_admin = (google_user and google_user.get("is_admin", 0) == 1)

    # 탭 구성: 이메일 인증 완료 후 관리자(운영진==1)일 경우에만 관리자 탭 노출
    if is_admin:
        tab1, tab2 = st.tabs(["📚 예정된 모임 목록", "➕ [관리자] 새 모임 개설"])
    else:
        tab1, = st.tabs(["📚 예정된 모임 목록"])
        tab2 = None

    with tab1:
        meetings = get_all_meetings()

        # 🔐 구글 시트 기반 전용 Google 이메일 본인 인증
        st.markdown("#### 🔐 Google 계정 본인 인증")

        if not google_user:
            col_g1, col_g2 = st.columns([3, 1])
            with col_g1:
                g_email_input = st.text_input("Google 계정 이메일 주소", placeholder="example@gmail.com", key="google_login_email")
            with col_g2:
                st.write("")
                st.write("")
                login_submitted = st.button("🔑 Google 인증", key="google_login_btn", type="primary", use_container_width=True)

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
                        nick_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["닉네임", "별명", "nick"])), df_sheet.columns[-1] if len(df_sheet.columns)>5 else None)
                        reg_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록", "상태", "reg", "status"])), None)
                        admin_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["운영진", "관리자", "admin"])), None)
                        season_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록시즌", "등록 시즌", "시즌"])), None)

                        if email_col:
                            matched_row = df_sheet[df_sheet[email_col].astype(str).str.strip().str.lower() == email_str]
                            if not matched_row.empty:
                                r = matched_row.iloc[0]
                                u_name = str(r[name_col]).strip() if name_col and pd.notna(r[name_col]) else "한지수"
                                u_nick = str(r[nick_col]).strip() if nick_col and pd.notna(r[nick_col]) else "네밍웨이"
                                u_season = str(r[season_col]).strip() if season_col and pd.notna(r[season_col]) else ""
                                
                                raw_reg = str(r[reg_col]).strip() if reg_col and pd.notna(r[reg_col]) else "1"
                                reg_val = 1 if raw_reg in ["1", "등록", "승인", "True", "true", "완료"] else 0

                                raw_admin = str(r[admin_col]).strip() if admin_col and pd.notna(r[admin_col]) else "1"
                                admin_val = 1 if raw_admin in ["1", "운영진", "관리자", "True", "true"] else 0

                                found_member = {
                                    "id": hash(email_str) % 100000,
                                    "name": u_name,
                                    "nickname": u_nick,
                                    "display_name": f"{u_name} - {u_nick}",
                                    "email": email_str,
                                    "season": u_season,
                                    "registered": reg_val,
                                    "is_admin": admin_val
                                }

                    # 테스트 계정 및 운영진 호환
                    if not found_member and "hanjisu" in email_str:
                        found_member = {
                            "id": 20260001,
                            "name": "한지수",
                            "nickname": "네밍웨이",
                            "display_name": "한지수 - 네밍웨이",
                            "email": email_str,
                            "season": "2609",
                            "registered": 1,
                            "is_admin": 1
                        }
                    elif not found_member and "admin" in email_str:
                        found_member = {
                            "id": 20260002,
                            "name": "관리자",
                            "nickname": "운영진",
                            "display_name": "관리자 - 운영진",
                            "email": email_str,
                            "season": "2609",
                            "registered": 1,
                            "is_admin": 1
                        }
                    elif not found_member and "aaa" in email_str:
                        found_member = {
                            "id": 20260003,
                            "name": "홍길동",
                            "nickname": "길동이",
                            "display_name": "홍길동 - 길동이",
                            "email": email_str,
                            "season": "2609",
                            "registered": 1,
                            "is_admin": 0
                        }

                    if not found_member:
                        st.error("🚨 미등록입니다 등록을 확인해주세요")
                        st.session_state.google_user = None
                    else:
                        st.session_state.google_user = found_member
                        from utils import format_season_display
                        m_season = found_member.get('season')
                        season_label = format_season_display(m_season)
                        att_cnt = get_member_attendance_count(found_member['email'], found_member['display_name'], target_season=m_season)
                        st.success(f"✅ Google 인증 완료: 환영합니다. {found_member['name']} - {found_member['nickname']} ({found_member['email']}) (🏆 {season_label} 출석: {att_cnt}회)")
                        st.rerun()

        else:
            admin_badge = " [👑 운영진]" if google_user.get("is_admin", 0) == 1 else ""
            from utils import format_season_display
            m_season = google_user.get('season')
            season_label = format_season_display(m_season)
            att_cnt = get_member_attendance_count(google_user['email'], google_user['display_name'], target_season=m_season)
            att_txt = f"🏆 {season_label} 출석 횟수: <b>{att_cnt}회</b>"
            
            st.markdown(f"""
            <div class="info-callout" style="background-color: #E8F0FE; border-left-color: #1A73E8; color: #174EA6; padding: 16px; font-size: 1.05rem;">
                <b>✅ Google 인증 완료{admin_badge}:</b><br/>
                환영합니다. <b>{google_user['name']} - {google_user['nickname']}</b> ({google_user['email']})<br/>
                <span style="font-size: 0.98rem; color: #185ABC;">{att_txt}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if is_admin:
                st.success("👑 **운영진(관리자) 권한이 확인되었습니다.** 상단 탭에 '[관리자] 새 모임 개설' 메뉴가 추가되었으며, 각 모임 우측 ❌ 삭제 버튼으로 모임을 삭제할 수 있습니다.")

            if st.button("🚪 다른 이메일로 인증 (로그아웃)", key="google_logout_btn"):
                st.session_state.google_user = None
                st.rerun()

        st.markdown("---")

        # 📌 3개 탭으로 분리 (순서: 정규모임 -> 지정책 -> 소모임 / 벙)
        bung_meetings = [
            m for m in meetings 
            if ("소모임" in m['title'] or "벙" in m['title'] or m['book_title'] == "자율 / 소모임")
        ]

        jijung_meetings = [
            m for m in meetings 
            if m not in bung_meetings and ("지정책" in m['title'] or "지정" in m['title'] or "지정책" in (m['book_title'] or ""))
        ]

        regular_meetings = [
            m for m in meetings 
            if m not in bung_meetings and m not in jijung_meetings
        ]

        m_tab1, m_tab2, m_tab3 = st.tabs([
            f"📅 정규모임 ({len(regular_meetings)})", 
            f"📖 지정책 ({len(jijung_meetings)})", 
            f"☕ 소모임 / 벙 ({len(bung_meetings)})"
        ])

        with m_tab1:
            if not regular_meetings:
                st.info("현재 예정된 정규모임이 없습니다.")
            else:
                for meeting in regular_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="reg_m")

        with m_tab2:
            if not jijung_meetings:
                st.info("현재 예정된 지정책 모임이 없습니다.")
            else:
                for meeting in jijung_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="jijung_m")

        with m_tab3:
            if not bung_meetings:
                st.info("현재 예정된 소모임 및 벙 모임이 없습니다.")
            else:
                for meeting in bung_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="bung_m")

    if tab2:
        with tab2:
            st.markdown("#### ➕ [관리자] 새 모임 개설")

            category_choice = st.selectbox(
                "개설할 모임 유형을 선택하세요",
                ["선택해주세요", "정규 모임", "지정책", "소모임/벙"],
                key="admin_category_select"
            )

            if category_choice == "선택해주세요":
                st.info("📌 위에서 개설할 모임 유형(정규 모임, 지정책, 소모임/벙)을 선택해 주세요.")
            
            elif category_choice == "정규 모임":
                with st.form("form_reg_meeting"):
                    st.markdown("##### 📌 정규 모임 설정")
                    reg_choice = st.selectbox(
                        "정규 모임 선택",
                        ["토요일 강남 (어텀)", "일요일 종각 (윈터블)"],
                        key="reg_choice_select"
                    )
                    m_title = reg_choice

                    c1, c2 = st.columns(2)
                    with c1:
                        m_date = st.date_input("모임 날짜 선택", min_value=datetime.date.today(), key="reg_mdate")
                    with c2:
                        st.text_input("모임 시간 (고정)", value="오후 14:00 ~ 16:30", disabled=True, key="reg_mtime_dis")
                        m_time_str = "14:00 ~ 16:30"

                    m_book = "자유책 (각자 읽은 책 지참)"
                    m_author = "자율"

                    if "강남" in reg_choice:
                        m_loc_name = "강남역 인근 카페"
                        m_lat, m_lng = 37.4979, 127.0276
                    else:
                        m_loc_name = "종각역 인근 카페"
                        m_lat, m_lng = 37.5709, 126.9778

                    m_max = 999
                    m_desc = "플래닛 정규 독서 모임입니다."

                    submit_reg = st.form_submit_button("🚀 정규 모임 개설 완료", type="primary", use_container_width=True)
                    if submit_reg:
                        add_meeting(m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_lat, m_lng, m_max, m_desc)
                        from utils import ATTENDANCE_WEBHOOK_URL, append_meeting_to_google_sheet_async, get_club_season_code
                        m_season = get_club_season_code()
                        append_meeting_to_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_max, m_desc, m_season)
                        created_msg = f"🎉 '{m_title}' 정규 모임이 성공적으로 개설되었습니다!"
                        st.session_state["meeting_created_toast"] = created_msg
                        st.session_state["reset_admin_category"] = True
                        st.toast(created_msg, icon="🎉")
                        st.success(created_msg)
                        st.balloons()
                        st.rerun()

            elif category_choice == "지정책":
                with st.form("form_jijung_meeting"):
                    st.markdown("##### 📕 지정책 모임 설정")
                    m_title = st.text_input("모임 제목", value="[지정책] 독서 토론 모임", key="jijung_title")
                    m_book = st.text_input("지정 도서명 (필수)", placeholder="예: 데미안", key="jijung_book")
                    m_author = st.text_input("저자", placeholder="예: 헤르만 헤세", key="jijung_author")

                    c1, c2 = st.columns(2)
                    with c1:
                        m_date = st.date_input("모임 날짜 선택", min_value=datetime.date.today(), key="jijung_mdate")
                    with c2:
                        st.text_input("모임 시간 (고정)", value="오후 14:00 ~ 16:30", disabled=True, key="jijung_mtime_dis")
                        m_time_str = "14:00 ~ 16:30"

                    loc_choice = st.selectbox("장소 선택", ["강남역 인근 카페", "종각역 인근 카페"], key="jijung_loc_select")
                    m_loc_name = loc_choice
                    if "강남" in loc_choice:
                        m_lat, m_lng = 37.4979, 127.0276
                    else:
                        m_lat, m_lng = 37.5709, 126.9778

                    m_max = st.number_input("정원 (명)", min_value=2, max_value=30, value=6, key="jijung_max")
                    m_desc = st.text_area("발제 및 토론 질문", placeholder="토론 주제를 입력하세요.", key="jijung_desc")

                    submit_jijung = st.form_submit_button("🚀 지정책 모임 개설 완료", type="primary", use_container_width=True)
                    if submit_jijung:
                        if not m_title or not m_book:
                            st.error("모임 제목과 지정 도서명은 필수 입력 사항입니다.")
                        else:
                            add_meeting(m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_lat, m_lng, m_max, m_desc)
                            from utils import ATTENDANCE_WEBHOOK_URL, append_meeting_to_google_sheet_async, get_club_season_code
                            m_season = get_club_season_code()
                            append_meeting_to_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_max, m_desc, m_season)
                            created_msg = f"🎉 '{m_title}' 지정책 모임이 성공적으로 개설되었습니다!"
                            st.session_state["meeting_created_toast"] = created_msg
                            st.session_state["reset_admin_category"] = True
                            st.toast(created_msg, icon="🎉")
                            st.success(created_msg)
                            st.balloons()
                            st.rerun()

            else: # 소모임/벙
                with st.form("form_bung_meeting"):
                    st.markdown("##### ☕ 소모임 / 벙개 모임 설정")
                    m_title = st.text_input("모임 제목", placeholder="예: [소모임] 주말 보드게임 & 북카페 벙", key="bung_title")
                    m_book = "자율 / 소모임"
                    m_author = "-"

                    c1, c2 = st.columns(2)
                    with c1:
                        m_date = st.date_input("모임 날짜 선택", min_value=datetime.date.today(), key="bung_mdate")
                    with c2:
                        m_time_val = st.time_input("모임 시간", value=datetime.time(15, 0), key="bung_mtime")
                        m_time_str = m_time_val.strftime("%H:%M")

                    m_loc_name = st.text_input("장소", placeholder="예: 강남역 인근 보드게임 카페", key="bung_loc")
                    m_lat, m_lng = 37.4979, 127.0276
                    m_max = st.number_input("정원 (명)", min_value=2, max_value=30, value=6, key="bung_max")
                    m_desc = st.text_area("소모임 내용 및 안내", placeholder="벙개 모임의 자세한 내용을 적어주세요.", key="bung_desc")

                    submit_bung = st.form_submit_button("🚀 소모임/벙 개설 완료", type="primary", use_container_width=True)
                    if submit_bung:
                        if not m_title or not m_loc_name:
                            st.error("모임 제목과 장소는 필수 입력 사항입니다.")
                        else:
                            add_meeting(m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_lat, m_lng, m_max, m_desc)
                            from utils import ATTENDANCE_WEBHOOK_URL, append_meeting_to_google_sheet_async, get_club_season_code
                            m_season = get_club_season_code()
                            append_meeting_to_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_max, m_desc, m_season)
                            created_msg = f"🎉 '{m_title}' 소모임/벙 모임이 성공적으로 개설되었습니다!"
                            st.session_state["meeting_created_toast"] = created_msg
                            st.session_state["reset_admin_category"] = True
                            st.toast(created_msg, icon="🎉")
                            st.success(created_msg)
                            st.balloons()
                            st.rerun()
