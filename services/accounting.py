import io
import re
import requests
import pandas as pd
import streamlit as st
from collections import Counter
from datetime import datetime, date

from services.config import (
    GOOGLE_SHEET_ID,
    get_current_kst, get_club_season_code, format_season_display
)
from services.sheets import (
    get_gspread_client, fetch_google_sheet_members, fetch_google_sheet_attendances
)

def get_member_attendance_count(user_email="", user_name="", target_season=None):
    """
    구글 시트 출석 기록에서 특정 회원의 누적 출석 횟수를 실시간 집계
    - 라운징(is_lounging == 1)은 0.5회 출석 인정
    - 정규 모임(is_lounging == 0)은 1.0회 출석 인정
    """
    ok_att, att_df = fetch_google_sheet_attendances()
    if not ok_att or att_df is None or att_df.empty:
        return 0.0

    total = 0.0
    e_clean = str(user_email).strip().lower()
    n_clean = str(user_name).split(" - ")[0].strip() if " - " in str(user_name) else str(user_name).strip()
    target_s = str(target_season).strip() if target_season else None

    # 컬럼 탐색
    email_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["이메일", "email"])), None)
    name_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["이름", "성함", "name"])), None)
    season_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["시즌", "season"])), None)
    date_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["일시", "날짜", "date"])), None)
    lounging_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["라운징", "lounging"])), None)
    book_col = next((c for c in att_df.columns if any(k in str(c).lower() for k in ["도서", "책", "book"])), None)

    for _, row in att_df.iterrows():
        r_email = str(row.get(email_col, '')).strip().lower() if email_col else ""
        r_name = str(row.get(name_col, '')).strip() if name_col else ""
        r_season = str(row.get(season_col, '')).strip() if season_col else ""
        r_date = str(row.get(date_col, '')).strip() if date_col else ""
        
        # 시즌 일치 여부 판정
        if target_s:
            season_match = (r_season == target_s)
            if not season_match and r_date:
                try:
                    d_obj = datetime.strptime(r_date[:10].replace('.', '-').replace('/', '-'), "%Y-%m-%d")
                    season_match = (get_club_season_code(d_obj) == target_s)
                except Exception:
                    pass
            if not season_match:
                continue

        # 회원 일치 여부 판정
        is_match = False
        if e_clean and r_email and e_clean == r_email:
            is_match = True
        elif n_clean and r_name and (n_clean in r_name or r_name in n_clean):
            is_match = True

        if is_match:
            is_l = False
            if lounging_col and pd.notna(row.get(lounging_col)):
                val = str(row.get(lounging_col)).strip()
                is_l = (val in ["1", "True", "true", "라운징"])
            if not is_l and book_col and pd.notna(row.get(book_col)):
                b_val = str(row.get(book_col)).strip()
                if "라운징" in b_val:
                    is_l = True
            
            total += 0.5 if is_l else 1.0

    if total.is_integer():
        return int(total)
    return total

count_member_season_attendances = get_member_attendance_count

def calculate_deposit_season(deposit_date=None, memo=""):
    """
    예치금 입금 시점 및 메모/적요를 바탕으로 소속 시즌 자동 판정 (20일 컷오프 룰 & 키워드 파싱)
    - 1순위: 적요나 메모에 명시된 시즌 코드 (예: '2609', '9월', '10월' 등)
    - 2순위: 입금일자 기준 20일 컷오프 룰:
      - 입금일이 매월 20일 이상인 경우 -> 다음 달 시작 시즌 (조기/사전 입금)
      - 입금일이 매월 19일 이하인 경우 -> 당월 시작 시즌 (정규/지각 입금)
    """
    if memo:
        memo_str = str(memo).strip()
        m4 = re.search(r'(2[5-9]\d{2})', memo_str)
        if m4:
            return m4.group(1)
        m_month = re.search(r'(\d{1,2})\s*월', memo_str)
        if m_month:
            month_num = int(m_month.group(1))
            dt_base = get_current_kst()
            year_short = dt_base.strftime("%y")
            return f"{year_short}{month_num:02d}"

    dt = None
    if isinstance(deposit_date, (datetime, date)):
        dt = deposit_date
    elif deposit_date and str(deposit_date).strip():
        d_str = str(deposit_date).strip().replace('.', '-').replace('/', '-')
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%y-%m-%d"]:
            try:
                dt = datetime.strptime(d_str[:10], fmt).date()
                break
            except Exception:
                pass

    if dt is None:
        dt = get_current_kst().date()

    year_val = dt.year
    month_val = dt.month
    day_val = dt.day

    if day_val >= 20:
        if month_val == 12:
            year_val += 1
            month_val = 1
        else:
            month_val += 1

    year_short = str(year_val)[2:]
    return f"{year_short}{month_val:02d}"

