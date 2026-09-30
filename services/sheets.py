import io
import os
import requests
import threading
import pandas as pd
import streamlit as st
import gspread
from concurrent.futures import ThreadPoolExecutor
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except Exception:
    add_script_run_ctx = None
    get_script_run_ctx = None

from services.config import (
    GOOGLE_SHEET_ID, GOOGLE_SHEET_ATTENDANCE_ID, GOOGLE_SHEET_FACILITATOR_ID,
    SERVICE_ACCOUNT_FILE, ATTENDANCE_WEBHOOK_URL, WEBHOOK_SECRET_KEY, get_current_kst
)

def sanitize_sheet_cell(val):
    """
    구글 시트 수식 인젝션(Formula / CSV Injection) 방어
    - 셀 첫 글자가 '=', '+', '-', '@', '\t', '\r' 등인 경우 앞에 작은따옴표(')를 부착하여
      수식이 실행되지 않고 안전한 순수 텍스트로 보존되도록 강제 이스케이프
    """
    if val is None:
        return ""
    if not isinstance(val, str):
        return val
    s = val.strip()
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return val

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """
    100% 비공개 구글 시트를 가져오기 위한 서비스 계정 클라이언트 생성
    - 1순위: Streamlit secrets (Cloud 배포 및 로컬 .streamlit/secrets.toml)
    - 2순위: 로컬 SERVICE_ACCOUNT_FILE 키 파일 (fallback)
    """
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2.service_account import Credentials
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            sec_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in sec_dict:
                sec_dict["private_key"] = sec_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(sec_dict, scopes=scopes)
            return gspread.authorize(creds)
    except Exception:
        pass

    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            return gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    except Exception:
        pass
    return None

def _async_send_post(webhook_url, payload):
    """
    백그라운드 비동기 스레드로 웹훅 URL에 POST 전송 (요청 대기시간 0초, 인증 토큰 자동 부착)
    """
    try:
        if webhook_url:
            headers = {"x-planet-auth-token": WEBHOOK_SECRET_KEY}
            if isinstance(payload, dict):
                payload["auth_token"] = WEBHOOK_SECRET_KEY
            requests.post(webhook_url, json=payload, headers=headers, timeout=8)
    except Exception:
        pass

@st.cache_data(ttl=600, show_spinner=False)
def fetch_google_sheet_members():
    """
    회원 명단 시트 다이렉트 전송 (gspread 보안 인증 1순위 사용)
    """
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_ID)
            try:
                ws = sh.worksheet("회원목록")
            except Exception:
                ws = sh.sheet1
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                if not df.empty and len(df.columns) > 1:
                    return True, df, None
    except Exception:
        pass

    # fallback: 기존 CSV 퍼블릭 경로
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200 and "html" not in res.text[:100].lower():
            for enc in ["utf-8", "cp949", "euc-kr"]:
                try:
                    df = pd.read_csv(io.BytesIO(res.content), encoding=enc)
                    if len(df.columns) > 1:
                        return True, df, None
                except Exception:
                    continue
    except Exception:
        pass
    return False, None, "구글 시트 공유 설정('링크가 있는 모든 사용자에게 공개') 확인이 필요합니다."

@st.cache_data(ttl=300, show_spinner=False)
def fetch_attendance_workbook_bundle():
    """
    출석 시트(GOOGLE_SHEET_ATTENDANCE_ID)의 주요 3대 탭(모임목록, 신청명단, 출석목록)을
    단 1회의 batch get API 호출로 동시 수신하여 (ok, df_meetings, df_rsvps, df_attendances) 반환.
    - 네트워크 라운드트립을 1회로 줄여 초기 로딩 속도 극대화
    """
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            res = sh.values_batch_get(["모임목록", "신청명단", "출석목록"])
            vr = res.get("valueRanges", [])

            def _to_df(v, max_tail_rows=None):
                rows = v.get("values", [])
                if not rows or len(rows) < 2:
                    return pd.DataFrame()
                seen = {}
                headers = []
                for idx, c in enumerate(rows[0]):
                    h = str(c).strip() or f"col_{idx}"
                    if h in seen:
                        seen[h] += 1
                        headers.append(f"{h}_{seen[h]}")
                    else:
                        seen[h] = 0
                        headers.append(h)

                data_rows = rows[1:]
                if max_tail_rows and len(data_rows) > max_tail_rows:
                    data_rows = data_rows[-max_tail_rows:]

                data = [(r[:len(headers)] + [''] * max(0, len(headers) - len(r))) for r in data_rows]
                return pd.DataFrame(data, columns=headers)

            df_m = _to_df(vr[0], max_tail_rows=300) if len(vr) > 0 else pd.DataFrame()
            df_r = _to_df(vr[1], max_tail_rows=600) if len(vr) > 1 else pd.DataFrame()
            df_a = _to_df(vr[2], max_tail_rows=600) if len(vr) > 2 else pd.DataFrame()

            return True, df_m, df_r, df_a
        except Exception:
            pass
    return False, None, None, None

