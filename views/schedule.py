from views.calendar_widget import render_season_calendar_2609, render_season_calendar_2610, render_submeeting_calendar
import streamlit as st
import datetime
import html
import pandas as pd
import streamlit.components.v1 as components
from utils import (
    LOCATION_PRESETS, fetch_google_sheet_members, get_member_attendance_count, 
    get_current_kst, format_member_attendance_and_deposit_text, get_member_deposit_info, 
    check_member_season_eligibility, get_all_meetings, get_rsvps_for_meeting,
    add_rsvp, cancel_rsvp, get_meeting_facilitator, get_all_meeting_rsvps_map,
    fetch_google_sheet_meetings, fetch_google_sheet_rsvps
)

# 정규모임 진행자 표시 여부 플래그 (True: 표시, False: 기능 유지한 채 임시 숨김)
SHOW_REGULAR_FACILITATOR = True
# 슈퍼 관리자 이메일 목록 (실시간 새로고침 등 특수 관리 기능 권한)
SUPER_ADMIN_EMAILS = ["hanjisubusiness22@gmail.com"]

if hasattr(st, "dialog"):
    @st.dialog("🗑️ 모임 삭제 확인")
    def confirm_delete_meeting_dialog(m_title, m_date, m_time):
        st.markdown(f"#### **[{m_title}]**")
        st.write(f"🗓️ 일시: **{m_date} {m_time}**")
        st.warning("⚠️ 해당 모임을 정말 삭제하시겠습니까?\n삭제 시 부원들의 모임 목록에서 완전히 제거됩니다.\n(기존 참가 신청자 명단과 출석 기록은 안전하게 보존됩니다)")
        
        c_cancel, c_confirm = st.columns(2)
        with c_cancel:
            if st.button("취소", use_container_width=True, key="dlg_del_cancel_btn"):
                st.rerun()
        with c_confirm:
            if st.button("🗑️ 삭제하기", type="primary", use_container_width=True, key="dlg_del_confirm_btn"):
                from utils import ATTENDANCE_WEBHOOK_URL, delete_meeting_from_google_sheet_async
                delete_meeting_from_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_date)
                del_msg = f"🗑️ '{m_title}' 모임이 삭제되었습니다."
                st.session_state["meeting_deleted_toast"] = del_msg
                st.toast(del_msg, icon="🗑️")
                st.rerun()
else:
    confirm_delete_meeting_dialog = None