def get_member_deposit_info(user_email="", user_name="", user_season=None):
    """
    회원의 예치금 상태, 시즌 출석 목표(신규 4회 vs 기존 3회 vs 운영진 면제), 
    현재 출석 횟수, 환급 달성 여부를 종합 판정하여 반환
    """
    ok_mem, df_mem, _ = fetch_google_sheet_members()
    member_row = None
    if ok_mem and df_mem is not None and not df_mem.empty:
        e_clean = str(user_email).strip().lower()
        n_clean = str(user_name).split(" - ")[0].strip() if " - " in str(user_name) else str(user_name).strip()
        
        email_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["이메일", "email"])), None)
        name_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["이름", "성함", "name"])), None)

        for idx, r in df_mem.iterrows():
            r_email = str(r.get(email_col, '')).strip().lower() if email_col else ""
            r_name = str(r.get(name_col, '')).strip() if name_col else ""
            if (e_clean and r_email == e_clean) or (n_clean and r_name == n_clean):
                member_row = r
                break

    is_admin = False
    reg_val = 1
    curr_season = str(user_season).strip() if user_season else get_club_season_code()
    first_season = curr_season
    refund_memo = ""

    if member_row is not None:
        admin_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["운영진", "admin"])), None)
        reg_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["등록", "상태", "status"])), None)
        curr_s_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["현재등록시즌", "등록시즌", "시즌"])), None)
        first_s_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["처음등록시즌", "최초등록시즌", "가입시즌"])), None)
        refund_col = next((c for c in df_mem.columns if any(k in str(c).lower() for k in ["환급", "반환", "비고"])), None)

        if admin_col and pd.notna(member_row.get(admin_col)):
            raw_adm = str(member_row.get(admin_col)).strip()
            is_admin = (raw_adm in ["1", "운영진", "관리자", "True", "true"])
        if reg_col and pd.notna(member_row.get(reg_col)):
            reg_val = 1 if str(member_row.get(reg_col)).strip() in ["1", "등록", "승인", "True", "true", "완료"] else 0
        if curr_s_col and pd.notna(member_row.get(curr_s_col)):
            c_val = str(member_row.get(curr_s_col)).strip()
            if c_val:
                curr_season = c_val
        if first_s_col and pd.notna(member_row.get(first_s_col)):
            f_val = str(member_row.get(first_s_col)).strip()
            if f_val:
                first_season = f_val
        if refund_col and pd.notna(member_row.get(refund_col)):
            refund_memo = str(member_row.get(refund_col)).strip()

    is_first_season = (first_season == curr_season)
    target_count = 0 if is_admin else (4 if is_first_season else 3)
    current_count = get_member_attendance_count(user_email, user_name, target_season=curr_season)
    remaining_count = max(0.0, float(target_count) - float(current_count))
    if remaining_count.is_integer():
        remaining_count = int(remaining_count)

    is_eligible = (current_count >= target_count) if not is_admin else False
    
    if is_admin:
        status_label = "운영진 면제"
    elif "환급완료" in refund_memo or "반환완료" in refund_memo:
        status_label = "환급 완료"
    elif is_eligible:
        status_label = "환급 요건 달성"
    else:
        status_label = "진행 중"

    return {
        "is_admin": is_admin,
        "is_first_season": is_first_season,
        "registered": reg_val,
        "current_season": curr_season,
        "first_season": first_season,
        "target_count": target_count,
        "current_count": current_count,
        "remaining_count": remaining_count,
        "is_eligible": is_eligible,
        "status_label": status_label,
        "deposit_amount": 0 if is_admin else 20000
    }