def clear_attendance_cache():
    """
    출석 시트 관련 번들 및 개별 캐시 일괄 무효화
    """
    for fn in [
        fetch_attendance_workbook_bundle,
        fetch_google_sheet_meetings,
        fetch_google_sheet_rsvps,
        fetch_google_sheet_attendances,
    ]:
        try:
            fn.clear()
        except Exception:
            pass

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_sheet_attendances():
    """
    출석전용 구글 시트 다이렉트 전송 (번들 캐시 1순위 사용)
    """
    try:
        ok_b, _, _, df_a = fetch_attendance_workbook_bundle()
        if ok_b and df_a is not None and not df_a.empty:
            return True, df_a
    except Exception:
        pass

    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("출석목록")
            except Exception:
                ws = sh.sheet1
            records = ws.get_all_records()
            df = pd.DataFrame(records)
            if not df.empty:
                return True, df
        except Exception:
            pass

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ATTENDANCE_ID}/export?format=csv&gid=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200 and "html" not in res.text[:100].lower():
            for enc in ["utf-8", "cp949", "euc-kr"]:
                try:
                    df = pd.read_csv(io.BytesIO(res.content), encoding=enc)
                    return True, df
                except Exception:
                    continue
    except Exception:
        pass
    return False, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_sheet_meetings():
    """
    모임 목록 시트 다이렉트 전송 (번들 캐시 1순위 사용)
    """
    try:
        ok_b, df_m, _, _ = fetch_attendance_workbook_bundle()
        if ok_b and df_m is not None and not df_m.empty:
            return True, df_m
    except Exception:
        pass

    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("모임목록")
                records = ws.get_all_records()
                df = pd.DataFrame(records)
                if not df.empty:
                    return True, df
            except Exception:
                pass
        except Exception:
            pass

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ATTENDANCE_ID}/export?format=csv&gid=1599243491"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200 and "html" not in res.text[:100].lower():
            for enc in ["utf-8", "cp949", "euc-kr"]:
                try:
                    df = pd.read_csv(io.BytesIO(res.content), encoding=enc)
                    return True, df
                except Exception:
                    continue
    except Exception:
        pass
    return False, None

def _clean_str(val, default=""):
    """
    NaN, None, 결측치 문자열을 감지하여 안전하게 기본값으로 정제
    """
    if val is None or pd.isna(val):
        return default
    s = str(val).strip()
    return default if s.lower() in ["nan", "none", "null", "undefined"] else s

def get_google_sheet_meetings_list():
    """
    구글 시트 '모임목록' 탭에서 모임 레코드 리스트 추출
    """
    ok, df = fetch_google_sheet_meetings()
    if not ok or df is None or df.empty:
        return []

    meetings = []
    for idx, row in df.iterrows():
        title = _clean_str(row.get('모임명'))
        date_str = _clean_str(row.get('모임일자'))
        time_str = _clean_str(row.get('모임시간'), "15:00")
        loc_name = _clean_str(row.get('장소명'), "종각 할리스")
        book_title = _clean_str(row.get('도서명'), "자유 도서")
        author = _clean_str(row.get('저자'))
        desc = _clean_str(row.get('모임설명', row.get('설명', '')))
        leader = _clean_str(row.get('모임장', row.get('지정책장', row.get('책장', ''))))
        kakao = _clean_str(row.get('오픈카톡방', row.get('카톡방', '')))
        account = _clean_str(row.get('입금계좌', row.get('계좌', row.get('계좌번호', ''))))

        if leader and f"[책장:{leader}]" not in desc:
            desc = f"[책장:{leader}]\n" + desc
        if kakao and f"[카톡:{kakao}]" not in desc:
            desc = desc + f"\n[카톡:{kakao}]"
        if account and f"[계좌:{account}]" not in desc:
            desc = desc + f"\n[계좌:{account}]"

        try:
            max_p = int(row.get('정원', 8))
        except Exception:
            max_p = 8
            
        try:
            lat = float(row.get('위도', 37.5699))
            lng = float(row.get('경도', 126.9823))
        except Exception:
            lat, lng = 37.5699, 126.9823

        if title and date_str:
            meetings.append({
                "id": hash(f"{title}_{date_str}_{idx}") % 100000,
                "title": title,
                "book_title": book_title if book_title else "자유 도서",
                "author": author if author else "",
                "meeting_date": date_str,
                "meeting_time": time_str if time_str else "15:00",
                "location_name": loc_name if loc_name else "종각 할리스",
                "latitude": lat,
                "longitude": lng,
                "max_participants": max_p,
                "description": desc,
                "leader": leader,
                "account": account
            })
    return meetings

