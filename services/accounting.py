import io
import re
import requests
import pandas as pd
import streamlit as st
from collections import Counter
from datetime import datetime, date

from services.config import (
    GOOGLE_SHEET_ID, GOOGLE_SHEET_ACCOUNTING_ID,
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

@st.cache_data(ttl=60, show_spinner=False)
def fetch_google_sheet_accounting():
    """
    회계장부 구글 시트 연동 (gspread 보안 인증 사용)
    - 입금내역 및 출금내역 추출
    - 헤더에 공백이나 중복이 있더라도 안전하게 파싱
    """
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ACCOUNTING_ID)
            worksheets = sh.worksheets()
            data = {}
            for ws in worksheets:
                try:
                    recs = ws.get_all_records()
                    if recs:
                        data[ws.title] = pd.DataFrame(recs)
                except Exception:
                    vals = ws.get_all_values()
                    if vals and len(vals) > 1:
                        header = vals[0]
                        seen = {}
                        clean_header = []
                        for i, h in enumerate(header):
                            h_str = str(h).strip() or f"col_{i}"
                            if h_str in seen:
                                seen[h_str] += 1
                                clean_header.append(f"{h_str}_{seen[h_str]}")
                            else:
                                seen[h_str] = 0
                                clean_header.append(h_str)
                        df = pd.DataFrame(vals[1:], columns=clean_header)
                        data[ws.title] = df
            if data:
                return True, data, None
        except Exception as e:
            err_text = str(e)
            if "403" in err_text or "Permission" in err_text:
                return False, None, "permission_denied"
            return False, None, err_text

    # fallback CSV
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ACCOUNTING_ID}/export?format=csv&gid=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200 and "html" not in res.text[:100].lower():
            df = pd.read_csv(io.BytesIO(res.content))
            return True, {"기본": df}, None
    except Exception:
        pass

    return False, None, "permission_denied"

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