def render_meeting_card(meeting, google_user, is_admin, key_prefix="g", is_ended=False, rsvps=None, user_eligibility=None, is_dedicated=False, first_attendees_set=None):
    if rsvps is None:
        rsvps = get_rsvps_for_meeting(meeting['id'], meeting=meeting)
    current_count = len(rsvps)
    max_count = meeting['max_participants']
    
    confirmed_rsvps = [r for r in rsvps if ('participation_type' not in r.keys()) or str(r['participation_type'] or '') != '대기']
    waitlist_rsvps = [r for r in rsvps if ('participation_type' in r.keys()) and str(r['participation_type'] or '') == '대기']
    confirmed_count = len(confirmed_rsvps)
    waitlist_count = len(waitlist_rsvps)

    # 회원 자격 판정 (사전 계산된 값 우선 재사용하여 카드별 중복 연산 제거)
    if user_eligibility is not None:
        is_eligible, reason_type, reason_msg = user_eligibility
    else:
        is_eligible, reason_type, reason_msg = check_member_season_eligibility(google_user) if google_user else (False, "NOT_LOGGED_IN", "Google 인증 필요")

    is_bung = ("소모임" in meeting['title'] or "벙" in meeting['title'] or meeting['book_title'] == "자율 / 소모임")
    is_jijung = (
        not is_bung and (
            "지정책" in meeting['title'] or "지정" in meeting['title'] or "지정책" in (meeting['book_title'] or "") or
            "[책장:" in (meeting['description'] or "") or "[카톡:" in (meeting['description'] or "") or
            (max_count > 0 and max_count < 50 and max_count != 999)
        )
    )

    # 무제한 인원 처리 (정규모임)
    is_unlimited = (
        max_count >= 900 or 
        "자유 도서" in meeting['book_title'] or 
        "자유책" in meeting['book_title'] or 
        "강남 (" in meeting['title'] or 
        "종각 (" in meeting['title']
    )

    desc_raw = meeting['description'] or ""
    leader_name = meeting.get('leader', '') if isinstance(meeting, dict) else getattr(meeting, 'leader', '')
    account_info = meeting.get('account', '') if isinstance(meeting, dict) else getattr(meeting, 'account', '')
    kakao_url = ""
    clean_desc = desc_raw

    if "[책장:" in clean_desc:
        try:
            l_part = clean_desc.split("[책장:")[1].split("]")[0]
            if not leader_name:
                leader_name = l_part.strip()
            clean_desc = clean_desc.replace(f"[책장:{l_part}]", "").strip()
        except Exception:
            pass

    if "[카톡:" in clean_desc:
        try:
            k_part = clean_desc.split("[카톡:")[1].split("]")[0]
            kakao_url = k_part.strip()
            clean_desc = clean_desc.replace(f"[카톡:{k_part}]", "").strip()
        except Exception:
            pass

    if "[계좌:" in clean_desc:
        try:
            a_part = clean_desc.split("[계좌:")[1].split("]")[0]
            if not account_info:
                account_info = a_part.strip()
            clean_desc = clean_desc.replace(f"[계좌:{a_part}]", "").strip()
        except Exception:
            pass

    # 정규모임 판별 및 진행자 조회
    is_regular = is_unlimited or ("강남 (" in meeting['title']) or ("종각 (" in meeting['title']) or ("정규" in meeting['title']) or ("어텀" in meeting['title']) or ("윈터블" in meeting['title'])
    facilitator_name = ""
    if SHOW_REGULAR_FACILITATOR and is_regular and not is_bung and not is_jijung:
        m_date_val = meeting.get('meeting_date', '') if isinstance(meeting, dict) else getattr(meeting, 'meeting_date', '')
        facilitator_name = get_meeting_facilitator(meeting['title'], m_date_val)

    # 상태 계산 및 컴팩트 배지(Chip) 생성
    if is_ended:
        status_chip_html = f'<span class="status-chip chip-ended">🏁 종료 ({confirmed_count}명 완료)</span>'
        is_full = True
        is_waitlist_mode = False
    elif is_unlimited:
        status_chip_html = f'<span class="status-chip chip-available">🟢 신청가능 ({confirmed_count}명)</span>'
        is_full = False
        is_waitlist_mode = False
    else:
        is_full = (confirmed_count >= max_count)
        if is_full:
            if waitlist_count > 0:
                status_chip_html = f'<span class="status-chip chip-full">🔴 마감 ({confirmed_count}/{max_count}명)</span> <span class="status-chip chip-wait">⏳ 대기 {waitlist_count}명</span>'
            else:
                status_chip_html = f'<span class="status-chip chip-full">🔴 마감 ({confirmed_count}/{max_count}명)</span> <span class="status-chip chip-wait">⏳ 대기 가능</span>'
            is_waitlist_mode = True
        else:
            status_chip_html = f'<span class="status-chip chip-available">🟢 신청가능 ({confirmed_count}/{max_count}명)</span>'
            is_waitlist_mode = False

    # 첫출석 신청자 수 사전 집계 (운영진 요약 표시용)
    first_count = 0
    if is_admin and first_attendees_set and rsvps:
        for r in rsvps:
            r_email = str(r.get('member_phone') or '').strip().lower()
            r_name_clean = str(r.get('member_name') or '').strip()
            base_name = r_name_clean.split(' - ')[0].strip() if ' - ' in r_name_clean else r_name_clean
            if (r_email and r_email in first_attendees_set) or (r_name_clean and r_name_clean in first_attendees_set) or (base_name and base_name in first_attendees_set):
                first_count += 1

    if is_admin and first_count > 0:
        status_chip_html += f' <span class="status-chip" style="background:#E8F5E9; color:#2E7D32; border:1px solid #A5D6A7; font-weight:600;">🌱 첫출석 {first_count}명</span>'

    # 독립된 모임 카드 컨테이너
    with st.container(border=True):
        m_title = meeting['title'] if isinstance(meeting, dict) or hasattr(meeting, '__getitem__') else getattr(meeting, 'title', '')
        import html
        m_title_safe = html.escape(str(m_title))
        m_date = meeting['meeting_date'] if (isinstance(meeting, dict) and 'meeting_date' in meeting) or (hasattr(meeting, 'keys') and 'meeting_date' in meeting.keys()) else ""
        m_id = meeting['id']

        # 1. 헤더 (제목 + 상태 배지 + 삭제 권한 체크 및 버튼)
        leader_html = ""
        if leader_name:
            role_label = "모임장" if is_bung else "지정책장"
            leader_html = f"<div class='meeting-leader-badge'>👤 <b>{role_label}</b>: <span>{leader_name}</span></div>"
        elif SHOW_REGULAR_FACILITATOR and is_regular and facilitator_name:
            if facilitator_name == "미정":
                leader_html = "<div class='meeting-leader-badge' style='background:#F7F7F7; border-color:#E0E0E0;'>👤 <b style='color:#757575;'>진행자</b>: <span style='background:#EEEEEE; color:#616161;'>미정</span></div>"
            else:
                leader_html = f"<div class='meeting-leader-badge'>👤 <b>진행자</b>: <span>{facilitator_name}</span></div>"

        # 삭제 권한 판정: 관리자는 모든 모임 삭제 가능, 열심멤버는 본인이 개설한 모임(정규모임 제외)만 삭제 가능
        is_my_meeting = False
        if google_user and leader_name:
            u_disp = str(google_user.get('display_name', '')).strip()
            u_name = str(google_user.get('name', '')).strip()
            u_nick = str(google_user.get('nickname', '')).strip()
            u_email = str(google_user.get('email', '')).strip().lower()
            l_str = str(leader_name).strip()

            if l_str == u_disp or l_str == u_name or (u_nick and l_str == u_nick):
                is_my_meeting = True
            elif u_name and u_name in l_str:
                if not u_nick or u_nick in l_str:
                    is_my_meeting = True
            elif u_email and u_email in l_str.lower():
                is_my_meeting = True

        can_delete = is_admin or (is_dedicated and is_my_meeting and not is_regular)

        if can_delete:
            col_t1, col_t2 = st.columns([5, 1])
            with col_t1:
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:6px;">'
                    f'<div class="meeting-card-title">📖 {m_title_safe}</div>'
                    f'<div>{status_chip_html}</div>'
                    f'</div>', 
                    unsafe_allow_html=True
                )
                if leader_html:
                    st.markdown(leader_html, unsafe_allow_html=True)
            with col_t2:
                if confirm_delete_meeting_dialog is not None:
                    if st.button("❌", key=f"{key_prefix}_del_m_{m_id}", help="이 모임을 목록에서 삭제합니다"):
                        m_time_str = meeting.get('meeting_time', '') if isinstance(meeting, dict) or hasattr(meeting, '__getitem__') else getattr(meeting, 'meeting_time', '')
                        confirm_delete_meeting_dialog(m_title, m_date, m_time_str)
                else:
                    with st.popover("❌", help="이 모임을 목록에서 삭제합니다"):
                        st.markdown(f"**[{m_title}]**")
                        st.caption(f"🗓️ {m_date}")
                        st.warning("⚠️ 해당 모임을 삭제하시겠습니까?")
                        if st.button("🗑️ 확인 (삭제)", key=f"{key_prefix}_del_confirm_{m_id}", type="primary", use_container_width=True):
                            from utils import ATTENDANCE_WEBHOOK_URL, delete_meeting_from_google_sheet_async
                            delete_meeting_from_google_sheet_async(ATTENDANCE_WEBHOOK_URL, m_title, m_date)
                            del_msg = f"🗑️ '{m_title}' 모임이 삭제되었습니다."
                            st.session_state["meeting_deleted_toast"] = del_msg
                            st.toast(del_msg, icon="🗑️")
                            st.rerun()
        else:
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:6px;">'
                f'<div class="meeting-card-title">📖 {m_title_safe}</div>'
                f'<div>{status_chip_html}</div>'
                f'</div>', 
                unsafe_allow_html=True
            )
            if leader_html:
                st.markdown(leader_html, unsafe_allow_html=True)

        # 2. 본문 정보 영역 (마크다운 인덴트 오류 방지 - 공백 없는 한 덩어리 HTML)
        safe_date = html.escape(str(meeting.get("meeting_date", "")).strip())
        safe_time = html.escape(str(meeting.get("meeting_time", "")).strip())
        safe_loc = html.escape(str(meeting.get("location_name", "")).strip())
        meta_items = [
            f'<div class="meeting-meta-item">🗓️ <span style="color:#6D4C41; font-weight:600;">일시:</span> <span class="meta-strong" style="font-size:1.02rem;">{safe_date} {safe_time}</span></div>',
            f'<div class="meeting-meta-item">📍 <span style="color:#6D4C41; font-weight:600;">장소:</span> <span class="meta-strong">{safe_loc}</span></div>'
        ]

        if not is_bung:
            if is_unlimited:
                meta_items.append('<div class="meeting-meta-item">📘 <span style="color:#6D4C41; font-weight:600;">모임형태:</span> <span class="meta-strong">자유책 (각자 읽은 책 지참)</span></div>')
            else:
                safe_book = html.escape(str(meeting.get("book_title", "자유 도서")).strip())
                meta_items.append(f'<div class="meeting-meta-item">📘 <span style="color:#6D4C41; font-weight:600;">선정도서:</span> <span class="meta-strong">{safe_book}</span></div>')
                m_author = str(meeting.get('author', '')).strip() if meeting.get('author') else ""
                if m_author and m_author.lower() not in ["자율", "nan", "none", "null"]:
                    safe_author = html.escape(m_author)
                    meta_items.append(f'<div class="meeting-meta-item">✍️ <span style="color:#6D4C41; font-weight:600;">저자:</span> <span class="meta-strong">{safe_author}</span></div>')

        if is_jijung and account_info:
            clean_acc = str(account_info).strip()
            if clean_acc and clean_acc.lower() not in ["nan", "none", "null"]:
                if google_user:
                    safe_account = html.escape(clean_acc, quote=True)
                    copy_btn_html = (
                        f'<span role="button" class="copy-account-btn" data-account="{safe_account}" '
                        f'style="display:inline-block; margin-left:8px; padding:2px 8px; font-size:0.78rem; font-weight:600; '
                        f'color:#5D4037; background-color:#F5F0EB; border:1px solid #D7CCC8; border-radius:6px; '
                        f'cursor:pointer; vertical-align:middle; user-select:none; -webkit-user-select:none;" '
                        f'title="계좌번호 복사">📋 복사</span>'
                    )
                    meta_items.append(f'<div class="meeting-meta-item">🏦 <span style="color:#6D4C41; font-weight:600;">입금계좌:</span> <span class="meta-strong">{safe_account}</span>{copy_btn_html}</div>')
                else:
                    meta_items.append('<div class="meeting-meta-item">🏦 <span style="color:#6D4C41; font-weight:600;">입금계좌:</span> <span style="color:#888; font-size:0.9rem;">(🔒 이메일 로그인 후 공개)</span></div>')

        if clean_desc and clean_desc.strip():
            safe_desc = html.escape(clean_desc.strip()).replace("\n", "<br/>")
            if is_jijung or is_bung:
                desc_html = (
                    f'<div class="meeting-meta-item" style="margin-top:8px; padding-top:8px; border-top:1px dashed #EAE5D9;">'
                    f'<details class="meeting-desc-details">'
                    f'<summary style="cursor:pointer; font-weight:600; color:#6D4C41; user-select:none; outline:none;">'
                    f'📝 <span style="color:#6D4C41; font-weight:600;">모임안내</span>'
                    f'<span class="desc-toggle-badge" style="font-size:0.82rem; color:#8D6E63; font-weight:normal; margin-left:4px;">(펼치기)</span>'
                    f'<span class="desc-close-badge" style="display:none; font-size:0.82rem; color:#8D6E63; font-weight:normal; margin-left:4px;">(접기)</span>'
                    f'</summary>'
                    f'<div class="meeting-desc-text" style="margin-top:8px;">{safe_desc}</div>'
                    f'</details>'
                    f'</div>'
                )
            else:
                desc_html = (
                    f'<div class="meeting-meta-item" style="margin-top:8px; padding-top:8px; border-top:1px dashed #EAE5D9;">'
                    f'📝 <span style="color:#6D4C41; font-weight:600;">모임안내:</span>'
                    f'<div class="meeting-desc-text">{safe_desc}</div>'
                    f'</div>'
                )
            meta_items.append(desc_html)

        meta_box_html = f'<div class="meeting-meta-box">{"".join(meta_items)}</div>'
        st.markdown(meta_box_html, unsafe_allow_html=True)

        # 3. 오픈 카카오톡방 주소 (시즌 회원에게 전용 링크 버튼 제공 - 프로토콜 검증 및 XSS 방어)
        clean_k_url = str(kakao_url).strip() if kakao_url else ""
        if clean_k_url and clean_k_url.lower() not in ["nan", "none", "null"]:
            if clean_k_url.startswith(("https://", "http://")):
                safe_k_url = html.escape(clean_k_url, quote=True)
                if is_eligible or is_admin:
                    kakao_btn_html = f'<div style="margin:6px 0 10px 0;"><a href="{safe_k_url}" target="_blank" rel="noopener noreferrer" class="kakao-link-btn">💬 <b>오픈 카톡방 입장하기</b> ↗</a></div>'
                    st.markdown(kakao_btn_html, unsafe_allow_html=True)
                else:
                    st.warning("🔒 오픈 카톡방 주소는 **이번 시즌 등록 회원**에게만 공개됩니다. 먼저 시즌 등록을 해주세요.")

        # 4. 신청 및 취소 액션
        already_rsvp = False
        if google_user and any(r['member_phone'] == google_user['email'] or r['member_name'] == google_user['display_name'] for r in rsvps):
            already_rsvp = True

        if is_ended:
            if already_rsvp:
                st.caption("✅ 이전 참가 신청했던 모임입니다.")
        elif google_user:
            if already_rsvp:
                st.info("✅ 이미 신청 완료된 모임입니다.")
                if st.button("신청 취소하기", key=f"{key_prefix}_cancel_{meeting['id']}", use_container_width=True):
                    with st.spinner("신청 취소 중..."): 
                        cancel_rsvp(meeting['id'], google_user['id'], member_name=google_user['display_name'], member_phone=google_user.get('email', ''))
                        st.toast("✅ 신청이 취소되었습니다.")
                        st.rerun()
            else:
                if not is_eligible and not is_admin:
                    st.warning(f"""
                    🚫 **모임 신청 제한 (시즌 등록 필요)**  
                    {reason_msg}  
                    📌 모든 모임에 참여하시려면 **이번 시즌 예치금 입금 및 등록**을 먼저 완료해 주세요!
                    """)
                else:
                    if is_waitlist_mode:
                        selected_part_type = "대기"
                        btn_label = "⏳ 대기 신청하기"
                    elif is_jijung:
                        selected_part_type = "지정책"
                        st.caption("💡 **지정책 모임**: 지정된 도서로 발제 및 토론을 진행하며, **출석 1회**로 인정됩니다.")
                        btn_label = "🚀 참가 신청하기"
                    elif is_bung:
                        selected_part_type = "참석"
                        btn_label = "🚀 참가 신청하기"
                    else:
                        part_choice = st.radio(
                            "참여 방식을 선택하세요",
                            ["📖 자유책 (출석 1회)", "📕 지정책 (출석 1회)", "🛋️ 라운징 (출석 0.5회)"],
                            horizontal=True,
                            key=f"{key_prefix}_part_radio_{meeting['id']}"
                        )
                        if "지정책" in part_choice:
                            selected_part_type = "지정책"
                            st.caption("💡 **지정책 안내**: 선정도서를 읽고 발제 및 토론에 참여하며, **출석 1회**로 인정됩니다.")
                        elif "라운징" in part_choice:
                            selected_part_type = "라운징"
                            st.caption("💡 **라운징 안내**: 발제 및 토론 없이 편하게 자유 독서를 하는 방식으로, **출석 0.5회**로 인정됩니다.")
                        else:
                            selected_part_type = "자유책"
                            st.caption("💡 **자유책 안내**: 각자 읽은 책을 지참하여 자유롭게 소통하며, **출석 1회**로 인정됩니다.")
                        btn_label = "🚀 참가 신청하기"

                    user_comment = st.text_input(
                        "💬 한마디 (선택)",
                        placeholder="모임에 전하고 싶은 한마디를 남겨주세요 (최대 25자)",
                        max_chars=30,
                        key=f"{key_prefix}_comment_{meeting['id']}"
                    )

                    btn_disabled = (is_full and not is_waitlist_mode)
                    if st.button(btn_label, key=f"{key_prefix}_rsvp_{meeting['id']}", disabled=btn_disabled, type="primary", use_container_width=True):
                        with st.spinner("참가 신청 중..."): 
                            success, msg = add_rsvp(meeting['id'], google_user['id'], google_user['display_name'], google_user['email'], selected_part_type, comment=user_comment)
                            if success:
                                toast_msg = "대기 신청이 완료되었습니다!" if selected_part_type == "대기" else "참가 신청이 완료되었습니다!"
                                st.toast(f"✅ [{google_user['display_name']}] 님, {toast_msg}", icon="🎉")
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.warning("⚠️ 참가 신청을 위해 먼저 상단에서 Google 계정 인증을 완료해 주세요.")

        # 5. 참석자 명단 expander (카드 내부 하단, 기본 접힘)
        # 유형별 신청 인원 집계 (신청자가 있는 항목만 동적으로 표시)
        c_free = 0
        c_jijung = 0
        c_lounge = 0
        c_attend = 0
        c_wait = 0
        if rsvps:
            for r in rsvps:
                pt = str(r.get('participation_type') or '자유책')
                if "대기" in pt:
                    c_wait += 1
                elif "지정책" in pt:
                    c_jijung += 1
                elif "라운징" in pt:
                    c_lounge += 1
                elif "참석" in pt:
                    c_attend += 1
                else:
                    c_free += 1

        type_parts = []
        if c_free > 0:
            type_parts.append(f"📖 자유책 {c_free}명")
        if c_jijung > 0:
            type_parts.append(f"📕 지정책 {c_jijung}명")
        if c_lounge > 0:
            type_parts.append(f"🛋️ 라운징 {c_lounge}명")
        if c_attend > 0:
            type_parts.append(f"\u2615\ufe0f 참석 {c_attend}명")
        if c_wait > 0:
            type_parts.append(f"⏳ 대기 {c_wait}명")

        summary_str = f" : {' · '.join(type_parts)}" if type_parts else ""
        first_str = f" / 🌱 첫출석 {first_count}명" if (is_admin and first_count > 0) else ""
        expander_title = f"👥 참석 명단 ({current_count}명{summary_str}{first_str})"

        with st.expander(expander_title, expanded=False):
            if rsvps:
                def _part_order(r):
                    pt = str(r.get('participation_type') or '자유책')
                    if "자유책" in pt:
                        return 1
                    if "지정책" in pt:
                        return 2
                    if "라운징" in pt:
                        return 3
                    if "참석" in pt:
                        return 4
                    if "대기" in pt:
                        return 5
                    return 6

                sorted_rsvps = sorted(rsvps, key=_part_order)
                for r in sorted_rsvps:
                    m_name = (r.get('member_name') or '').strip()
                    if not m_name:
                        m_name = (r.get('member_phone') or '').split('@')[0] if r.get('member_phone') else '회원'
                    p_type = r['participation_type'] if 'participation_type' in r.keys() and r['participation_type'] else '자유책'

                    # 첫출석 뱃지 판정 (운영진에게만 표시: 🌱이름 형식)
                    first_prefix = ""
                    if is_admin and first_attendees_set:
                        r_email = str(r.get('member_phone') or '').strip().lower()
                        r_name_clean = str(r.get('member_name') or '').strip()
                        is_first = False
                        if r_email and r_email in first_attendees_set:
                            is_first = True
                        elif r_name_clean and r_name_clean in first_attendees_set:
                            is_first = True
                        elif r_name_clean:
                            base_name = r_name_clean.split(' - ')[0].strip() if ' - ' in r_name_clean else r_name_clean
                            if base_name in first_attendees_set:
                                is_first = True

                        if is_first:
                            first_prefix = "🌱"

                    import html
                    r_comment = str(r.get('comment') or '').strip().replace("\n", " ")
                    if len(r_comment) > 22:
                        r_comment = r_comment[:20] + "…"
                    safe_comment = html.escape(r_comment)
                    comment_suffix = f' <span style="background:#F4F1EA; color:#5D4037; padding:2px 8px; border-radius:6px; font-size:0.83rem; border:1px solid #E5E0D6; margin-left:4px; display:inline-block; vertical-align:middle; line-height:1.3;">💬 {safe_comment}</span>' if r_comment else ""

                    safe_m_name = html.escape(m_name)
                    if "대기" in str(p_type):
                        st.markdown(f"• **{first_prefix}{safe_m_name}** (⏳){comment_suffix}", unsafe_allow_html=True)
                    elif "지정책" in str(p_type):
                        st.markdown(f"• **{first_prefix}{safe_m_name}** (📕){comment_suffix}", unsafe_allow_html=True)
                    elif "라운징" in str(p_type):
                        st.markdown(f"• **{first_prefix}{safe_m_name}** (🛋️){comment_suffix}", unsafe_allow_html=True)
                    elif "자유책" in str(p_type):
                        st.markdown(f"• **{first_prefix}{safe_m_name}** (📖){comment_suffix}", unsafe_allow_html=True)
                    elif "참석" in str(p_type):
                        st.markdown(f'• **{first_prefix}{safe_m_name}** (<span style="font-family:\'Segoe UI Emoji\',\'Apple Color Emoji\',sans-serif;">\u2615\ufe0f</span>){comment_suffix}', unsafe_allow_html=True)
                    else:
                        st.markdown(f"• **{first_prefix}{safe_m_name}**{comment_suffix}", unsafe_allow_html=True)
            else:
                st.write("아직 참가 신청자가 없습니다.")