def get_all_meetings():
    """
    구글 시트 기반 전체 모임 목록 반환
    """
    return get_google_sheet_meetings_list()

def get_meeting_by_id(meeting_id):
    """
    모임 ID로 모임 상세 정보 검색
    """
    meetings = get_all_meetings()
    for m in meetings:
        if m['id'] == meeting_id or str(m['id']) == str(meeting_id):
            return m
    return None

def _merge_session_rsvps(meeting_id, current_rsvps):
    """
    세션에 임시 보관된 로컬 신청/취소 상태를 구글 시트 데이터와 즉시 병합 (낙관적 UI 업데이트)
    """
    try:
        if "local_added_rsvps" not in st.session_state and "local_cancelled_rsvps" not in st.session_state:
            return current_rsvps

        cancelled_set = st.session_state.get("local_cancelled_rsvps", set())
        added_list = st.session_state.get("local_added_rsvps", [])

        filtered = []
        seen = set()
        for r in current_rsvps:
            r_email = str(r.get('member_phone') or '').strip().lower()
            r_name = str(r.get('member_name') or '').strip()
            ident = r_email if r_email else r_name
            if (meeting_id, ident) in cancelled_set:
                continue
            filtered.append(r)
            if ident:
                seen.add(ident)

        for r in added_list:
            if r.get('meeting_id') == meeting_id:
                r_email = str(r.get('member_phone') or '').strip().lower()
                r_name = str(r.get('member_name') or '').strip()
                ident = r_email if r_email else r_name
                if ident and ident not in seen:
                    filtered.append(r)
                    seen.add(ident)

        return filtered
    except Exception:
        return current_rsvps

def get_all_meeting_rsvps_map(meetings=None):
    """
    모든 모임의 신청자 목록을 단 한 번의 시트 순회로 사전 집계하여 {meeting_id: [rsvps...]} 딕셔너리로 반환
    - 각 모임 카드마다 fetch 및 iterrows()를 반복하지 않고 O(1)로 조회 가능
    """
    if meetings is None:
        meetings = get_all_meetings()

    rsvps_map = {m['id']: [] for m in meetings}
    if not meetings:
        return rsvps_map

    ok, df = fetch_google_sheet_rsvps()
    if not ok or df is None or df.empty:
        for m in meetings:
            m_id = m['id']
            rsvps_map[m_id] = _merge_session_rsvps(m_id, rsvps_map.get(m_id, []))
        return rsvps_map

    m_col = next((c for c in df.columns if any(k in str(c) for k in ["모임명", "모임", "title"])), df.columns[0])
    date_col = next((c for c in df.columns if any(k in str(c) for k in ["모임일자", "일자", "날짜", "date"])), None)
    name_col = next((c for c in df.columns if any(k in str(c) for k in ["회원명", "이름", "성함", "name"])), None)
    email_col = next((c for c in df.columns if any(k in str(c) for k in ["이메일", "email", "mail"])), None)
    type_col = next((c for c in df.columns if any(k in str(c) for k in ["참여방식", "방식", "type"])), None)
    comment_col = next((c for c in df.columns if any(k in str(c) for k in ["한마디", "코멘트", "메모", "소감", "comment"])), None)

    seen_map = {m['id']: set() for m in meetings}
    m_info_list = [(m['id'], str(m.get('title', '')).strip(), str(m.get('meeting_date', '')).strip()) for m in meetings]

    records = df.to_dict('records')
    for idx, row in enumerate(records):
        row_m = _clean_str(row.get(m_col))
        row_d = _clean_str(row.get(date_col)) if date_col else ""

        is_shifted = bool(row_d and ("@" in row_d or ("-" in row_d and not row_d[:4].isdigit())))
        if is_shifted:
            r_name = row_d
            r_email = _clean_str(row.get(name_col)) if name_col else ""
            r_type = _clean_str(row.get(email_col), "자유책") if email_col else "자유책"
            r_comment = _clean_str(row.get(type_col)) if type_col else ""
        else:
            r_name = _clean_str(row.get(name_col)) if name_col else ""
            r_email = _clean_str(row.get(email_col)) if email_col else ""
            r_type = _clean_str(row.get(type_col), "자유책") if type_col else "자유책"
            r_comment = _clean_str(row.get(comment_col)) if comment_col else ""
            if not r_name:
                r_name = r_email.split('@')[0] if r_email else "회원"

        identifier = r_email.strip().lower() if r_email else r_name.strip()

        for m_id, m_title, m_date in m_info_list:
            title_match = bool(m_title and (row_m == m_title or m_title in row_m or row_m in m_title))
            if not title_match:
                continue

            if is_shifted:
                date_match = True
            else:
                date_match = True
                if row_d and m_date:
                    date_match = (row_d == m_date or m_date in row_d or row_d in m_date)

            if date_match:
                if identifier and identifier in seen_map[m_id]:
                    continue
                if identifier:
                    seen_map[m_id].add(identifier)

                rsvps_map[m_id].append({
                    "id": idx + 1,
                    "meeting_id": m_id,
                    "member_id": hash(r_email) % 100000 if r_email else idx + 100,
                    "member_name": r_name,
                    "member_phone": r_email,
                    "participation_type": r_type,
                    "comment": r_comment
                })

    for m in meetings:
        m_id = m['id']
        rsvps_map[m_id] = _merge_session_rsvps(m_id, rsvps_map.get(m_id, []))
    return rsvps_map