def sync_accounting_pipeline_with_members():
    """
    회계장부 시트와 회원목록 시트를 연동하여 입출금에 따라 등록 및 환급 상태 자동 동기화
    [안전장치] 동명이인 감지 및 분기 처리
    - 동명이인이 없는 고유 이름: 기존처럼 100% 즉시 자동 연동
    - 동명이인이 존재하는 이름:
      - 입금자 적요에 전화번호 뒤 4자리 또는 닉네임이 기재되어 식별 가능한 경우: 해당 회원 자동 연동
      - 식별자가 없는 경우: 오승인 방지를 위해 자동 연동을 건너뛰고 수동 확인 필요 알림 리포트 반환
    """
    ok_acc, acc_data, err = fetch_google_sheet_accounting()
    if not ok_acc:
        return False, err

    gc = get_gspread_client()
    if not gc:
        return False, "구글 서비스 계정 인증 클라이언트가 필요합니다."

    sh_mem = gc.open_by_key(GOOGLE_SHEET_ID)
    ws_mem = sh_mem.worksheet("회원목록") if "회원목록" in [w.title for w in sh_mem.worksheets()] else sh_mem.sheet1
    all_members = ws_mem.get_all_records()
    
    if not all_members:
        return False, "회원목록 시트에 회원 데이터가 없습니다."

    # 1. 회원 명단 전체에서 이름별 인원수 카운트 (동명이인 판별)
    name_counts = Counter([str(m.get("이름", '')).strip() for m in all_members if str(m.get("이름", '')).strip()])
    duplicate_names = {name for name, count in name_counts.items() if count > 1}

    # 2. 회원 시트의 컬럼 인덱스 탐색 (헤더 기준)
    headers = list(all_members[0].keys())
    def find_col_idx(candidates, default_idx):
        for idx, h in enumerate(headers, start=1):
            if any(k in str(h).lower() for k in candidates):
                return idx
        return default_idx

    col_reg = find_col_idx(["등록여부", "등록", "상태"], 3)
    col_curr_s = find_col_idx(["현재등록시즌", "등록시즌", "시즌"], 8)
    col_first_s = find_col_idx(["처음등록시즌", "최초등록시즌", "가입시즌"], 9)

    updated_count = 0
    unresolved_duplicates = []

    # 3. 회계장부 각 워크시트(수입/지출/입출금내역 등) 검사
    for sheet_title, df_acc in acc_data.items():
        if df_acc is None or df_acc.empty:
            continue
        
        name_col = next((c for c in df_acc.columns if any(k in str(c) for k in ["이름", "성명", "입금자", "출금자", "대상자", "내용", "적요"])), None)
        date_col = next((c for c in df_acc.columns if any(k in str(c) for k in ["일자", "날짜", "일시", "date"])), None)
        in_col = next((c for c in df_acc.columns if any(k in str(c) for k in ["입금", "수입", "수납"])), None)
        out_col = next((c for c in df_acc.columns if any(k in str(c) for k in ["출금", "지출", "반환", "환급"])), None)
        
        if not name_col:
            continue

        for _, row in df_acc.iterrows():
            row_text = str(row.get(name_col, '')).strip()
            row_date = str(row.get(date_col, '')).strip() if date_col else ""
            in_amt = row.get(in_col, 0) if in_col else 0
            
            if not row_text:
                continue

            candidate_matches = []
            for m_idx, m in enumerate(all_members):
                m_name = str(m.get("이름", '')).strip()
                if not m_name:
                    continue
                if m_name in row_text and (in_amt or in_col is None):
                    candidate_matches.append((m_idx, m, m_name))

            if not candidate_matches:
                continue

            target_to_update = None

            for m_idx, m, m_name in candidate_matches:
                if m_name not in duplicate_names:
                    target_to_update = (m_idx, m)
                    break
                
                m_nick = str(m.get("닉네임", '')).strip()
                raw_phone = re.sub(r'\D', '', str(m.get("회원번호", '') or m.get("전화번호", '') or ''))
                phone_last4 = raw_phone[-4:] if len(raw_phone) >= 4 else ""

                has_nick = bool(m_nick and len(m_nick) >= 2 and m_nick.lower() in row_text.lower())
                has_phone = bool(phone_last4 and phone_last4 in row_text)

                if has_nick or has_phone:
                    target_to_update = (m_idx, m)
                    break

            if target_to_update:
                m_idx, m = target_to_update
                target_season = calculate_deposit_season(row_date, row_text)
                if str(m.get("등록여부")) != "1" or str(m.get("현재등록시즌")) != str(target_season):
                    sheet_row = m_idx + 2
                    ws_mem.update_cell(sheet_row, col_reg, "1")
                    ws_mem.update_cell(sheet_row, col_curr_s, target_season)
                    if not str(m.get("처음등록시즌", "")).strip():
                        ws_mem.update_cell(sheet_row, col_first_s, target_season)
                    updated_count += 1
            else:
                for _, _, m_name in candidate_matches:
                    if m_name in duplicate_names:
                        unresolved_duplicates.append({
                            "name": m_name,
                            "row_text": row_text,
                            "row_date": row_date,
                            "in_amt": in_amt
                        })

    fetch_google_sheet_members.clear()
    st.cache_data.clear()

    result_msgs = [f"✅ {updated_count}명의 회원이 회계장부와 정상 동기화되었습니다."]
    if unresolved_duplicates:
        seen = set()
        unique_unresolved = []
        for item in unresolved_duplicates:
            key = (item['name'], item['row_text'], item['row_date'])
            if key not in seen:
                seen.add(key)
                unique_unresolved.append(item)

        result_msgs.append(f"\n⚠️ **[동명이인 수동 확인 필요: {len(unique_unresolved)}건]**")
        for item in unique_unresolved:
            date_str = f" ({item['row_date']})" if item['row_date'] else ""
            result_msgs.append(f"- **{item['name']}** | 입금적요: `{item['row_text']}`{date_str} -> 닉네임/전화번호 미기재로 자동승인 보류")
        result_msgs.append("\n💡 *동명이인 입금 건은 회원 확인 후 구글 시트의 [회원목록]에서 수동으로 등록여부('1') 및 시즌을 입력해 주세요.*")

    return True, "\n".join(result_msgs)