def check_member_season_eligibility(google_user):
    """
    회원의 현재 시즌 활동 가능 여부 종합 판정
    """
    if not google_user:
        return False, "NOT_LOGGED_IN", "Google 계정 본인 인증이 필요합니다."

    is_admin = (google_user.get("is_admin", 0) == 1)
    if is_admin:
        return True, "ADMIN", "운영진 계정 (예치금 면제)"

    dep = get_member_deposit_info(
        user_email=google_user.get('email', ''),
        user_name=google_user.get('display_name', google_user.get('name', '')),
        user_season=google_user.get('season')
    )

    current_club_season = get_club_season_code()
    user_reg_season = str(dep.get('current_season', '')).strip()

    raw_status = str(dep.get('status_label', ''))
    if any(k in raw_status for k in ["출석실패", "출석 미달", "미납", "예치금미납", "박탈"]):
        return False, "FAILED_OR_UNPAID", "이전 시즌 출석 미달 또는 예치금 미납으로 모임 신청이 제한되었습니다."

    if dep.get('registered', 0) != 1 or google_user.get('registered', 0) != 1:
        return False, "UNREGISTERED", "이번 시즌 예치금 미등록 상태입니다 (입금 확인 필요)."

    if user_reg_season != current_club_season:
        return False, "PAST_SEASON", f"현재 {format_season_display(current_club_season)} 미등록 상태입니다 (이전 등록: {format_season_display(user_reg_season)})."

    return True, "ACTIVE", "정상 등록 회원"

def format_member_attendance_and_deposit_text(google_user):
    """
    Google 인증 배너에 들어갈 출석 횟수 및 예치금 환급 요건 문구 생성
    """
    if not google_user:
        return ""
        
    dep = get_member_deposit_info(
        user_email=google_user.get('email', ''),
        user_name=google_user.get('display_name', google_user.get('name', '')),
        user_season=google_user.get('season')
    )
    s_label = format_season_display(dep['current_season'])
    cnt = dep['current_count']
    if dep['is_admin']:
        return f"🏆 {s_label} 출석 횟수: <b>{cnt}회</b> <span style='font-size: 0.88rem; color: #856404; margin-left: 6px;'>(👑 예치금 면제)</span>"
    
    is_eligible, reason_type, _ = check_member_season_eligibility(google_user)
    if not is_eligible:
        return f"🏆 {s_label} 출석 횟수: <b>{cnt}회</b> <span style='color: #D32F2F; font-size: 0.88rem; margin-left: 6px;'>(⚠️ 이번 시즌 예치금 미등록 - 활동을 위해 시즌 등록을 진행해 주세요)</span>"

    target = dep['target_count']
    tag = "신규" if dep['is_first_season'] else "기존"
    if dep['is_eligible']:
        tag_badge = f"<span style='color: #2E7D32; font-weight: bold; margin-left: 6px;'>🎉 예치금 환급 달성! ({cnt}/{target}회)</span>"
    else:
        remain = dep['remaining_count']
        tag_badge = f"<span style='color: #1565C0; font-size: 0.9rem; margin-left: 6px;'>(💰 {tag} 예치금 환급: <b>{cnt}/{target}회</b>, {remain}회 남음)</span>"
    return f"🏆 {s_label} 출석 횟수: <b>{cnt}회</b> {tag_badge}"

def render_deposit_refund_card(google_user):
    pass