def get_rsvps_for_meeting(meeting_id, meeting=None, rsvps_map=None):
    """
    구글 시트 '신청명단' 탭에서 특정 모임의 신청자 목록 반환 (rsvps_map이 있으면 즉시 반환)
    """
    if rsvps_map is not None and meeting_id in rsvps_map:
        return _merge_session_rsvps(meeting_id, rsvps_map[meeting_id])

    if meeting is None:
        meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return _merge_session_rsvps(meeting_id, [])

    m_title = meeting.get('title', '')
    m_date = str(meeting.get('meeting_date', '')).strip()

    rsvps = []
    seen_identifiers = set()

    ok, df = fetch_google_sheet_rsvps()
    if ok and df is not None and not df.empty:
        m_col = next((c for c in df.columns if any(k in str(c) for k in ["모임명", "모임", "title"])), df.columns[0])
        date_col = next((c for c in df.columns if any(k in str(c) for k in ["모임일자", "일자", "날짜", "date"])), None)
        name_col = next((c for c in df.columns if any(k in str(c) for k in ["회원명", "이름", "성함", "name"])), None)
        email_col = next((c for c in df.columns if any(k in str(c) for k in ["이메일", "email", "mail"])), None)
        type_col = next((c for c in df.columns if any(k in str(c) for k in ["참여방식", "방식", "type"])), None)
        comment_col = next((c for c in df.columns if any(k in str(c) for k in ["한마디", "코멘트", "메모", "소감", "comment"])), None)

        for idx, row in df.iterrows():
            row_m = str(row.get(m_col, '')).strip()
            row_d = str(row.get(date_col, '')).strip() if date_col and pd.notna(row.get(date_col)) else ""

            title_match = bool(m_title and (row_m == m_title or m_title in row_m or row_m in m_title))
            is_shifted = bool(row_d and ("@" in row_d or ("-" in row_d and not row_d[:4].isdigit())))

            if is_shifted:
                r_name = row_d
                r_email = str(row.get(name_col, '')).strip() if name_col and pd.notna(row.get(name_col)) else ""
                r_type = str(row.get(email_col, '자유책')).strip() if email_col and pd.notna(row.get(email_col)) else "자유책"
                r_comment = str(row.get(type_col, '')).strip() if type_col and pd.notna(row.get(type_col)) else ""
                date_match = True
            else:
                date_match = True
                if row_d and m_date:
                    date_match = (row_d == m_date or m_date in row_d or row_d in m_date)
                r_name = str(row.get(name_col, '')).strip() if name_col and pd.notna(row.get(name_col)) else "회원"
                r_email = str(row.get(email_col, '')).strip() if email_col and pd.notna(row.get(email_col)) else ""
                r_type = str(row.get(type_col, '자유책')).strip() if type_col and pd.notna(row.get(type_col)) else "자유책"
                r_comment = str(row.get(comment_col, '')).strip() if comment_col and pd.notna(row.get(comment_col)) else ""

            if title_match and date_match:
                identifier = r_email.strip().lower() if r_email else r_name.strip()
                if identifier and identifier in seen_identifiers:
                    continue
                if identifier:
                    seen_identifiers.add(identifier)

                rsvps.append({
                    "id": idx + 1,
                    "meeting_id": meeting_id,
                    "member_id": hash(r_email) % 100000 if r_email else idx + 100,
                    "member_name": r_name,
                    "member_phone": r_email,
                    "participation_type": r_type,
                    "comment": r_comment
                })
    return _merge_session_rsvps(meeting_id, rsvps)

