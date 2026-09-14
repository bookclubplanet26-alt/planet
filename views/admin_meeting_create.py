import streamlit as st
import datetime
from utils import (
    get_current_kst, 
    ATTENDANCE_WEBHOOK_URL, 
    append_meeting_to_google_sheet_async, 
    get_club_season_code
)

def render_admin_meeting_create():
    """
    운영진(관리자) 전용 모임 개설 뷰
    - 정규 모임, 지정책, 소모임/벙 3개 유형 폼 제공
    """
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
                with st.spinner("정규 모임 개설 중..."): 
                    m_season = get_club_season_code()
                    ok = append_meeting_to_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, str(m_date), m_time_str, m_loc_name, m_max, m_desc, m_season)
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
            m_title = st.text_input("모임 제목", value="[지정책] 독서 토론 모임", key="jijung_title")
            jijung_leader = st.text_input("지정책장 이름", placeholder="예: 한지수 - 네밍웨이", key="jijung_leader")
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
            kakao_link = st.text_input("오픈 카카오톡방 주소 (URL)", placeholder="예: https://open.kakao.com/o/...", key="jijung_kakao_link")
            m_desc = st.text_area("발제 및 토론 질문", placeholder="토론 주제를 입력하세요.", key="jijung_desc")

            submit_jijung = st.form_submit_button("🚀 지정책 모임 개설 완료", type="primary", use_container_width=True)
            if submit_jijung:
                if not m_title or not m_book:
                    st.error("모임 제목과 지정 도서명은 필수 입력 사항입니다.")
                else:
                    with st.spinner("지정책 모임 개설 중..."): 
                        pure_desc = m_desc.strip() if m_desc else ""
                        m_season = get_club_season_code()
                        # 구글 시트에는 순수 모임설명만 전송 (책장/카톡 태그 분리)
                        ok = append_meeting_to_google_sheet_async(
                            ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, 
                            str(m_date), m_time_str, m_loc_name, m_max, pure_desc, 
                            m_season, jijung_leader=jijung_leader.strip(), kakao_url=kakao_link.strip()
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
            st.markdown("##### ☕ 소모임 / 벙개 모임 설정")
            m_title = st.text_input("모임 제목", placeholder="예: [소모임] 주말 보드게임 & 북카페 벙", key="bung_title")
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
            m_desc = st.text_area("소모임 내용 및 안내", placeholder="벙개 모임의 자세한 내용을 적어주세요.", key="bung_desc")

            submit_bung = st.form_submit_button("🚀 소모임/벙 개설 완료", type="primary", use_container_width=True)
            if submit_bung:
                if not m_title or not m_loc_name:
                    st.error("모임 제목과 장소는 필수 입력 사항입니다.")
                else:
                    with st.spinner("소모임 개설 중..."): 
                        m_season = get_club_season_code()
                        pure_desc = m_desc.strip() if m_desc else ""
                        ok = append_meeting_to_google_sheet_async(
                            ATTENDANCE_WEBHOOK_URL, m_title, m_book, m_author, 
                            str(m_date), m_time_str, m_loc_name, m_max, pure_desc, 
                            m_season, kakao_url=kakao_link.strip()
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