def render_schedule():
    # 세션 스테이트 초기화
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    google_user = st.session_state.google_user
    user_email = (google_user.get("email") or "").strip().lower() if google_user else ""
    is_super_admin = bool(user_email and user_email in SUPER_ADMIN_EMAILS)

    if is_super_admin:
        col_hdr1, col_hdr2 = st.columns([4, 1.2])
        with col_hdr1:
            st.subheader("📅 모임 일정 및 신청")
        with col_hdr2:
            if st.button("🔄 실시간 새로고침", key="sched_force_refresh_btn", help="구글 시트의 최신 모임 및 신청자 명단을 즉시 다시 불러옵니다"):
                fetch_google_sheet_meetings.clear()
                fetch_google_sheet_rsvps.clear()
                st.cache_data.clear()
                st.rerun()
    else:
        st.subheader("📅 모임 일정 및 신청")

    # 계좌번호 원클릭 클립보드 복사 이벤트 리스너 주입 (window.parent.document 위임)
    copy_script = """
    <script>
    (function() {
        try {
            var doc = window.parent.document;
            if (doc._accountCopyAttached) return;
            doc._accountCopyAttached = true;

            doc.addEventListener('click', function(e) {
                var btn = e.target.closest('.copy-account-btn');
                if (!btn) return;
                var text = btn.getAttribute('data-account') || '';
                if (!text) return;

                function showSuccess() {
                    var origHtml = btn.getAttribute('data-orig-html') || btn.innerHTML;
                    btn.setAttribute('data-orig-html', origHtml);
                    btn.innerHTML = '✅ 복사완료';
                    btn.style.borderColor = '#4CAF50';
                    btn.style.color = '#2E7D32';
                    btn.style.backgroundColor = '#E8F5E9';
                    setTimeout(function() {
                        btn.innerHTML = origHtml;
                        btn.style.borderColor = '#D7CCC8';
                        btn.style.color = '#5D4037';
                        btn.style.backgroundColor = '#F5F0EB';
                    }, 1500);
                }

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(showSuccess).catch(function() {
                        fallbackCopy(text);
                    });
                } else {
                    fallbackCopy(text);
                }

                function fallbackCopy(textVal) {
                    try {
                        var ta = doc.createElement('textarea');
                        ta.value = textVal;
                        ta.style.position = 'fixed';
                        ta.style.left = '-9999px';
                        ta.style.top = '-9999px';
                        ta.style.opacity = '0';
                        doc.body.appendChild(ta);
                        ta.focus();
                        ta.select();
                        var ok = doc.execCommand('copy');
                        doc.body.removeChild(ta);
                        if (ok) {
                            showSuccess();
                        } else {
                            prompt('계좌번호를 복사하세요:', textVal);
                        }
                    } catch (err) {
                        prompt('계좌번호를 복사하세요:', textVal);
                    }
                }
            });
        } catch (err) {
            console.error('Account copy setup failed:', err);
        }
    })();
    </script>
    """
    components.html(copy_script, height=0, width=0)

    # 🗓️ 2609 시즌 캘린더 전체보기 (접기/펼치기)
    with st.expander("🗓️ 2609 시즌 캘린더 전체보기 (9/12 ~ 11/1)", expanded=False):
        render_season_calendar_2609()

    # 🗓️ 2610 시즌 캘린더 전체보기 (접기/펼치기)
    with st.expander("🗓️ 2610 시즌 캘린더 전체보기 (10/3 ~ 11/29)", expanded=False):
        render_season_calendar_2610()

    meetings = get_all_meetings()

    # 📚 지정책 & 소모임 캘린더 (접기/펼치기)
    with st.expander("📚 지정책 & 소모임 캘린더", expanded=False):
        render_submeeting_calendar(meetings)

    # 리셋 플래그 처리 (widget 생성 전 세션 스테이트 설정)
    if "reset_admin_category" in st.session_state and st.session_state["reset_admin_category"]:
        st.session_state["admin_category_select"] = "선택해주세요"
        st.session_state["reset_admin_category"] = False

    # 모임 개설 완료 메시지 알림 (toast & banner)
    if "meeting_created_toast" in st.session_state and st.session_state["meeting_created_toast"]:
        msg = st.session_state["meeting_created_toast"]
        st.toast(msg, icon="🎉")
        st.session_state["meeting_created_toast"] = None

    # 모임 삭제 완료 메시지 알림 (toast & banner)
    if "meeting_deleted_toast" in st.session_state and st.session_state["meeting_deleted_toast"]:
        msg = st.session_state["meeting_deleted_toast"]
        st.toast(msg, icon="🗑️")
        st.session_state["meeting_deleted_toast"] = None

    is_admin = bool(google_user and google_user.get("is_admin", 0) == 1)
    is_dedicated = bool(google_user and google_user.get("is_dedicated", 0) == 1)
    can_create_meeting = (is_admin or is_dedicated)

    # 탭 구성: 관리자 또는 열심멤버일 경우 '➕ 새 모임 개설' 탭 제공
    if can_create_meeting:
        tab1, tab2 = st.tabs(["📚 예정된 모임 목록", "➕ 새 모임 개설"])
    else:
        tab1, = st.tabs(["📚 예정된 모임 목록"])
        tab2 = None

    with tab1:
        rsvps_map = get_all_meeting_rsvps_map(meetings)
        dep_info = get_member_deposit_info(
            user_email=google_user.get('email', ''),
            user_name=google_user.get('display_name', google_user.get('name', '')),
            user_season=google_user.get('season')
        ) if google_user else None
        try:
            user_eligibility = check_member_season_eligibility(google_user, dep=dep_info) if google_user else (False, "NOT_LOGGED_IN", "로그인 필요")
        except TypeError:
            user_eligibility = check_member_season_eligibility(google_user) if google_user else (False, "NOT_LOGGED_IN", "로그인 필요")

        # 운영진 전용 첫출석 대상자 집합 생성 (초고속 O(1) 매핑)
        first_attendees_set = set()
        if is_admin:
            try:
                success_m, df_members, _ = fetch_google_sheet_members()
                if success_m and df_members is not None:
                    first_col = next((c for c in df_members.columns if any(k in str(c).lower() for k in ["첫출석", "첫 출석", "first_attend"])), None)
                    email_col = next((c for c in df_members.columns if any(k in str(c).lower() for k in ["이메일", "email", "mail"])), None)
                    name_col = next((c for c in df_members.columns if any(k in str(c).lower() for k in ["이름", "성함", "name"])), None)
                    nick_col = next((c for c in df_members.columns if any(k in str(c).lower() for k in ["닉네임", "별명", "nick"])), None)

                    if first_col:
                        for _, r in df_members.iterrows():
                            val = str(r.get(first_col, '')).strip()
                            if val in ['1', 'Y', 'y', 'TRUE', 'true']:
                                if email_col and pd.notna(r.get(email_col)):
                                    em = str(r[email_col]).strip().lower()
                                    if em:
                                        first_attendees_set.add(em)
                                if name_col and pd.notna(r.get(name_col)):
                                    u_n = str(r[name_col]).strip()
                                    if u_n:
                                        first_attendees_set.add(u_n)
                                        if nick_col and pd.notna(r.get(nick_col)):
                                            u_nk = str(r[nick_col]).strip()
                                            if u_nk:
                                                first_attendees_set.add(f"{u_n} - {u_nk}")
            except Exception:
                pass

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
                    with st.spinner("회원 정보 확인 중..."): 
                        success, df_sheet, err_msg = fetch_google_sheet_members()
                    found_member = None

                    if success and df_sheet is not None:
                        email_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이메일", "email", "mail"])), df_sheet.columns[1] if len(df_sheet.columns)>1 else None)
                        name_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["이름", "성함", "name", "성명"])), df_sheet.columns[0] if len(df_sheet.columns)>0 else None)
                        nick_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["닉네임", "별명", "nick"])), df_sheet.columns[-1] if len(df_sheet.columns)>5 else None)
                        reg_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록", "상태", "reg", "status"])), None)
                        admin_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["운영진", "관리자", "admin"])), None)
                        season_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["등록시즌", "등록 시즌", "시즌"])), None)
                        dedicated_col = next((c for c in df_sheet.columns if any(k in str(c).lower() for k in ["열심멤버", "열심", "dedicated"])), None)

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

                                raw_dedicated = str(r[dedicated_col]).strip() if dedicated_col and pd.notna(r[dedicated_col]) else "0"
                                dedicated_val = 1 if raw_dedicated in ["1", "열심", "열심멤버", "True", "true", "Y", "y"] else 0

                                found_member = {
                                    "id": hash(email_str) % 100000,
                                    "name": u_name,
                                    "nickname": u_nick,
                                    "display_name": f"{u_name} - {u_nick}" if u_nick else u_name,
                                    "email": email_str,
                                    "season": u_season,
                                    "registered": reg_val,
                                    "is_admin": admin_val,
                                    "is_dedicated": dedicated_val
                                }

                    if not found_member:
                        st.error("🚨 미등록 회원입니다. 모임장에게 연락해 주세요.")
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
            admin_badge = " [👑 운영진]" if is_admin else (" [🔥 열심멤버]" if is_dedicated else "")
            try:
                att_txt = format_member_attendance_and_deposit_text(google_user, dep=dep_info, user_eligibility=user_eligibility)
            except TypeError:
                att_txt = format_member_attendance_and_deposit_text(google_user)
            if not att_txt:
                from utils import format_season_display
                m_season = google_user.get('season')
                season_label = format_season_display(m_season)
                att_cnt = dep_info['current_count'] if dep_info else get_member_attendance_count(google_user['email'], google_user['display_name'], target_season=m_season)
                att_txt = f"🏆 {season_label} 출석 횟수: <b>{att_cnt}회</b>"
            
            st.markdown(f"""
            <div class="info-callout" style="background-color: #E8F0FE; border-left-color: #1A73E8; color: #174EA6; padding: 16px; font-size: 1.05rem;">
                <b>✅ Google 인증 완료{admin_badge}:</b><br/>
                환영합니다. <b>{google_user['name']} - {google_user['nickname']}</b> ({google_user['email']})<br/>
                <span style="font-size: 0.98rem; color: #185ABC;">{att_txt}</span>
            </div>
            """, unsafe_allow_html=True)
            
            is_elig, reason_type, reason_msg = user_eligibility
            if not is_elig and not is_admin:
                if reason_type == "PRE_REGISTERED":
                    st.markdown(f"""
                    <div style="margin: 10px 0 16px 0; padding: 14px 18px; background-color: #E8F5E9; border: 1px solid #A5D6A7; border-left: 5px solid #4CAF50; border-radius: 10px; color: #1B5E20; font-size: 0.95rem; line-height: 1.55;">
                        <div style="font-weight: bold; font-size: 1.02rem; margin-bottom: 4px; color: #2E7D32;">🌱 차기 시즌 사전 등록 완료</div>
                        <b>{reason_msg}</b><br/>
                        시즌 시작일 이후 열리는 모임부터 참가 신청 및 활동이 활성화됩니다.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="margin: 10px 0 16px 0; padding: 14px 18px; background-color: #FFF3E0; border: 1px solid #FFE082; border-left: 5px solid #FF9800; border-radius: 10px; color: #7F5100; font-size: 0.95rem; line-height: 1.55;">
                        <div style="font-weight: bold; font-size: 1.02rem; margin-bottom: 4px; color: #E65100;">📢 시즌 등록 및 예치금 입금 안내</div>
                        <b>{reason_msg}</b><br/>
                        정규모임, 지정책, 소모임/벙 등 모든 모임 참가 신청 및 지정책 오픈 카톡방 열람을 위해 먼저 <b>이번 시즌 등록(예치금 입금)</b>을 완료해 주세요!
                    </div>
                    """, unsafe_allow_html=True)

            if is_admin:
                st.success("👑 **운영진(관리자) 권한이 확인되었습니다.** 상단 탭에 '➕ 새 모임 개설' 메뉴가 추가되었으며, 각 모임 우측 ❌ 삭제 버튼으로 모임을 삭제할 수 있습니다.")
            elif is_dedicated:
                st.success("🔥 **열심멤버 권한이 확인되었습니다.** 상단 탭에 '➕ 새 모임 개설' 메뉴에서 지정책 및 소모임/벙을 개설할 수 있으며, 직접 개설한 모임은 ❌ 삭제할 수 있습니다.")

            if st.button("🚪 다른 이메일로 인증 (로그아웃)", key="google_logout_btn"):
                st.session_state.google_user = None
                st.rerun()

        st.markdown("---")

        # 모임 날짜 기준으로 예정된 모임과 지난 모임(최근 60일 내) 분류
        today_date = get_current_kst().date()
        from datetime import timedelta
        cutoff_date = today_date - timedelta(days=60)

        upcoming_meetings = []
        past_meetings = []

        for m in meetings:
            m_date_str = m['meeting_date'] if (isinstance(m, dict) and 'meeting_date' in m) else getattr(m, 'meeting_date', '')
            try:
                m_date = datetime.datetime.strptime(str(m_date_str).strip(), "%Y-%m-%d").date()
            except Exception:
                m_date = today_date

            if m_date >= today_date:
                upcoming_meetings.append(m)
            elif m_date >= cutoff_date:
                past_meetings.append(m)

        # 🕒 지난 모임은 최신순(최근 일시가 위)으로 정렬
        past_meetings.sort(
            key=lambda x: (
                str(x.get('meeting_date', '') if isinstance(x, dict) else getattr(x, 'meeting_date', '')),
                str(x.get('meeting_time', '') if isinstance(x, dict) else getattr(x, 'meeting_time', ''))
            ),
            reverse=True
        )

        # 예정된 모임은 다가오는 순(가까운 일시가 위)으로 정렬
        upcoming_meetings.sort(
            key=lambda x: (
                str(x.get('meeting_date', '') if isinstance(x, dict) else getattr(x, 'meeting_date', '')),
                str(x.get('meeting_time', '') if isinstance(x, dict) else getattr(x, 'meeting_time', ''))
            )
        )

        bung_meetings = [
            m for m in upcoming_meetings 
            if ("소모임" in m['title'] or "벙" in m['title'] or m['book_title'] == "자율 / 소모임")
        ]
        jijung_meetings = [
            m for m in upcoming_meetings 
            if m not in bung_meetings and (
                "지정책" in m['title'] or "지정" in m['title'] or "지정책" in (m['book_title'] or "") or
                "[책장:" in (m['description'] or "") or "[카톡:" in (m['description'] or "") or
                (m['max_participants'] > 0 and m['max_participants'] < 50 and m['max_participants'] != 999)
            )
        ]
        regular_meetings = [
            m for m in upcoming_meetings 
            if m not in bung_meetings and m not in jijung_meetings
        ]

        # 📌 한 줄 4개 탭 구성 (정규모임 | 지정책 | 소모임/벙 | 지난 모임)
        m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs([
            f"📅 정규모임 ({len(regular_meetings)})", 
            f"📖 지정책 ({len(jijung_meetings)})", 
            f"\u2615\ufe0f 소모임 / 벙 ({len(bung_meetings)})",
            f"📜 지난 모임 ({len(past_meetings)})"
        ])

        with m_tab1:
            if not regular_meetings:
                st.info("현재 예정된 정규모임이 없습니다.")
            else:
                for meeting in regular_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="reg_m", rsvps=rsvps_map.get(meeting['id'], []), user_eligibility=user_eligibility, is_dedicated=is_dedicated, first_attendees_set=first_attendees_set)

        with m_tab2:
            if not jijung_meetings:
                st.info("현재 예정된 지정책 모임이 없습니다.")
            else:
                for meeting in jijung_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="jijung_m", rsvps=rsvps_map.get(meeting['id'], []), user_eligibility=user_eligibility, is_dedicated=is_dedicated, first_attendees_set=first_attendees_set)

        with m_tab3:
            if not bung_meetings:
                st.info("현재 예정된 소모임 및 벙 모임이 없습니다.")
            else:
                for meeting in bung_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="bung_m", rsvps=rsvps_map.get(meeting['id'], []), user_eligibility=user_eligibility, is_dedicated=is_dedicated, first_attendees_set=first_attendees_set)

        with m_tab4:
            if not past_meetings:
                st.info("진행된 지난 모임 기록이 없습니다.")
            else:
                st.caption("💡 성황리에 마무리된 지난 모임 목록입니다.")
                for meeting in past_meetings:
                    render_meeting_card(meeting, google_user, is_admin, key_prefix="past_m", is_ended=True, rsvps=rsvps_map.get(meeting['id'], []), user_eligibility=user_eligibility, is_dedicated=is_dedicated, first_attendees_set=first_attendees_set)

    if tab2:
        with tab2:
            from views.admin_meeting_create import render_admin_meeting_create
            render_admin_meeting_create(google_user=google_user, is_admin=is_admin, is_dedicated=is_dedicated)