def add_rsvp(meeting_id, member_id, member_name, member_phone, participation_type="자유책", comment=""):
    """
    모임 참가 신청 (순수 구글 시트 연동)
    """
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return False, "존재하지 않는 모임입니다."

    max_p = meeting.get('max_participants', 8)
    if participation_type != "대기":
        current_rsvps = get_rsvps_for_meeting(meeting_id, meeting=meeting)
        confirmed_count = len([r for r in current_rsvps if str(r.get('participation_type', '') or '') != '대기'])
        if confirmed_count >= max_p and max_p < 900:
            return False, "모임 정원이 마감되어 대기 신청만 가능합니다."

    # 세션 상태에 즉시 낙관적(Optimistic) 반영
    if "local_added_rsvps" not in st.session_state:
        st.session_state.local_added_rsvps = []
    if "local_cancelled_rsvps" not in st.session_state:
        st.session_state.local_cancelled_rsvps = set()

    ident = (member_phone or member_name).strip().lower()
    st.session_state.local_cancelled_rsvps.discard((meeting_id, ident))
    st.session_state.local_added_rsvps.append({
        "id": hash(member_phone or member_name) % 100000,
        "meeting_id": meeting_id,
        "member_id": member_id,
        "member_name": member_name,
        "member_phone": member_phone,
        "participation_type": participation_type,
        "comment": comment
    })

    from services.config import ATTENDANCE_WEBHOOK_URL
    add_rsvp_to_google_sheet_async(
        ATTENDANCE_WEBHOOK_URL,
        meeting_name=meeting.get('title', ''),
        member_name=member_name,
        email=member_phone,
        participation_type=participation_type,
        meeting_date=meeting.get('meeting_date', ''),
        comment=comment
    )
    clear_attendance_cache()
    msg_type = "대기 신청" if participation_type == "대기" else "참가 신청"
    return True, f"{msg_type}이 성공적으로 완료되었습니다!"

def cancel_rsvp(meeting_id, member_id, member_name="", member_phone=""):
    """
    모임 참가 신청 취소 (순수 구글 시트 연동)
    """
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return False

    # 세션 상태에 즉시 낙관적(Optimistic) 취소 반영
    if "local_added_rsvps" not in st.session_state:
        st.session_state.local_added_rsvps = []
    if "local_cancelled_rsvps" not in st.session_state:
        st.session_state.local_cancelled_rsvps = set()

    ident = (member_phone or member_name).strip().lower()
    st.session_state.local_cancelled_rsvps.add((meeting_id, ident))
    st.session_state.local_added_rsvps = [
        r for r in st.session_state.local_added_rsvps
        if not (r.get('meeting_id') == meeting_id and (r.get('member_phone') or r.get('member_name', '')).strip().lower() == ident)
    ]

    from services.config import ATTENDANCE_WEBHOOK_URL
    cancel_rsvp_from_google_sheet_async(
        ATTENDANCE_WEBHOOK_URL,
        meeting_name=meeting.get('title', ''),
        email=member_phone,
        member_name=member_name,
        meeting_date=meeting.get('meeting_date', '')
    )
    clear_attendance_cache()
    return True

def append_attendance_to_google_sheet_async(webhook_url, checked_at, email, name, year, season, meeting_name, book_read, book_review="", is_lounging=0, book_author="", rating=5):
    """
    백그라운드 비동기 스레드로 구글 시트에 출석 정보 전송 (사용자 대기시간 0초)
    """
    if not webhook_url:
        return False
    
    clean_book_title = str(book_read or "").strip()

    payload = {
        "checked_at": checked_at,
        "email": sanitize_sheet_cell(email),
        "name": sanitize_sheet_cell(name),
        "year": year,
        "season": season,
        "meeting_name": sanitize_sheet_cell(meeting_name),
        "book_read": sanitize_sheet_cell(clean_book_title),
        "book_title": sanitize_sheet_cell(clean_book_title),
        "도서명": sanitize_sheet_cell(clean_book_title),
        "book_review": sanitize_sheet_cell(book_review),
        "review": sanitize_sheet_cell(book_review),
        "감상평": sanitize_sheet_cell(book_review),
        "한줄평": sanitize_sheet_cell(book_review),
        "is_lounging": is_lounging,
        "lounging": is_lounging,
        "라운징": is_lounging,
        "book_author": sanitize_sheet_cell(book_author),
        "author": sanitize_sheet_cell(book_author),
        "저자명": sanitize_sheet_cell(book_author),
        "rating": rating,
        "별점": rating
    }
    
    try:
        fetch_google_sheet_attendances.clear()
        st.cache_data.clear()
    except Exception:
        pass
    
    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
    t.start()
    return True

