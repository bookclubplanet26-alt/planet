import streamlit as st
import pandas as pd
from utils import fetch_google_sheet_attendances, fetch_google_sheet_members, format_member_attendance_and_deposit_text, check_member_season_eligibility

def render_bookshelf():
    st.subheader("📚 나의 서재 (My Book Planet)")

    # 세션 스테이트 인증 확인
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    google_user = st.session_state.google_user

    # 🔐 Google 계정 본인 인증
    if not google_user:
        st.markdown("#### 🔐 Google 계정 본인 인증")
        st.info("💡 나의 독서 기록 및 감상평을 확인하려면 먼저 Google 계정 인증을 완료해 주세요.")
        
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            g_email_input = st.text_input("Google 계정 이메일 주소", placeholder="example@gmail.com", key="bookshelf_login_email")
        with col_g2:
            st.write("")
            st.write("")
            login_submitted = st.button("🔑 Google 인증", key="bookshelf_login_btn", type="primary", use_container_width=True)

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
                    st.rerun()
        return

    # 인증된 회원 상단 배너
    if google_user.get('display_name'):
        user_disp_name = google_user['display_name']
    elif google_user.get('name') and google_user.get('nickname'):
        user_disp_name = f"{google_user['name']} - {google_user['nickname']}"
    else:
        user_disp_name = google_user.get('name', '')

    att_txt = format_member_attendance_and_deposit_text(google_user)

    st.markdown(f"""
    <div class="info-callout" style="background-color: #F0F7FF; border-left-color: #0066CC; color: #003366; padding: 16px; font-size: 1.05rem; border-radius: 12px; margin-bottom: 20px;">
        <b>📖 {user_disp_name} 님의 개인 독서 서재</b><br/>
        <span style="font-size: 0.9rem; color: #4A5568;">계정: {google_user['email']}</span><br/>
        <span style="font-size: 0.95rem; color: #003366; margin-top: 4px; display: inline-block;">{att_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    is_elig, _, reason_msg = check_member_season_eligibility(google_user)
    if not is_elig and not (google_user and google_user.get("is_admin", 0) == 1):
        st.markdown(f"""
        <div style="margin: -10px 0 20px 0; padding: 14px 18px; background-color: #FFF3E0; border: 1px solid #FFE082; border-left: 5px solid #FF9800; border-radius: 10px; color: #7F5100; font-size: 0.95rem; line-height: 1.55;">
            <div style="font-weight: bold; font-size: 1.02rem; margin-bottom: 4px; color: #E65100;">📢 시즌 등록 및 예치금 입금 안내</div>
            현재 <b>{reason_msg}</b><br/>
            모임 참가 신청 및 활동을 위해 먼저 <b>이번 시즌 등록(예치금 입금)</b>을 완료해 주세요!
        </div>
        """, unsafe_allow_html=True)

    # 구글 시트 출석 기록에서 본인 데이터 추출
    with st.spinner("📚 나의 독서 기록을 불러오는 중..."):
        ok_att, att_df = fetch_google_sheet_attendances()

    my_records = []
    if ok_att and att_df is not None and not att_df.empty:
        u_email = google_user.get('email', '').strip().lower()
        u_name = google_user.get('name', '').strip()

        for idx, row in att_df.iterrows():
            r_email = str(row.get('회원 이메일', '')).strip().lower()
            r_name = str(row.get('회원 성함', '')).strip()

            # 본인 기록 매칭 (이메일 및 성함 완전/부분 일치)
            is_me = False
            if u_email and r_email and u_email == r_email:
                is_me = True
            elif u_name and r_name and (u_name == r_name or u_name in r_name or r_name in u_name):
                is_me = True

            if is_me:
                date_val = str(row.get('출석 일시 (KST)', '')).strip()
                meeting_name = str(row.get('모임명', '')).strip()
                book_raw = str(row.get('도서명', '')).strip()
                book_review_col = str(row.get('한줄평', '') or row.get('감상평', '') or row.get('review', '')).strip()
                season_val = str(row.get('시즌 코드', '')).strip() or str(row.get('시즌', '')).strip()
                
                # 도서명과 감상평 분리
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
        return

    # 📊 독서 통계 카운터
    df_my = pd.DataFrame(my_records)
    
    # 🗓️ 최신 날짜순 정렬 (내림차순)
    try:
        df_my['parsed_date'] = pd.to_datetime(df_my['date'], errors='coerce')
        df_my = df_my.sort_values(by='parsed_date', ascending=False)
    except Exception:
        df_my = df_my.iloc[::-1]

    total_att = len(df_my)
    unique_books = df_my[df_my['book_title'] != '자유책']['book_title'].nunique()
    
    # 주 장소 통계 (강남/종각/기타)
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

    # 🗓️ 시즌 필터링
    all_seasons = ["전체 보기"] + list(df_my['season'].unique())
    selected_season = st.selectbox("🗓️ 시즌별 필터 선택", all_seasons, key="bookshelf_season_select")

    filtered_df = df_my if selected_season == "전체 보기" else df_my[df_my['season'] == selected_season]

    st.markdown(f"### 🖼️ 나의 독서 서가 ({len(filtered_df)}권)")

    # 🖼️ 카드 갤러리 형태로 도서 서가 표시
    for idx, r in filtered_df.iterrows():
        date_str = r['date'].split()[0] if ' ' in r['date'] else r['date']
        author_text = f" <span style='font-size: 0.9rem; color: #795548;'>({r['book_author']})</span>" if r['book_author'] else ""
        
        # 별점 렌더링
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
