import streamlit as st
import datetime
from utils import (
    get_current_kst, 
    ATTENDANCE_WEBHOOK_URL, 
    append_meeting_to_google_sheet_async, 
    get_club_season_code,
    get_all_meetings
)

def _format_kakao_link(url_str):
    """
    오픈카톡 링크 입력값에 프로토콜(https://)이 누락된 경우 자동 보정
    """
    s = str(url_str or "").strip()
    if not s or s.lower() in ["nan", "none", "null"]:
        return ""
    if not s.startswith(("http://", "https://")):
        return f"https://{s}"
    return s

def _is_duplicate_meeting(title, meeting_date):
    """
    동일 날짜 및 동일 제목의 모임이 이미 존재하는지 검사하여 중복 등록 방어
    """
    existing = get_all_meetings()
    clean_t = str(title).strip()
    clean_d = str(meeting_date).strip()
    for m in existing:
        m_t = str(m.get('title', '')).strip()
        m_d = str(m.get('meeting_date', '')).strip()
        if m_t == clean_t and m_d == clean_d:
            return True
    return False

def render_admin_meeting_create(google_user=None, is_admin=None, is_dedicated=None):
    """
    모임 개설 뷰 (관리자: 정규모임/지정책/소모임 전체, 열심멤버: 지정책/소모임 개설 및 본인 이름 고정)
    """
    if google_user is None:
        google_user = st.session_state.get("google_user")
    if is_admin is None:
        is_admin = bool(google_user and google_user.get("is_admin", 0) == 1)
    if is_dedicated is None:
        is_dedicated = bool(google_user and google_user.get("is_dedicated", 0) == 1)

    st.markdown("#### ➕ 새 모임 개설")

    # 관리자는 정규모임 포함 전체, 열심멤버(비관리자)는 정규모임 제외하고 지정책/소모임만 선택 가능
    if is_admin:
        cat_options = ["선택해주세요", "정규 모임", "지정책", "소모임/벙"]
    else:
        cat_options = ["선택해주세요", "지정책", "소모임/벙"]

    category_choice = st.selectbox(
        "개설할 모임 유형을 선택하세요",
        cat_options,
        key="admin_category_select"
    )

    if category_choice == "선택해주세요":
        type_names = ", ".join(cat_options[1:])
        st.info(f"📌 위에서 개설할 모임 유형({type_names})을 선택해 주세요.")
    
    elif category_choice == "정규 모임" and is_admin:
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
                m_date = st.date_input("모임 날짜 선택", min_value=get_current_kst().date(), key="reg_mdate")
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
                weekday = m_date.weekday()
                weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
                if "토요일" in reg_choice and weekday != 5:
                    st.error(f"🚨 선택하신 날짜({m_date})는 **{weekday_names[weekday]}요일**입니다. '토요일 강남 (어텀)' 모임은 반드시 토요일 날짜여야 합니다.")
                elif "일요일" in reg_choice and weekday != 6:
                    st.error(f"🚨 선택하신 날짜({m_date})는 **{weekday_names[weekday]}요일**입니다. '일요일 종각 (윈터블)' 모임은 반드시 일요일 날짜여야 합니다.")
                elif _is_duplicate_meeting(m_title, str(m_date)):
                    st.error(f"🚨 해당 날짜({m_date})에 동일한 모임('{m_title}')이 이미 개설되어 있습니다.")
                else:
                    with st.spinner("정규 모임 개설 중..."): 
                        m_season = get_club_season_code()
                        ok = append_meeting_to_google_sheet_async(
                            webhook_url=ATTENDANCE_WEBHOOK_URL,
                            title=m_title,
                            book_title=m_book,
                            author=m_author,
                            meeting_date=str(m_date),
                            meeting_time=m_time_str,
                            location_name=m_loc_name,
                            max_participants=m_max,
                            description=m_desc,
                            season=m_season,
                            jijung_leader="",
                            kakao_url="",
                            account_info=""
                        )
                    if ok:
                        created_msg = f"🎉 '{m_title}' 정규 모임이 성공적으로 개설되었습니다!"
                        st.session_state["meeting_created_toast"] = created_msg
                        st.session_state["reset_admin_category"] = True
                        st.toast(created_msg, icon="🎉")
                        st.success(created_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("🚨 구글 시트에 모임을 저장하지 못했습니다. 서비스 계정 권한 또는 네트워크 상태를 확인해 주세요.")

    elif category_choice == "지정책":
        with st.form("form_jijung_meeting"):
            st.markdown("##### 📕 지정책 모임 설정")
            m_title = st.text_input("모임 제목", value="<지정책> 독서 토론 모임", key="jijung_title")
            
            default_leader = google_user.get('display_name', '') if google_user else ""
            jijung_leader = st.text_input(
                "지정책장 이름", 
                value=default_leader, 
                disabled=(not is_admin),
                placeholder="예: 한지수 - 네밍웨이", 
                key="jijung_leader",
                help="열심멤버는 본인 명의로 자동 고정됩니다." if not is_admin else "관리자는 직접 입력 및 수정 가능합니다."
            )
            m_book = st.text_input("지정 도서명 (필수)", placeholder="예: 태양은 다시 떠오른다", key="jijung_book")
            m_author = st.text_input("저자명 (필수)", placeholder="예: 어니스트 헤밍웨이", key="jijung_author")

            c1, c2 = st.columns(2)
            with c1:
                m_date = st.date_input("모임 날짜 선택", min_value=get_current_kst().date(), key="jijung_mdate")
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
            c_link1, c_link2 = st.columns(2)
            with c_link1:
                kakao_link = st.text_input("오픈 카카오톡방 주소 (URL)", placeholder="예: https://open.kakao.com/o/...", key="jijung_kakao_link")
            with c_link2:
                account_info = st.text_input("입금 계좌번호 (선택)", placeholder="예: 카카오뱅크 3333-01-xxxx (예금주)", key="jijung_account")
            m_desc = st.text_area("책 설명", placeholder="책에 대한 설명을 입력하세요.", key="jijung_desc")

            submit_jijung = st.form_submit_button("🚀 지정책 모임 개설 완료", type="primary", use_container_width=True)
            if submit_jijung:
                leader_val = jijung_leader.strip() if jijung_leader else default_leader
                clean_kakao = _format_kakao_link(kakao_link)
                if not m_title or not m_book:
                    st.error("모임 제목과 지정 도서명은 필수 입력 사항입니다.")
                elif not leader_val:
                    st.error("지정책장 이름이 입력되지 않았습니다.")
                elif _is_duplicate_meeting(m_title, str(m_date)):
                    st.error(f"🚨 해당 날짜({m_date})에 동일한 모임('{m_title}')이 이미 개설되어 있습니다.")
                else:
                    with st.spinner("지정책 모임 개설 중..."): 
                        pure_desc = m_desc.strip() if m_desc else ""
                        acc_val = account_info.strip() if account_info else ""
                        m_season = get_club_season_code()
                        ok = append_meeting_to_google_sheet_async(
                            webhook_url=ATTENDANCE_WEBHOOK_URL,
                            title=m_title,
                            book_title=m_book,
                            author=m_author,
                            meeting_date=str(m_date),
                            meeting_time=m_time_str,
                            location_name=m_loc_name,
                            max_participants=m_max,
                            description=pure_desc,
                            season=m_season,
                            jijung_leader=leader_val,
                            kakao_url=clean_kakao,
                            account_info=acc_val
                        )
                    if ok:
                        created_msg = f"🎉 '{m_title}' 지정책 모임이 성공적으로 개설되었습니다!"
                        st.session_state["meeting_created_toast"] = created_msg
                        st.session_state["reset_admin_category"] = True
                        st.toast(created_msg, icon="🎉")
                        st.success(created_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("🚨 구글 시트에 모임을 저장하지 못했습니다. 서비스 계정 권한 또는 네트워크 상태를 확인해 주세요.")

    else: # 소모임/벙
        with st.form("form_bung_meeting"):
            st.markdown("##### ☕ 소모임 / 벙 모임 설정")
            m_title = st.text_input("모임 제목", placeholder="예: [소모임] 주말 보드게임 & 북카페 벙", key="bung_title")
            
            default_host = google_user.get('display_name', '') if google_user else ""
            bung_host = st.text_input(
                "모임장(호스트) 이름", 
                value=default_host, 
                disabled=(not is_admin),
                placeholder="예: 한지수 - 네밍웨이", 
                key="bung_host",
                help="열심멤버는 본인 명의로 자동 고정됩니다." if not is_admin else "관리자는 직접 입력 및 수정 가능합니다."
            )
            m_book = "자율 / 소모임"
            m_author = "-"

            c1, c2 = st.columns(2)
            with c1:
                m_date = st.date_input("모임 날짜 선택", min_value=get_current_kst().date(), key="bung_mdate")
            with c2:
                m_time_val = st.time_input("모임 시간", value=datetime.time(15, 0), key="bung_mtime")
                m_time_str = m_time_val.strftime("%H:%M")

            m_loc_name = st.text_input("장소", placeholder="예: 강남역 인근 보드게임 카페", key="bung_loc")
            m_lat, m_lng = 37.4979, 127.0276
            m_max = st.number_input("정원 (명)", min_value=2, max_value=30, value=6, key="bung_max")
            kakao_link = st.text_input("오픈 카카오톡방 주소 (URL)", placeholder="예: https://open.kakao.com/o/...", key="bung_kakao_link")
            m_desc = st.text_area("모임 내용 및 안내", placeholder="모임의 자세한 내용을 적어주세요.", key="bung_desc")

            submit_bung = st.form_submit_button("🚀 소모임/벙 개설 완료", type="primary", use_container_width=True)
            if submit_bung:
                host_val = bung_host.strip() if bung_host else default_host
                clean_kakao = _format_kakao_link(kakao_link)
                if not m_title or not m_loc_name:
                    st.error("모임 제목과 장소는 필수 입력 사항입니다.")
                elif not host_val:
                    st.error("모임장(호스트) 이름이 입력되지 않았습니다.")
                elif _is_duplicate_meeting(m_title, str(m_date)):
                    st.error(f"🚨 해당 날짜({m_date})에 동일한 모임('{m_title}')이 이미 개설되어 있습니다.")
                else:
                    with st.spinner("소모임 개설 중..."): 
                        m_season = get_club_season_code()
                        pure_desc = m_desc.strip() if m_desc else ""
                        ok = append_meeting_to_google_sheet_async(
                            webhook_url=ATTENDANCE_WEBHOOK_URL,
                            title=m_title,
                            book_title=m_book,
                            author=m_author,
                            meeting_date=str(m_date),
                            meeting_time=m_time_str,
                            location_name=m_loc_name,
                            max_participants=m_max,
                            description=pure_desc,
                            season=m_season,
                            jijung_leader=host_val,
                            kakao_url=clean_kakao,
                            account_info=""
                        )
                    if ok:
                        created_msg = f"🎉 '{m_title}' 소모임/벙 모임이 성공적으로 개설되었습니다!"
                        st.session_state["meeting_created_toast"] = created_msg
                        st.session_state["reset_admin_category"] = True
                        st.toast(created_msg, icon="🎉")
                        st.success(created_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("🚨 구글 시트에 모임을 저장하지 못했습니다. 서비스 계정 권한 또는 네트워크 상태를 확인해 주세요.")