def append_meeting_to_google_sheet_async(webhook_url, title, book_title, author, meeting_date, meeting_time, location_name, max_participants=8, description="", season="", jijung_leader="", kakao_url="", account_info=""):
    """
    새로 개설된 모임 정보를 구글 시트 '모임목록' 탭에 직접 저장하고 캐시를 즉시 갱신
    """
    leader_name = jijung_leader.strip()
    k_url = kakao_url.strip()
    acc_info = account_info.strip()
    clean_desc = description or ""
    if not leader_name and "[책장:" in clean_desc:
        try:
            leader_name = clean_desc.split("[책장:")[1].split("]")[0].strip()
        except Exception:
            pass
    if not k_url and "[카톡:" in clean_desc:
        try:
            k_url = clean_desc.split("[카톡:")[1].split("]")[0].strip()
        except Exception:
            pass
    if not acc_info and "[계좌:" in clean_desc:
        try:
            acc_info = clean_desc.split("[계좌:")[1].split("]")[0].strip()
        except Exception:
            pass

    row_data = [
        sanitize_sheet_cell(title),
        sanitize_sheet_cell(str(meeting_date)),
        sanitize_sheet_cell(str(meeting_time)),
        sanitize_sheet_cell(str(location_name)),
        sanitize_sheet_cell(str(book_title)),
        sanitize_sheet_cell(str(author)),
        max_participants,
        sanitize_sheet_cell(clean_desc),
        sanitize_sheet_cell(leader_name),
        sanitize_sheet_cell(k_url),
        sanitize_sheet_cell(acc_info)
    ]

    # 1순위: gspread 서비스 계정으로 '모임목록' 시트에 즉시 행 추가
    appended = False
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("모임목록")
            except Exception:
                ws = None
            if ws:
                ws.append_row(row_data)
                appended = True
    except Exception:
        pass

    # gspread 서비스 계정으로 '모임목록' 시트에 직접 저장 완료 후 캐시 갱신
    clear_attendance_cache()
    try:
        st.cache_data.clear()
    except Exception:
        pass

    return appended

def delete_meeting_from_google_sheet_async(webhook_url, title, meeting_date=""):
    """
    구글 시트 '모임목록' 탭에서 모임 삭제 및 캐시 즉시 갱신
    """
    deleted = False
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("모임목록")
            except Exception:
                ws = None
            if ws:
                records = ws.get_all_records()
                for idx, r in enumerate(records, start=2):
                    r_title = str(r.get("모임명") or "").strip()
                    r_date = str(r.get("모임일자") or "").strip()
                    t_match = (title == r_title or title in r_title or r_title in title)
                    d_match = (not meeting_date or not r_date or str(meeting_date).strip() == r_date)
                    if t_match and d_match:
                        ws.delete_rows(idx)
                        deleted = True
                        break
    except Exception:
        pass

    clear_attendance_cache()
    try:
        st.cache_data.clear()
    except Exception:
        pass
    return deleted

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_sheet_rsvps():
    """
    구글 시트에서 신청명단/참가신청 탭을 가져오는 함수 (번들 캐시 1순위 사용)
    """
    try:
        ok_b, _, df_r, _ = fetch_attendance_workbook_bundle()
        if ok_b and df_r is not None and not df_r.empty and any(k in str(col) for col in df_r.columns for k in ["회원", "이름", "모임", "신청"]):
            return True, df_r
    except Exception:
        pass

    gc = get_gspread_client()
    if gc:
        # 1순위: 출석 시트의 '신청명단' 탭 다이렉트 오픈
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("신청명단")
                records = ws.get_all_records()
                if records:
                    df = pd.DataFrame(records)
                    if not df.empty and any(k in str(col) for col in df.columns for k in ["회원", "이름", "모임", "신청"]):
                        return True, df
            except Exception:
                pass
        except Exception:
            pass

        # 2순위 fallback: 전체 탭 순회
        for s_id in [GOOGLE_SHEET_ATTENDANCE_ID, GOOGLE_SHEET_ID]:
            try:
                sh = gc.open_by_key(s_id)
                for w_title in ["신청명단", "참가신청"]:
                    try:
                        ws = sh.worksheet(w_title)
                        records = ws.get_all_records()
                        df = pd.DataFrame(records)
                        if not df.empty and any(k in str(col) for col in df.columns for k in ["회원", "이름", "모임", "신청"]):
                            return True, df
                    except Exception:
                        continue
            except Exception:
                continue

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for s_id in [GOOGLE_SHEET_ATTENDANCE_ID, GOOGLE_SHEET_ID]:
        for g_id in [0, 1599243491, 1000, 2000]:
            url = f"https://docs.google.com/spreadsheets/d/{s_id}/export?format=csv&gid={g_id}"
            try:
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code == 200 and "html" not in res.text[:100].lower():
                    for enc in ["utf-8", "cp949", "euc-kr"]:
                        try:
                            df = pd.read_csv(io.BytesIO(res.content), encoding=enc)
                            if any(k in str(col) for col in df.columns for k in ["회원", "이름", "모임", "신청"]):
                                return True, df
                        except Exception:
                            continue
            except Exception:
                continue
    return False, None

