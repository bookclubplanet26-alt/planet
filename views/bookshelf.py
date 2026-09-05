import streamlit as st
import pandas as pd
import datetime
from utils import (
    fetch_google_sheet_attendances, fetch_google_sheet_members,
    ATTENDANCE_WEBHOOK_URL, cancel_rsvp_from_google_sheet_async
)
from database import get_all_meetings, get_rsvps_for_meeting, cancel_rsvp

def render_bookshelf():
    st.markdown("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin-bottom: 4px; font-weight: 800; color: #1E293B;">📚 나의 서재 & 나의 모임</h2>
        <p style="color: #64748B; font-size: 0.95rem; margin: 0;">내가 신청한 모임 일정과 지금까지 참여한 독서 서가를 확인하세요.</p>
    </div>
    """, unsafe_allow_html=True)

    # 세션 스테이트 인증 확인
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    google_user = st.session_state.google_user

    # 🔐 Google 계정 본인 인증
    if not google_user:
        st.info("🔐 '나의 서재 & 모임'을 조회하려면 먼저 Google 계정 본인 인증이 필요합니다.")
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            g_email_input = st.text_input("Google 계정 이메일 주소", placeholder="example@gmail.com", key="bs_google_login_email")
        with col_g2:
            st.write("")
            st.write("")
            login_submitted = st.button("🔑 Google 인증", key="bs_google_login_btn", type="primary", use_container_width=True)

        if login_submitted:
            email_str = g_email_input.strip().lower()
            if "@" not in email_str or "." not in email_str:
                st.error("올바른 Google 이메일 주소를 입력해 주세요.")
            else:
                success, df_sheet, err_msg = fetch_google_sheet_members()
                found_member = None

                if success and df_sheet is not None:
                    email_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이메일", "email", "mail"])), df_sheet.columns[1] if len(df_sheet.columns) > 1 else None)
                    name_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이름", "성함", "name", "성명"])), df_sheet.columns[0] if len(df_sheet.columns) > 0 else None)
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
                    st.success(f"✅ Google 인증 완료! 환영합니다. {found_member['display_name']}님")
                    st.rerun()
        return

    # 인증된 회원 상단 배너 & 로그아웃
    user_disp_name = google_user.get('display_name') or google_user.get('name', '')
    col_u1, col_u2 = st.columns([4, 1])
    with col_u1:
        st.markdown(f"""
        <div class="info-callout" style="background-color: #F0F7FF; border-left-color: #0066CC; color: #003366; padding: 14px; font-size: 1.02rem; border-radius: 12px;">
            <b>📖 {user_disp_name} 님의 서재 & 모임 관리</b><br/>
            <span style="font-size: 0.9rem; color: #4A5568;">계정: {google_user['email']}</span>
        </div>
        """, unsafe_allow_html=True)
    with col_u2:
        st.write("")
        if st.button("🚪 로그아웃", key="bs_logout_btn"):
            st.session_state.google_user = None
            st.rerun()

    st.markdown("---")

    # 2개 탭 구성: 내가 신청한 모임 vs 나의 독서 서가
    tab_upcoming, tab_bookshelf = st.tabs(["📅 내가 신청한 모임 (참여 예정)", "📖 나의 독서 서가 (출석 완료 기록)"])

    # ==========================================
    # 탭 1: 내가 신청한 모임 (참여 예정)
    # ==========================================
    with tab_upcoming:
        all_meetings = get_all_meetings()
        today_date = datetime.date.today()

        u_email = str(google_user.get('email', '')).strip().lower()
        u_disp = str(google_user.get('display_name', '')).strip()
        u_name = str(google_user.get('name', '')).strip()

        my_upcoming_rsvps = []
        for m in all_meetings:
            m_date_str = m.get('meeting_date', '') if isinstance(m, dict) else getattr(m, 'meeting_date', '')
            try:
                m_date = datetime.datetime.strptime(str(m_date_str).strip(), "%Y-%m-%d").date()
            except Exception:
                m_date = today_date

            if m_date >= today_date:
                rsvps = get_rsvps_for_meeting(m['id'])
                my_rsvp = next((
                    r for r in rsvps
                    if (u_email and str(r.get('member_phone', '')).strip().lower() == u_email) or
                       (u_disp and str(r.get('member_name', '')).strip() == u_disp) or
                       (u_name and str(r.get('member_name', '')).strip() == u_name)
                ), None)

                if my_rsvp:
                    my_upcoming_rsvps.append({
                        "meeting": m,
                        "rsvp": my_rsvp,
                        "m_date": m_date
                    })

        # 날짜 오름차순 정렬 (가장 가까운 예정 모임부터)
        my_upcoming_rsvps.sort(key=lambda x: x['m_date'])

        if not my_upcoming_rsvps:
            st.info("📌 현재 참가 신청한 예정된 모임이 없습니다. **'모임 일정 & 신청'** 메뉴에서 함께할 모임에 신청해 보세요! 🪐")
        else:
            st.markdown(f"#### 🗓️ 신청 완료된 예정 모임 ({len(my_upcoming_rsvps)}개)")
            for item in my_upcoming_rsvps:
                m = item['meeting']
                r = item['rsvp']
                p_type = r.get('participation_type') or '자유책'

                # 뱃지 색상
                if "대기" in str(p_type):
                    badge_style = "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;"
                    badge_txt = "⏳ 대기자"
                elif "지정책" in str(p_type):
                    badge_style = "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;"
                    badge_txt = "📕 지정책"
                elif "라운징" in str(p_type):
                    badge_style = "background-color: #EDE9FE; color: #5B21B6; border: 1px solid #C4B5FD;"
                    badge_txt = "🛋️ 라운징"
                else:
                    badge_style = "background-color: #E0F2FE; color: #075985; border: 1px solid #7DD3FC;"
                    badge_txt = "📖 자유책"

                col_c1, col_c2 = st.columns([4, 1])
                with col_c1:
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 0.9rem; font-weight: 700; color: #475569;">🗓️ {m['meeting_date']} {m.get('meeting_time', '')}</span>
                            <span style="padding: 3px 10px; border-radius: 16px; font-size: 0.82rem; font-weight: 700; {badge_style}">{badge_txt}</span>
                        </div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 6px;">
                            {m['title']}
                        </div>
                        <div style="font-size: 0.95rem; color: #334155; margin-bottom: 4px;">
                            📍 <b>장소</b>: {m['location_name']}
                        </div>
                        {f'<div style="font-size: 0.92rem; color: #475569;">📘 <b>책 제목</b>: {m["book_title"]}</div>' if m.get("book_title") and "자율" not in m["book_title"] else ""}
                    </div>
                    """, unsafe_allow_html=True)
                with col_c2:
                    st.write("")
                    st.write("")
                    if st.button("신청 취소", key=f"bs_cancel_{m['id']}", use_container_width=True):
                        with st.spinner("🔄 신청 취소 처리 중입니다..."):
                            cancel_rsvp(m['id'], google_user['id'])
                            m_date_val = m.get('meeting_date', '')
                            cancel_rsvp_from_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m['title'], google_user.get('email', ''), google_user['display_name'], meeting_date=m_date_val)
                            st.toast("✅ 신청이 취소되었습니다.")
                            st.rerun()

    # ==========================================
    # 탭 2: 나의 독서 서가 (출석 완료 기록)
    # ==========================================
    with tab_bookshelf:
        with st.spinner("📚 나의 독서 기록을 불러오는 중..."):
            ok_att, att_df = fetch_google_sheet_attendances()

        my_records = []
        if ok_att and att_df is not None and not att_df.empty:
            u_email = google_user.get('email', '').strip().lower()
            u_name = google_user.get('name', '').strip()
            u_disp = google_user.get('display_name', '').strip()

            for idx, row in att_df.iterrows():
                r_email = str(row.get('회원 이메일', '')).strip().lower()
                r_name = str(row.get('회원 성함', '')).strip()

                is_me = False
                if u_email and r_email and u_email == r_email:
                    is_me = True
                elif u_disp and r_name and u_disp == r_name:
                    is_me = True
                elif u_name and r_name and (u_name == r_name or u_name in r_name or r_name in u_name):
                    is_me = True

                if is_me:
                    date_val = str(row.get('출석 일시 (KST)', '')).strip()
                    meeting_name = str(row.get('모임명', '')).strip()
                    book_raw = str(row.get('도서명', '')).strip()
                    book_review_col = str(row.get('한줄평', '') or row.get('감상평', '') or row.get('review', '')).strip()
                    season_val = str(row.get('시즌 코드', '')).strip() or str(row.get('시즌', '')).strip()

                    book_title = book_raw
                    book_review = book_review_col
                    if " (💬 " in book_raw:
                        parts = book_raw.split(" (💬 ")
                        book_title = parts[0].strip()
                        if not book_review:
                            book_review = parts[1].rstrip(")").strip()

                    author_val = str(row.get('저자명', '') or row.get('저자', '')).strip()
                    rating_val = str(row.get('별점', '')).strip()

                    my_records.append({
                        "date": date_val,
                        "meeting": meeting_name,
                        "book_title": book_title if book_title else "자유책",
                        "book_author": author_val,
                        "rating": rating_val,
                        "book_review": book_review,
                        "season": season_val if season_val else "기타 시즌"
                    })

        if not my_records:
            st.info("📖 아직 기록된 독서/출석 내역이 없습니다. 모임에 참가하고 출석체크를 완료하시면 이곳에 나만의 서재가 완성됩니다! 🪐")
        else:
            df_my = pd.DataFrame(my_records)
            try:
                df_my['parsed_date'] = pd.to_datetime(df_my['date'], errors='coerce')
                df_my = df_my.sort_values(by='parsed_date', ascending=False)
            except Exception:
                df_my = df_my.iloc[::-1]

            total_att = len(df_my)
            unique_books = df_my[df_my['book_title'] != '자유책']['book_title'].nunique()

            gangnam_cnt = df_my['meeting'].str.contains('강남').sum()
            jongno_cnt = df_my['meeting'].str.contains('종각').sum()
            main_loc = "강남" if gangnam_cnt >= jongno_cnt else "종각"

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("🏆 총 참여 횟수", f"{total_att}회")
            with col_s2:
                st.metric("📚 읽은 책 종류", f"{unique_books}권")
            with col_s3:
                st.metric("📍 주 참여 장소", f"{main_loc}")

            st.markdown("---")

            all_seasons = ["전체 보기"] + list(df_my['season'].unique())
            selected_season = st.selectbox("🗓️ 시즌별 필터 선택", all_seasons, key="bookshelf_season_select")

            filtered_df = df_my if selected_season == "전체 보기" else df_my[df_my['season'] == selected_season]

            st.markdown(f"### 🖼️ 나의 독서 서가 ({len(filtered_df)}권)")

            for idx, r in filtered_df.iterrows():
                date_str = r['date'].split()[0] if ' ' in r['date'] else r['date']
                author_text = f" <span style='font-size: 0.9rem; color: #795548;'>({r['book_author']})</span>" if r['book_author'] else ""

                try:
                    r_num = int(float(r['rating'])) if r['rating'] else 0
                    star_text = "⭐" * r_num if r_num > 0 else ""
                except Exception:
                    star_text = ""
                star_badge = f" <span style='font-size: 0.9rem; margin-left: 6px;'>{star_text}</span>" if star_text else ""

                st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #EAE5D9; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <div style="font-size: 0.85rem; color: #8D6E63; font-weight: bold; margin-bottom: 4px;">
                        🗓️ {date_str} | 📌 {r['meeting']}
                    </div>
                    <div style="font-size: 1.15rem; font-weight: bold; color: #3E2723; margin-bottom: 6px;">
                        📖 {r['book_title']}{author_text}{star_badge}
                    </div>
                    {f'<div style="font-size: 0.92rem; color: #5D4037; background-color: #FAF8F5; padding: 10px; border-radius: 8px; margin-top: 6px;">💬 <i>"{r["book_review"]}"</i></div>' if r['book_review'] else ''}
                </div>
                """, unsafe_allow_html=True)
