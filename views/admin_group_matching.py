"""
views/admin_group_matching.py - [슈퍼 관리자 전용] 자유책 조 자동 배치 및 노쇼 대응 뷰
"""

import streamlit as st
import pandas as pd
import datetime

from services.config import get_current_kst, get_club_season_code
from services.sheets import (
    fetch_google_sheet_members,
    fetch_google_sheet_meetings,
    fetch_google_sheet_rsvps,
    get_all_meetings
)
from services.group_matching import (
    assign_groups,
    dissolve_and_redistribute_group,
    classify_member
)

SUPER_ADMIN_EMAILS = ["hanjisubusiness22@gmail.com"]


def check_is_super_admin(google_user=None):
    """슈퍼 관리자 권한 여부 확인"""
    if google_user is None:
        google_user = st.session_state.get("google_user")
    
    # 1. 구글 로그인 이메일 검사
    if google_user:
        u_email = str(google_user.get("email", "")).strip().lower()
        if u_email in SUPER_ADMIN_EMAILS:
            return True

    # 2. 로컬 개발/테스트용 세션 플래그
    if st.session_state.get("dev_super_admin_mode", False):
        return True

    return False


def render_group_matching():
    """자유책 조 자동 배치 화면 렌더링"""
    google_user = st.session_state.get("google_user")
    is_super_admin = check_is_super_admin(google_user)

    st.markdown("""
    <div style="background-color: #F7F5F0; border-left: 5px solid #6D4C41; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #4E342E; font-size: 1.25rem;">👥 자유책 모임 조 자동 배치 (슈퍼 관리자 전용)</h3>
        <p style="margin: 4px 0 0 0; color: #795548; font-size: 0.88rem;">
            기존 및 신규 회원의 자연스러운 교류와 밸런스를 고려하여 4인 테이블을 자동 구성합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not is_super_admin:
        st.error("🔒 이 페이지는 슈퍼 관리자(Super Admin) 전용 메뉴입니다.")
        st.info("슈퍼 관리자 구글 계정으로 로그인되어 있어야 이용하실 수 있습니다.")
        
        # 로컬 테스트 지원용 (슈퍼 관리자 이메일 인증 우회 테스트)
        with st.expander("🛠️ 로컬 개발자 인증 도구"):
            adm_pw = st.text_input("테스트 인증키", type="password", key="adm_dev_pwd")
            if st.button("슈퍼 관리자 모드 활성화"):
                if adm_pw == "hanji22":
                    st.session_state["dev_super_admin_mode"] = True
                    st.success("슈퍼 관리자 모드가 활성화되었습니다!")
                    st.rerun()
                else:
                    st.error("인증키가 일치하지 않습니다.")
        return

    # 세션 상태 초기화
    if "current_assigned_groups" not in st.session_state:
        st.session_state.current_assigned_groups = None
    if "group_matching_meeting_id" not in st.session_state:
        st.session_state.group_matching_meeting_id = None

    # Step 1. 모임 데이터 및 신청자 데이터 불러오기
    with st.spinner("구글 시트에서 모임 및 회원 데이터를 불러오는 중..."):
        all_meetings = get_all_meetings()
        ok_m, df_members, _ = fetch_google_sheet_members()
        ok_r, df_rsvps = fetch_google_sheet_rsvps()

    if not all_meetings:
        st.warning("등록된 모임 목록을 가져올 수 없습니다.")
        return

    # Step 1-1. 정규모임 & 예정된 모임만 필터링 (지난 모임 제외)
    today_kst = get_current_kst().date()

    meeting_options = []
    meeting_map = {}

    for m in all_meetings:
        m_title = str(m.get("title", "")).strip()
        m_date_str = str(m.get("meeting_date", "")).strip()
        m_book = str(m.get("book_title", "")).strip()
        m_cat = str(m.get("category", "")).strip()
        max_count = m.get("max_participants", 0)

        # 1. 정규모임 여부 검사 (소모임/벙 및 지정책 제외)
        is_bung = ("소모임" in m_title or "벙" in m_title or m_book == "자율 / 소모임")
        is_jijung = ("지정책" in m_title or "지정" in m_title or "지정책" in m_book)
        is_regular = (
            not is_bung and not is_jijung and (
                max_count >= 900 or
                "토요일 강남" in m_title or "일요일 종각" in m_title or
                "강남 (" in m_title or "종각 (" in m_title or
                "정규" in m_title or
                "자유 도서" in m_book or "자유책" in m_book or
                m_cat == "정규 모임"
            )
        )
        if not is_regular:
            continue

        # 2. 날짜 검사 (지나간 모임 제외)
        m_date = None
        for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
            try:
                m_date = datetime.datetime.strptime(m_date_str, fmt).date()
                break
            except Exception:
                continue

        is_past = (m_date < today_kst) if m_date else False
        if is_past:
            continue

        label = f"[{m_date_str}] {m_title}"
        meeting_options.append(label)
        meeting_map[label] = m

    if not meeting_options:
        st.info("📅 현재 예정된 정규모임(자유책)이 없습니다.")
        return

    selected_label = st.selectbox(
        "📅 조를 편성할 모임을 선택하세요",
        options=meeting_options,
        index=0,
        key="sel_matching_meeting"
    )

    selected_meeting = meeting_map.get(selected_label)
    if not selected_meeting:
        return

    # 선택된 모임 일자 기준 자동으로 시즌 코드 계산 (관리자 수동 선택 불필요)
    m_date_str = str(selected_meeting.get("meeting_date", "")).strip()
    try:
        m_dt = datetime.datetime.strptime(m_date_str, "%Y-%m-%d").date()
        cutoff_season = str(get_club_season_code(m_dt))
    except Exception:
        cutoff_season = str(get_club_season_code())

    # 회원 사전 구축 (이름 -> 닉네임, 처음등록시즌, 조배치)
    # 회원 사전 구축 (이름 & 이메일 매핑)
    mem_by_name = {}
    mem_by_email = {}
    if df_members is not None and not df_members.empty:
        for _, mrow in df_members.iterrows():
            m_name = str(mrow.get("이름", "")).strip()
            m_email = str(mrow.get("이메일", "")).strip().lower()
            m_nick = str(mrow.get("닉네임", "")).strip()
            # 회원목록 시트의 '처음등록시즌' 열 정확히 매핑
            m_season = str(mrow.get("처음등록시즌", "")).strip()
            if not m_season:
                m_season = str(mrow.get("현재등록시즌", "")).strip()
            m_attr = str(mrow.get("조배치", "0")).strip()
            
            info = {
                "name": m_name,
                "nickname": m_nick,
                "season": m_season,
                "group_attr": m_attr
            }
            if m_name:
                mem_by_name[m_name] = info
            if m_email:
                mem_by_email[m_email] = info

    # 해당 모임 신청자 추출 (모임명 & 모임일자 동시 일치 검사 및 중복 제거)
    m_title_clean = str(selected_meeting.get("title", "")).strip()
    m_date_clean = str(selected_meeting.get("meeting_date", "")).strip()

    target_rsvps = []
    seen_identifiers = set()

    if df_rsvps is not None and not df_rsvps.empty:
        m_col = next((c for c in df_rsvps.columns if any(k in str(c) for k in ["모임명", "모임", "title"])), df_rsvps.columns[0])
        date_col = next((c for c in df_rsvps.columns if any(k in str(c) for k in ["모임일자", "일자", "날짜", "date"])), None)
        name_col = next((c for c in df_rsvps.columns if any(k in str(c) for k in ["회원명", "이름", "성함", "name"])), None)
        email_col = next((c for c in df_rsvps.columns if any(k in str(c) for k in ["이메일", "email"])), None)

        for _, rrow in df_rsvps.iterrows():
            row_m = str(rrow.get(m_col, "")).strip()
            row_d = str(rrow.get(date_col, "")).strip() if date_col else ""
            row_email = str(rrow.get(email_col, "")).strip().lower() if email_col else ""
            raw_name = str(rrow.get(name_col, "")).strip() if name_col else ""

            # 1. 모임명 매칭 검사
            title_match = bool(m_title_clean and (m_title_clean in row_m or row_m in m_title_clean))
            if not title_match:
                continue

            # 2. 모임일자(날짜) 매칭 검사 - 과거 누적 데이터와 당일 데이터 분리
            if m_date_clean and row_d:
                # 일자 정규화 비교 (2026-10-11 vs 2026.10.11 등)
                norm_target_d = m_date_clean.replace(".", "-").replace("/", "-")
                norm_row_d = row_d.replace(".", "-").replace("/", "-")
                if norm_target_d not in norm_row_d and norm_row_d not in norm_target_d:
                    continue

            # 3. 중복 신청자 제거 (동일인 중복 제출 방지)
            ident = row_email if row_email else raw_name
            if not ident or ident in seen_identifiers:
                continue
            seen_identifiers.add(ident)

            # 4. 이름 및 닉네임 분리 ("이름 - 닉네임" 형태 지원)
            clean_name = raw_name
            extracted_nick = ""
            if " - " in raw_name:
                parts = raw_name.split(" - ", 1)
                clean_name = parts[0].strip()
                extracted_nick = parts[1].strip()

            # 5. 회원목록(처음등록시즌, 조배치) 정보 매핑
            m_info = mem_by_email.get(row_email) or mem_by_name.get(clean_name) or {}

            target_rsvps.append({
                "name": clean_name or m_info.get("name", "회원"),
                "nickname": extracted_nick or m_info.get("nickname", ""),
                "season": m_info.get("season", cutoff_season),
                "group_attr": m_info.get("group_attr", "0")
            })

    st.markdown("---")

    # Step 2. 참석자 명단 및 속성 확인
    st.markdown(f"#### 📋 모임 신청자 명단 (총 {len(target_rsvps)}명)")

    if not target_rsvps:
        st.info("💡 해당 모임에 아직 신청자가 없습니다. 아래 버튼으로 시뮬레이션 샘플을 불러올 수 있습니다.")
        if st.button("🧪 시뮬레이션용 가상 샘플 명단(18명) 로드"):
            sample_raw = [
                ("김민수", "망고", "2501", "0"),
                ("이영희", "라떼", "2505", "1"),
                ("박지민", "포레스트", "2609", "0"),
                ("정수진", "클로버", "2609", "1"),
                ("최준호", "블루", "2409", "0"),
                ("강다은", "단풍", "2509", "1"),
                ("윤서준", "밤하늘", "2609", "0"),
                ("한지원", "모모", "2609", "1"),
                ("오태양", "썬", "2501", "1"),
                ("서예린", "린", "2505", "0"),
                ("송민혁", "호크", "2609", "1"),
                ("임수아", "애플", "2609", "0"),
                ("조현우", "윈드", "2405", "1"),
                ("백지우", "스노우", "2609", "0"),
                ("신동혁", "제우스", "2509", "0"),
                ("황유진", "진", "2609", "1"),
                ("권태훈", "태양", "2505", "0"),
                ("문채원", "달빛", "2609", "1"),
            ]
            target_rsvps = [
                {"name": n, "nickname": nk, "season": s, "group_attr": a}
                for n, nk, s, a in sample_raw
            ]
            st.session_state["mock_participants_list"] = target_rsvps
            st.rerun()

    if "mock_participants_list" in st.session_state and not target_rsvps:
        target_rsvps = st.session_state["mock_participants_list"]

    if target_rsvps:
        # 명단 요약 데이터프레임
        table_rows = []
        for p in target_rsvps:
            cat = classify_member(p, cutoff_season=cutoff_season)
            is_new = cat.startswith("NEW")
            table_rows.append({
                "이름": p["name"],
                "닉네임": p.get("nickname", "-"),
                "처음등록시즌": p.get("season", "-"),
                "구분": "🟢 새멤버 (New)" if is_new else "⚪ 기존멤버 (Old)"
            })
        
        with st.expander(f"참석자 명단 확인 ({len(target_rsvps)}명)", expanded=False):
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        # Step 3. 조 편성 파라미터 & 실행 버튼
        col_p1, col_p2 = st.columns([2, 2])
        with col_p1:
            target_size = st.slider("테이블당 목표 인원", min_value=3, max_value=6, value=4, step=1)
        with col_p2:
            st.write("")
            st.write("")
            assign_btn = st.button("🎲 자유책 조 자동 배치 실행", type="primary", use_container_width=True)

        if assign_btn:
            new_groups = assign_groups(
                target_rsvps,
                target_size=target_size,
                cutoff_season=cutoff_season
            )
            st.session_state.current_assigned_groups = new_groups
            st.session_state.group_matching_meeting_id = selected_label
            st.toast("✅ 조 자동 배치가 완료되었습니다!", icon="🎉")

    # Step 4. 배정 결과 시각화 및 노쇼 대응
    groups = st.session_state.current_assigned_groups
    if groups:
        st.markdown("---")
        st.markdown(f"### 🎯 자유책 모임 조 편성 결과 (총 {len(groups)}개 테이블)")

        # 각 조 카드 렌더링
        for idx, g in enumerate(groups):
            stats = g["stats"]
            with st.container():
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E0DCD3; border-radius:8px; padding:12px 16px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #F0EEE9; padding-bottom:8px; margin-bottom:8px;">
                        <span style="font-weight:700; font-size:1.1rem; color:#4E342E;">🏷️ {g['table_name']} (총 {stats['total']}명)</span>
                        <span style="font-size:0.85rem; color:#6D4C41; background:#F5F2EB; padding:3px 8px; border-radius:12px;">
                            기존: {stats['old']}명 / 신규: {stats['new']}명
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_card_left, col_card_right = st.columns([3.5, 1.5])
                with col_card_left:
                    for m in g["members"]:
                        cat_badge = "🟢 신규" if m["is_new"] else "⚪ 기존"
                        nick_str = f"({m.get('nickname')})" if m.get('nickname') else ""
                        st.markdown(
                            f"• **{m['name']}** {nick_str} &nbsp; <span style='font-size:0.8rem; color:#888;'>[ {cat_badge} ]</span>",
                            unsafe_allow_html=True
                        )

                with col_card_right:
                    # 노쇼 발생 시 2번 조 해체 및 분산 흡수 버튼
                    if len(groups) > 1:
                        if st.button(f"💥 {g['table_name']} 해체 & 분산", key=f"dissolve_btn_{idx}", use_container_width=True):
                            reorganized = dissolve_and_redistribute_group(groups, idx)
                            st.session_state.current_assigned_groups = reorganized
                            st.toast(f"🚨 {g['table_name']}를 해체하고 인원을 타 조로 균등 분산 흡수했습니다!", icon="🔄")
                            st.rerun()

        # Step 5. 카카오톡 공지용 텍스트 복사 박스
        st.markdown("#### 📢 카카오톡 공지용 텍스트")
        notice_lines = [
            f"📢 [{selected_label}] 자유책 모임 조 안내",
            ""
        ]
        for g in groups:
            notice_lines.append(f"📖 [{g['table_name']}] ({g['stats']['total']}명)")
            for m in g["members"]:
                nick_part = f" ({m.get('nickname')})" if m.get('nickname') else ""
                notice_lines.append(f"• {m['name']}{nick_part}")
            notice_lines.append("")

        notice_text = "\n".join(notice_lines)
        st.code(notice_text, language="text")