def _async_append_rsvp(webhook_url, payload, row_data):
    try:
        gc = get_gspread_client()
        if gc and row_data:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("신청명단")
            except Exception:
                ws = None
            if ws:
                ws.append_row(row_data)
                return
    except Exception:
        pass

    try:
        if webhook_url:
            _async_send_post(webhook_url, payload)
    except Exception:
        pass

def add_rsvp_to_google_sheet_async(webhook_url, meeting_name, member_name, email, participation_type="자유책", meeting_date="", comment=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에 참가 신청 정보 전송 (대기시간 0초)
    """
    if not webhook_url:
        return False

    now_str = get_current_kst().strftime("%Y-%m-%d %H:%M:%S")

    clean_mname = sanitize_sheet_cell(meeting_name)
    clean_name = sanitize_sheet_cell(member_name)
    clean_email = sanitize_sheet_cell(email)
    clean_type = sanitize_sheet_cell(participation_type)
    clean_comment = sanitize_sheet_cell(comment)

    payload = {
        "type": "add_rsvp",
        "action": "add_rsvp",
        "created_at": now_str,
        "meeting_name": clean_mname,
        "모임명": clean_mname,
        "meeting_date": meeting_date,
        "모임일자": meeting_date,
        "member_name": clean_name,
        "회원명": clean_name,
        "이름": clean_name,
        "email": clean_email,
        "이메일": clean_email,
        "participation_type": clean_type,
        "참여방식": clean_type,
        "방식": clean_type,
        "comment": clean_comment,
        "한마디": clean_comment
    }

    row_data = [
        now_str,
        clean_mname,
        sanitize_sheet_cell(meeting_date if meeting_date else ""),
        clean_name,
        clean_email,
        clean_type,
        clean_comment
    ]

    clear_attendance_cache()

    t = threading.Thread(target=_async_append_rsvp, args=(webhook_url, payload, row_data), daemon=True)
    t.start()
    return True

def _async_cancel_rsvp(webhook_url, payload, meeting_name, email, member_name="", meeting_date=""):
    """
    백그라운드에서 구글 시트 신청명단 탭의 신청 행을 직접 삭제하거나 웹훅으로 취소 요청
    """
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            try:
                ws = sh.worksheet("신청명단")
            except Exception:
                ws = None
            if ws:
                records = ws.get_all_records()
                for idx, r in enumerate(records, start=2):
                    r_mname = str(r.get("모임명") or r.get("meeting_name") or "")
                    r_email = str(r.get("이메일") or r.get("email") or "").strip().lower()
                    r_name = str(r.get("회원명") or r.get("member_name") or r.get("이름") or "").strip()
                    r_date = str(r.get("모임일자") or r.get("meeting_date") or "").strip()

                    m_match = (meeting_name in r_mname or r_mname in meeting_name) if meeting_name else False
                    e_match = bool(email and email.strip().lower() == r_email)
                    n_match = bool(member_name and (member_name.strip() in r_name or r_name in member_name.strip()))
                    d_match = (not meeting_date or not r_date or meeting_date == r_date)

                    if m_match and (e_match or n_match) and d_match:
                        ws.delete_rows(idx)
                        return
    except Exception:
        pass

    try:
        if webhook_url:
            _async_send_post(webhook_url, payload)
    except Exception:
        pass

def cancel_rsvp_from_google_sheet_async(webhook_url, meeting_name, email, member_name="", meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에서 참가 신청 삭제 전송 (대기시간 0초)
    """
    if not webhook_url:
        return False

    payload = {
        "type": "cancel_rsvp",
        "action": "cancel_rsvp",
        "meeting_name": sanitize_sheet_cell(meeting_name),
        "모임명": sanitize_sheet_cell(meeting_name),
        "meeting_date": meeting_date,
        "모임일자": meeting_date,
        "email": sanitize_sheet_cell(email),
        "이메일": sanitize_sheet_cell(email),
        "member_name": sanitize_sheet_cell(member_name),
        "회원명": sanitize_sheet_cell(member_name)
    }

    clear_attendance_cache()

    t = threading.Thread(target=_async_cancel_rsvp, args=(webhook_url, payload, meeting_name, email, member_name, meeting_date), daemon=True)
    t.start()
    return True

@st.cache_data(ttl=600, show_spinner=False)
def fetch_google_sheet_facilitators():
    """
    진행자 목록 구글 시트 데이터를 가져와 캐싱 (5분 캐시)
    """
    # 1순위: gspread 서비스 계정 조회
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_FACILITATOR_ID)
            ws = sh.get_worksheet(0)
            values = ws.get_all_values()
            if values:
                return values
    except Exception:
        pass

    # 2순위: 공개 gviz CSV 내보내기 fallback
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_FACILITATOR_ID}/gviz/tq?tqx=out:csv&gid=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            import csv
            reader = csv.reader(io.StringIO(res.text))
            values = list(reader)
            if values:
                return values
    except Exception:
        pass

    return []

def _parse_month_day(date_val):
    if not date_val:
        return None, None
    s = str(date_val).strip()
    if "-" in s:
        parts = s[:10].split("-")
        if len(parts) >= 3:
            try:
                return int(parts[1]), int(parts[2])
            except Exception:
                pass
    if "." in s and len(s) >= 8:
        parts = s[:10].split(".")
        if len(parts) >= 3:
            try:
                return int(parts[1]), int(parts[2])
            except Exception:
                pass
    if "/" in s:
        parts = s.split("/")
        if len(parts) >= 2:
            try:
                if len(parts) == 3 and len(parts[0]) == 4:
                    return int(parts[1]), int(parts[2])
                return int(parts[0]), int(parts[1])
            except Exception:
                pass
    return None, None

def get_meeting_facilitator(meeting_title, meeting_date):
    """
    모임 제목과 일자를 바탕으로 진행자 목록 구글 시트에서 배정된 진행자를 검색
    - 토요일 강남 (어텀): 어텀(토) 실제/계획 진행자 매칭
    - 일요일 종각 (윈터블): 윈터블(일) 실제/계획 진행자 매칭
    - 매칭되지 않거나 미배정된 경우 '미정' 반환
    """
    target_m, target_d = _parse_month_day(meeting_date)
    if target_m is None or target_d is None:
        return "미정"

    m_title = str(meeting_title or "").strip().lower()
    is_autumn = any(k in m_title for k in ["어텀", "강남", "토"])
    is_winter = any(k in m_title for k in ["윈터블", "종각", "일"])
    is_spring = any(k in m_title for k in ["스프링", "수"])

    values = fetch_google_sheet_facilitators()
    if not values:
        return "미정"

    invalid_names = {"", "추석", "설날", "휴무", "휴강", "nan", "none", "미정"}

    for row in values:
        # 어텀(토) 열 인덱스: 6=실제날짜, 7=실제진행자, 5=계획진행자
        if is_autumn and len(row) > 7:
            cell_m, cell_d = _parse_month_day(row[6])
            if cell_m == target_m and cell_d == target_d:
                act = str(row[7]).strip()
                if act and act.lower() not in invalid_names:
                    return act
                plan = str(row[5]).strip() if len(row) > 5 else ""
                if plan and plan.lower() not in invalid_names:
                    return plan
                return "미정"

        # 윈터블(일) 열 인덱스: 10=실제날짜, 11=실제진행자, 9=계획진행자
        if is_winter and len(row) > 11:
            cell_m, cell_d = _parse_month_day(row[10])
            if cell_m == target_m and cell_d == target_d:
                act = str(row[11]).strip()
                if act and act.lower() not in invalid_names:
                    return act
                plan = str(row[9]).strip() if len(row) > 9 else ""
                if plan and plan.lower() not in invalid_names:
                    return plan
                return "미정"

        # 스프링토(수) 열 인덱스: 2=실제날짜, 3=실제진행자, 1=계획진행자
        if is_spring and len(row) > 3:
            cell_m, cell_d = _parse_month_day(row[2])
            if cell_m == target_m and cell_d == target_d:
                act = str(row[3]).strip()
                if act and act.lower() not in invalid_names:
                    return act
                plan = str(row[1]).strip() if len(row) > 1 else ""
                if plan and plan.lower() not in invalid_names:
                    return plan
                return "미정"

    return "미정"

def prefetch_schedule_data():
    """
    모임 일정/출석 페이지 진입 시 주요 3대 탭 번들(모임, 신청, 출석)을 안전하게 1회 사전 로딩
    """
    try:
        fetch_attendance_workbook_bundle()
    except Exception:
        pass

