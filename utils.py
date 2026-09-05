import math
import requests
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 사용자가 제공한 구글 시트 ID (회원 명단 시트)
GOOGLE_SHEET_ID = "1UbvS5tDzQvGlOh-TVagtYJ31pW9u8CNw-wENIK8iK48"

# 사용자가 출석 기록용으로 제공한 구글 시트 ID 및 Webhook URL
GOOGLE_SHEET_ATTENDANCE_ID = "1k1lJmH6fmsPKD8h_-QMbTVy6nrh-RTJt-fUJAQWukKE"
ATTENDANCE_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw1KwJAy3_GGXkQ_pYISTxExafydX2JGPyY6BsS711V1m4s49N7VwDL2dmeJbF8qBFMrA/exec"

def get_current_kst():
    """
    대한민국 표준시(KST, UTC+9) datetime 객체 반환
    - Streamlit Cloud(Linux UTC) 환경에서도 언제나 정확한 한국 시간 보장
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=9)))

def get_club_season_code(dt=None):
    """
    2달 간격 시즌 코드 (시작 월 기준 매월 롤링 시즌)
    - 2601: 1월~2월 시즌
    - 2602: 2월~3월 시즌
    ...
    - 2608: 8월~9월 시즌
    - 2609: 9월~10월 시즌
    """
    if dt is None:
        dt = get_current_kst()
    year_short = dt.strftime("%y")
    return f"{year_short}{dt.month:02d}"


import os
import gspread

# 서비스 계정 JSON 파일 경로
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "planet-app-507608-f8729d5756b5.json")

def get_gspread_client():
    """
    100% 비공개 구글 시트를 가져오기 위한 서비스 계정 클라이언트 생성
    - 1순위: Streamlit secrets (Cloud 배포 환경)
    - 2순위: 로컬 planet-app-507608-f8729d5756b5.json 키 파일
    """
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2.service_account import Credentials
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            sec_dict = dict(st.secrets["gcp_service_account"])
            # toml 형식 줄바꿈 호환 처리
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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_sheet_members():
    """
    회원 명단 시트 다이렉트 전송 (gspread 보안 인증 1순위 사용)
    """
    try:
        gc = get_gspread_client()
        if gc:
            sh = gc.open_by_key(GOOGLE_SHEET_ID)
            ws = sh.worksheet("회원목록") if "회원목록" in [w.title for w in sh.worksheets()] else sh.sheet1
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

@st.cache_data(ttl=60, show_spinner=False)
def fetch_google_sheet_attendances():
    """
    출석전용 구글 시트 다이렉트 전송 (gspread 보안 인증 1순위 사용)
    """
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            ws = sh.worksheet("출석목록") if "출석목록" in [w.title for w in sh.worksheets()] else sh.sheet1
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
        if res.status_code == 200:
            df = pd.read_csv(io.BytesIO(res.content), encoding="utf-8")
            return True, df
    except Exception:
        pass
    return False, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_google_sheet_meetings():
    """
    모임 목록 시트 다이렉트 전송 (gspread 보안 인증 1순위 사용)
    """
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            ws = sh.worksheet("모임목록") if "모임목록" in [w.title for w in sh.worksheets()] else None
            if ws:
                records = ws.get_all_records()
                df = pd.DataFrame(records)
                if not df.empty:
                    return True, df
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
                    if any(k in str(col) for col in df.columns for k in ["모임명", "모임 제목", "모임일자", "일자", "title"]):
                        return True, df
                except Exception:
                    continue
    except Exception:
        pass

    return False, None

def get_google_sheet_meetings_list():
    """
    구글 시트 데이터를 정제하여 기존 DB dict 객체 규격으로 반환
    """
    ok, df = fetch_google_sheet_meetings()
    if not ok or df is None or df.empty:
        return []

    title_col = next((c for c in df.columns if any(k in str(c) for k in ["모임명", "모임 제목", "title"])), df.columns[0])
    date_col = next((c for c in df.columns if any(k in str(c) for k in ["모임일자", "일자", "날짜", "date"])), None)
    time_col = next((c for c in df.columns if any(k in str(c) for k in ["모임시간", "시간", "time"])), None)
    loc_col = next((c for c in df.columns if any(k in str(c) for k in ["장소명", "장소", "location"])), None)
    book_col = next((c for c in df.columns if any(k in str(c) for k in ["도서명", "책제목", "book"])), None)
    author_col = next((c for c in df.columns if any(k in str(c) for k in ["저자", "author"])), None)
    max_col = next((c for c in df.columns if any(k in str(c) for k in ["정원", "최대인원", "max"])), None)
    desc_col = next((c for c in df.columns if any(k in str(c) for k in ["모임설명", "설명", "desc"])), None)
    leader_col = next((c for c in df.columns if any(k in str(c) for k in ["지정책장", "책장", "leader"])), None)
    kakao_col = next((c for c in df.columns if any(k in str(c) for k in ["오픈카톡방", "오픈카톡", "카톡", "kakao"])), None)

    meetings = []
    for idx, row in df.iterrows():
        title_val = str(row.get(title_col, '')).strip()
        if not title_val or pd.isna(row.get(title_col)):
            continue

        date_val = str(row.get(date_col, '2026-08-30')).strip() if date_col and pd.notna(row.get(date_col)) else "2026-08-30"
        time_val = str(row.get(time_col, '14:00 ~ 16:30')).strip() if time_col and pd.notna(row.get(time_col)) else "14:00 ~ 16:30"
        loc_val = str(row.get(loc_col, '강남역 인근 카페')).strip() if loc_col and pd.notna(row.get(loc_col)) else "강남역 인근 카페"
        book_val = str(row.get(book_col, '자유책 (각자 읽은 책 지참)')).strip() if book_col and pd.notna(row.get(book_col)) else "자유책 (각자 읽은 책 지참)"
        author_val = str(row.get(author_col, '자율')).strip() if author_col and pd.notna(row.get(author_col)) else "자율"
        
        try:
            max_val = int(row.get(max_col, 8)) if max_col and pd.notna(row.get(max_col)) else 8
        except Exception:
            max_val = 8
            
        desc_val = str(row.get(desc_col, '')).strip() if desc_col and pd.notna(row.get(desc_col)) else ""
        leader_val = str(row.get(leader_col, '')).strip() if leader_col and pd.notna(row.get(leader_col)) else ""
        kakao_val = str(row.get(kakao_col, '')).strip() if kakao_col and pd.notna(row.get(kakao_col)) else ""

        if leader_val and "[책장:" not in desc_val:
            desc_val = f"[책장:{leader_val}]\n" + desc_val
        if kakao_val and "[카톡:" not in desc_val:
            desc_val = desc_val + f"\n[카톡:{kakao_val}]"

        # 좌표 설정
        if "종각" in loc_val or "종로" in loc_val:
            lat, lng = 37.5709, 126.9778
        else:
            lat, lng = 37.4979, 127.0276

        m_dict = {
            "id": idx + 1000,
            "title": title_val,
            "book_title": book_val,
            "author": author_val,
            "meeting_date": date_val,
            "meeting_time": time_val,
            "location_name": loc_val,
            "latitude": lat,
            "longitude": lng,
            "max_participants": max_val,
            "description": desc_val
        }
        meetings.append(m_dict)

    return meetings

def format_season_display(season_code):
    """
    시즌 코드를 입력받아 '2609시즌(9~10월)' 형태의 1번 방식 표기로 변환
    - 예: 2609 -> 2609시즌(9~10월)
    - 예: 2608 -> 2608시즌(8~9월)
    """
    if not season_code or not str(season_code).strip():
        curr = get_club_season_code()
        season_code = curr

    sc = str(season_code).strip()
    if len(sc) == 4 and sc.isdigit():
        start_month = int(sc[2:4])
        end_month = (start_month % 12) + 1
        return f"{sc}시즌({start_month}~{end_month}월)"
    return f"{sc}시즌"

def get_member_attendance_count(email, name="", target_season=None):
    """
    구글 시트 출석 기록에서 해당 회원의 지정 시즌(또는 현재 시즌) 출석 횟수를 실시간 집계 (라운징 0.5회, 정규 1회)
    """
    ok, df = fetch_google_sheet_attendances()
    if not ok or df is None or df.empty:
        return 0
    
    current_season = str(target_season).strip() if target_season else get_club_season_code()
    user_email = email.strip().lower() if email else ""
    user_name_only = name.split(" - ")[0].strip() if " - " in name else name.strip()
    user_nick_only = name.split(" - ")[1].strip() if " - " in name else ""

    total = 0.0
    for idx, row in df.iterrows():
        r_email = str(row.get('회원 이메일', row.get('email', ''))).strip().lower()
        r_name = str(row.get('회원 성함', row.get('name', ''))).strip()
        r_season = str(row.get('시즌 코드', row.get('시즌', row.get('season', '')))).strip()
        r_book = str(row.get('도서명', row.get('book_read', ''))).strip()
        r_lounging = str(row.get('라운징 여부', row.get('is_lounging', ''))).strip()

        # 이메일 일치 OR 이름/닉네임 일치 검증
        match_email = (user_email and r_email == user_email)
        match_name = (user_name_only and user_name_only == r_name) or (user_nick_only and user_nick_only == r_name)
        
        # 시즌 체크 (시즌 값이 없거나 지정/현재 시즌과 일치하는 경우)
        match_season = (not r_season) or (r_season == current_season) or (current_season in r_season)

        if (match_email or match_name) and match_season:
            if "1" in r_lounging or "라운징" in r_book or "라운징" in r_lounging:
                total += 0.5
            else:
                total += 1.0

    if total.is_integer():
        return int(total)
    return total

# 하위 호환성 별칭
count_member_season_attendances = get_member_attendance_count

def _async_append_attendance(webhook_url, payload, row_data):
    # 1순위: gspread 서비스 계정 다이렉트 추가 (100% 컬럼 정확성 및 지연 없는 기록)
    try:
        gc = get_gspread_client()
        if gc and row_data:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            ws = sh.worksheet("출석목록") if "출석목록" in [w.title for w in sh.worksheets()] else sh.sheet1
            ws.append_row(row_data)
            return
    except Exception:
        pass

    # 2순위: Google Apps Script Webhook fallback
    try:
        requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

def append_attendance_to_google_sheet_async(webhook_url, checked_at, email, name, year, season, meeting_name, book_read, book_review="", is_lounging=0, book_author="", rating=5):
    """
    백그라운드 비동기 스레드(Async Thread)로 구글 시트에 전송하여 사용자 대기시간 0초로 단축!
    - gspread 다이렉트 연동 1순위 사용 (누락 및 열 밀림 0%)
    - is_lounging: 라운징 선택시 1, 아니면 0
    - book_author: 저자/작가명 (선택)
    - rating: 별점 (1~5)
    """
    import threading
    if not webhook_url:
        return False
    
    payload = {
        "type": "attendance",
        "action": "attendance",
        "checked_at": checked_at,
        "email": email,
        "name": name,
        "year": year,
        "season": season,
        "meeting_name": meeting_name,
        "book_read": book_read,
        "book_review": book_review,
        "review": book_review,
        "감상평": book_review,
        "한줄평": book_review,
        "is_lounging": is_lounging,
        "lounging": is_lounging,
        "라운징": is_lounging,
        "book_author": book_author,
        "author": book_author,
        "저자명": book_author,
        "저자": book_author,
        "rating": rating,
        "별점": rating
    }

    # 출석목록 11개 컬럼 순서
    # ['출석 일시 (KST)', '회원 이메일', '회원 성함', '연도', '시즌', '모임명', '도서명', '한줄평', '라운징', '저자명', '별점']
    row_data = [
        str(checked_at),
        str(email),
        str(name),
        str(year),
        str(season),
        str(meeting_name),
        str(book_read),
        str(book_review),
        str(is_lounging),
        str(book_author),
        str(rating)
    ]
    
    # 캐시 지우기 (다음번 조회시 반영)
    try:
        fetch_google_sheet_attendances.clear()
        st.cache_data.clear()
    except Exception:
        pass
    
    # 백그라운드 비동기 스레드 시작
    t = threading.Thread(target=_async_append_attendance, args=(webhook_url, payload, row_data), daemon=True)
    t.start()
    return True

def append_meeting_to_google_sheet_async(webhook_url, title, book_title, author, meeting_date, meeting_time, location_name, max_participants=8, description="", season="", jijung_leader="", kakao_url=""):
    """
    백그라운드 비동기 스레드로 구글 시트 웹훅에 새로 개설된 모임 정보를 전송
    """
    import threading
    if not webhook_url:
        return False

    leader_name = jijung_leader.strip()
    k_url = kakao_url.strip()
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

    payload = {
        "type": "create_meeting",
        "action": "create_meeting",
        "title": title,
        "meeting_name": title,
        "모임명": title,
        "book_title": book_title,
        "도서명": book_title,
        "author": author,
        "저자": author,
        "meeting_date": meeting_date,
        "모임일자": meeting_date,
        "meeting_time": meeting_time,
        "모임시간": meeting_time,
        "location_name": location_name,
        "장소명": location_name,
        "max_participants": max_participants,
        "정원": max_participants,
        "description": description,
        "모임설명": description,
        "season": season,
        "시즌": season,
        "jijung_leader": leader_name,
        "지정책장": leader_name,
        "kakao_url": k_url,
        "오픈카톡방": k_url
    }

    try:
        fetch_google_sheet_meetings.clear()
        st.cache_data.clear()
    except Exception:
        pass

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        pass

    try:
        fetch_google_sheet_meetings.clear()
        st.cache_data.clear()
    except Exception:
        pass

    return True

def delete_meeting_from_google_sheet_async(webhook_url, title, meeting_date=""):
    """
    구글 시트 웹훅에 모임 삭제 요청 전송 및 캐시 즉시 비우기
    """
    if not webhook_url:
        return False

    payload = {
        "type": "delete_meeting",
        "action": "delete_meeting",
        "title": title,
        "meeting_name": title,
        "모임명": title,
        "meeting_date": meeting_date,
        "모임일자": meeting_date
    }

    try:
        fetch_google_sheet_meetings.clear()
        fetch_google_sheet_attendances.clear()
        st.cache_data.clear()
    except Exception:
        pass

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        pass

    try:
        fetch_google_sheet_meetings.clear()
        fetch_google_sheet_attendances.clear()
        st.cache_data.clear()
    except Exception:
        pass

    return True

def cancel_rsvp_from_google_sheet_async(webhook_url, title, email, name, meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 웹훅에 참가 신청 취소 요청 전송
    """
    import threading
    if not webhook_url:
        return False

    payload = {
        "type": "cancel_rsvp",
        "action": "cancel_rsvp",
        "title": title,
        "meeting_name": title,
        "모임명": title,
        "email": email,
        "회원이메일": email,
        "name": name,
        "회원성함": name,
        "meeting_date": meeting_date,
        "모임일자": meeting_date
    }

    try:
        fetch_google_sheet_rsvps.clear()
        st.cache_data.clear()
    except Exception:
        pass

    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
    t.start()
    return True

@st.cache_data(ttl=60, show_spinner=False)
def fetch_google_sheet_rsvps():
    """
    구글 시트에서 신청명단/참가신청 탭을 가져오는 함수 (gspread 보안 인증 1순위 사용)
    """
    gc = get_gspread_client()
    if gc:
        for s_id in [GOOGLE_SHEET_ATTENDANCE_ID, GOOGLE_SHEET_ID]:
            try:
                sh = gc.open_by_key(s_id)
                for w_title in ["신청명단", "참가신청"]:
                    if w_title in [w.title for w in sh.worksheets()]:
                        ws = sh.worksheet(w_title)
                        records = ws.get_all_records()
                        df = pd.DataFrame(records)
                        if not df.empty and any(k in str(col) for col in df.columns for k in ["회원", "이름", "모임", "신청"]):
                            return True, df
            except Exception:
                continue

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    urls = [
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ATTENDANCE_ID}/gviz/tq?tqx=out:csv&sheet=%EC%8B%A0%EC%B2%AD%EB%AA%85%EB%8B%A8",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ATTENDANCE_ID}/gviz/tq?tqx=out:csv&sheet=%EC%B0%B8%EA%B0%80%EC%8B%A0%EC%B2%AD",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=%EC%8B%A0%EC%B2%AD%EB%AA%85%EB%8B%A8"
    ]
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=4)
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
    # 1순위: gspread 서비스 계정 다이렉트 추가 (정확한 6개 컬럼 일치: 신청일시, 모임명, 모임일자, 회원명, 이메일, 참여방식)
    try:
        gc = get_gspread_client()
        if gc and row_data:
            sh = gc.open_by_key(GOOGLE_SHEET_ATTENDANCE_ID)
            ws = sh.worksheet("신청명단") if "신청명단" in [w.title for w in sh.worksheets()] else None
            if ws:
                ws.append_row(row_data)
                return
    except Exception:
        pass

    # 2순위: Google Apps Script Webhook fallback
    try:
        requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

def add_rsvp_to_google_sheet_async(webhook_url, meeting_name, member_name, email, participation_type="자유책", meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에 참가 신청 정보 전송 (대기시간 0초)
    - gspread 다이렉트 연동 1순위 사용 (열 밀림 방지 및 정확한 6개 컬럼 보장)
    """
    import threading
    if not webhook_url:
        return False

    from datetime import datetime
    now_str = get_current_kst().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "type": "add_rsvp",
        "action": "add_rsvp",
        "created_at": now_str,
        "meeting_name": meeting_name,
        "모임명": meeting_name,
        "meeting_date": meeting_date,
        "모임일자": meeting_date,
        "member_name": member_name,
        "회원명": member_name,
        "이름": member_name,
        "email": email,
        "이메일": email,
        "participation_type": participation_type,
        "참여방식": participation_type
    }

    # 신청명단 6개 컬럼 순서
    # ['신청일시', '모임명', '모임일자', '회원명', '이메일', '참여방식']
    row_data = [
        str(now_str),
        str(meeting_name),
        str(meeting_date),
        str(member_name),
        str(email),
        str(participation_type)
    ]

    try:
        fetch_google_sheet_rsvps.clear()
        st.cache_data.clear()
    except Exception:
        pass

    t = threading.Thread(target=_async_append_rsvp, args=(webhook_url, payload, row_data), daemon=True)
    t.start()
    return True

def cancel_rsvp_from_google_sheet_async(webhook_url, meeting_name, email, member_name="", meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에서 참가 신청 삭제 전송 (대기시간 0초)
    """
    import threading
    if not webhook_url:
        return False

    payload = {
        "type": "cancel_rsvp",
        "action": "cancel_rsvp",
        "meeting_name": meeting_name,
        "모임명": meeting_name,
        "meeting_date": meeting_date,
        "모임일자": meeting_date,
        "email": email,
        "이메일": email,
        "member_name": member_name,
        "회원명": member_name
    }

    try:
        fetch_google_sheet_rsvps.clear()
        st.cache_data.clear()
    except Exception:
        pass

    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
    t.start()
    return True

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    위도, 경도 좌표간 거리를 하버사인(Haversine) 공식을 이용하여 메터(m) 단위로 계산
    """
    R = 6371000  # 지구 반지름 (미터 단위)
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def render_geolocation_button():
    """
    현장 출석 인증 버튼을 렌더링
    """
    geo_html = """
    <div style="background-color: #F7F5F0; padding: 15px; border-radius: 10px; border: 1px solid #E0DCD3; font-family: sans-serif;">
        <h4 style="margin-top:0; color: #4A3E3D;">📍 현장 출석 인증</h4>
        <p style="font-size: 13px; color: #666; margin-bottom: 10px;">
            아래 버튼을 눌러 모임 현장 출석 인증을 진행해 주세요.
        </p>
        <button id="getLocBtn" onclick="getLocation()" style="
            background-color: #8D6E63;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        ">📍 출석 인증 진행하기</button>

        <div id="locationResult" style="margin-top: 12px; font-size: 14px; font-weight: bold; color: #2C3E50;"></div>

        <script>
        function getLocation() {
            var resultDiv = document.getElementById("locationResult");
            if (navigator.geolocation) {
                resultDiv.innerHTML = "⏳ 출석 인증 정보를 확인하는 중...";
                navigator.geolocation.getCurrentPosition(showPosition, showError, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                });
            } else {
                resultDiv.innerHTML = "❌ 이 브라우저는 출석 인증을 지원하지 않습니다.";
            }
        }

        function showPosition(position) {
            var lat = position.coords.latitude.toFixed(6);
            var lng = position.coords.longitude.toFixed(6);
            
            var resultDiv = document.getElementById("locationResult");
            resultDiv.innerHTML = "✅ 출석 인증 정보 확인 완료!<br/>" + 
                                  "💡 <b>아래 버튼을 눌러 출석체크를 완료해 주세요!</b>";
        }

        function showError(error) {
            var resultDiv = document.getElementById("locationResult");
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    resultDiv.innerHTML = "❌ 출석 인증 권한 요청이 거부되었습니다.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    resultDiv.innerHTML = "❌ 출석 인증 정보를 확인할 수 없습니다.";
                    break;
                case error.TIMEOUT:
                    resultDiv.innerHTML = "❌ 출석 인증 요청 시간이 초과되었습니다.";
                    break;
                case error.UNKNOWN_ERROR:
                    resultDiv.innerHTML = "❌ 알 수 없는 오류가 발생했습니다.";
                    break;
            }
        }
        </script>
    </div>
    """
    components.html(geo_html, height=220)

# 위치 테스트용 주요 장소 프리셋
LOCATION_PRESETS = {
    "📍 일요일 모임: 할리스 종각역점 (37.5699, 126.9823)": (37.5699, 126.9823),
    "📍 토요일 모임: 뚜레쥬르 카페역삼점 (37.5007, 127.0366)": (37.5007, 127.0366),
    "📍 강남 북카페 북클럽 플래닛 (37.4979, 127.0276)": (37.4979, 127.0276),
    "📍 홍대입구 문학살롱 (37.5563, 126.9226)": (37.5563, 126.9226),
}

def get_meeting_target_gps(meeting):
    """
    모임 정보(제목, 장소명, 날짜)에 따라 기준 GPS 좌표(종각 할리스 / 역삼 뚜레쥬르) 반환
    - 일요일 모임: 할리스 종각역점 (37.5699, 126.9823)
    - 토요일 모임: 뚜레쥬르 카페역삼점 (37.5007, 127.0366)
    """
    m_dict = dict(meeting) if meeting else {}
    title = str(m_dict.get('title', '')).strip()
    loc = str(m_dict.get('location_name', '')).strip()
    date_str = str(m_dict.get('meeting_date', '')).strip()

    if "토" in title or "역삼" in loc or "뚜레쥬르" in loc:
        return "뚜레쥬르 카페역삼점", 37.5007, 127.0366
    elif "종각" in loc or "할리스" in loc or "일" in title:
        return "할리스 종각역점", 37.5699, 126.9823
    elif m_dict.get('latitude') and m_dict.get('longitude'):
        return loc if loc else "모임 장소", m_dict['latitude'], m_dict['longitude']
    
    # 기본값: 종각역점
    return "할리스 종각역점", 37.5699, 126.9823

def fetch_korean_book_search(query, kakao_key=None, size=5):
    """
    카카오 도서 Open API를 활용하여 국내 모든 정식 출간 한글 도서 정보(표지, 저자, 출판사, 줄거리 등) 실시간 검색
    """
    if not query or not query.strip():
        return []
        
    query_clean = query.strip()
    key_to_use = kakao_key if kakao_key else st.session_state.get("kakao_api_key", "").strip()
    
    if not key_to_use:
        # 기본 오픈 테스트 키
        key_to_use = "8a9134a6e45fa600a0684f8bb6be980a"
        
    url = "https://dapi.kakao.com/v3/search/book"
    headers = {"Authorization": f"KakaoAK {key_to_use}"}
    
    try:
        res = requests.get(url, params={"query": query_clean, "size": size}, headers=headers, timeout=5)
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            books = []
            for doc in docs:
                authors = ", ".join(doc.get("authors", []))
                books.append({
                    "title": doc.get("title", ""),
                    "author": authors if authors else "저자 미상",
                    "publisher": doc.get("publisher", ""),
                    "price": doc.get("price", 0),
                    "sale_price": doc.get("sale_price", 0),
                    "thumbnail": doc.get("thumbnail", ""),
                    "contents": doc.get("contents", ""),
                    "url": doc.get("url", ""),
                    "datetime": doc.get("datetime", "")[:10] if doc.get("datetime") else ""
                })
            return books
    except Exception:
        pass
        
    return []

# ==========================================
# 💰 예치금 & 회계장부 파이프라인 연동 모듈
# ==========================================
GOOGLE_SHEET_ACCOUNTING_ID = "17Puv1lLwzZy9M-rJIVGzMhEHrF3hb_zrWBjzgxXnKsk"

def calculate_deposit_season(deposit_date=None, memo=""):
    """
    예치금 입금 시점 및 메모/적요를 바탕으로 소속 시즌 자동 판정 (20일 컷오프 룰 & 키워드 파싱)
    - 1순위: 적요나 메모에 명시된 시즌 코드 (예: '2609', '9월', '10월' 등)
    - 2순위: 입금일자 기준 20일 컷오프 룰:
      - 입금일이 매월 20일 이상인 경우 -> 다음 달 시작 시즌 (조기/사전 입금)
        (예: 8월 25일 입금 -> 2609시즌)
      - 입금일이 매월 19일 이하인 경우 -> 당월 시작 시즌 (정규/지각 입금)
        (예: 9월 5일 입금 -> 2609시즌)
    """
    import re
    from datetime import datetime, date
    
    # 1. 메모/적요에서 4자리 시즌 코드 탐색 (예: 2609, 2610)
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

    # 2. 날짜 파싱
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

    # 3. 20일 컷오프 자동 판정
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
    """
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(GOOGLE_SHEET_ACCOUNTING_ID)
            worksheets = sh.worksheets()
            data = {}
            for ws in worksheets:
                recs = ws.get_all_records()
                if recs:
                    data[ws.title] = pd.DataFrame(recs)
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

    # 신규 부원 판정: 처음등록시즌과 현재등록시즌이 일치하는 경우
    is_first_season = (first_season == curr_season)
    
    # 목표 출석 수: 운영진 0회(면제), 신규 부원 4회, 기존 부원 3회
    target_count = 0 if is_admin else (4 if is_first_season else 3)

    # 현재 시즌 누적 출석 수 (라운징 0.5회, 정규 1회)
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

def render_deposit_refund_card(google_user):
    """
    회원의 예치금 및 시즌 출석 환급 달성 현황 카드 UI 컴포넌트
    - 첫 등록 신규 부원: 시즌 4회 출석 시 100% 반환 (20,000원)
    - 기존 활동 부원: 시즌 3회 출석 시 100% 반환 (20,000원)
    - 운영진: 예치금 면제 대상
    """
    if not google_user:
        return
    
    dep_info = get_member_deposit_info(
        user_email=google_user.get('email', ''),
        user_name=google_user.get('name', ''),
        user_season=google_user.get('season')
    )
    
    is_admin = dep_info['is_admin']
    curr_s_label = format_season_display(dep_info['current_season'])
    
    if is_admin:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FFFDF5, #FFF9E6); border: 1px solid #FFE082; border-radius: 12px; padding: 14px 18px; margin: 10px 0 16px 0; box-shadow: 0 2px 6px rgba(255, 179, 0, 0.08);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 800; font-size: 1.0rem; color: #B78103;">👑 운영진 예치금 안내</span>
                <span style="background-color: #FFE082; color: #8C6200; font-size: 0.78rem; font-weight: bold; padding: 2px 8px; border-radius: 10px;">예치금 면제</span>
            </div>
            <p style="margin: 6px 0 0 0; color: #6D4C00; font-size: 0.88rem; line-height: 1.4;">
                운영진은 모임 기획 및 운영을 총괄하므로 시즌 예치금(20,000원) 납부 및 환급 요건이 적용되지 않습니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # 일반 부원
    is_first = dep_info['is_first_season']
    member_type_tag = "🌱 첫 등록 신규 부원" if is_first else "⭐ 기존 활동 부원"
    tag_bg = "#E8F5E9" if is_first else "#E3F2FD"
    tag_color = "#2E7D32" if is_first else "#1565C0"
    
    target = dep_info['target_count']
    curr = dep_info['current_count']
    remain = dep_info['remaining_count']
    is_eligible = dep_info['is_eligible']
    
    progress_pct = min(100, int((curr / target * 100))) if target > 0 else 100
    
    if is_eligible:
        border_color = "#81C784"
        bg_color = "#F1F8E9"
        status_badge = '<span style="background-color: #4CAF50; color: white; font-size: 0.8rem; font-weight: bold; padding: 4px 10px; border-radius: 12px;">🎉 환급 요건 달성!</span>'
        status_msg = f"축하합니다! 이번 <b>{curr_s_label}</b> 목표 출석(<b>{target}회</b>)을 모두 달성하셨습니다.<br/>시즌 종료 후 등록하신 계좌로 예치금 <b>20,000원</b>이 100% 전액 반환됩니다. 💸"
    else:
        border_color = "#90CAF9"
        bg_color = "#F6FAFD"
        status_badge = f'<span style="background-color: #1976D2; color: white; font-size: 0.8rem; font-weight: bold; padding: 4px 10px; border-radius: 12px;">활동 중 ({curr}/{target}회)</span>'
        status_msg = f"앞으로 <b>{remain}회 더 출석</b>하시면 시즌 종료 후 예치금(20,000원) 100% 반환 대상이 됩니다! 🏃‍♂️"

    st.markdown(f"""
    <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 14px; padding: 16px 18px; margin: 10px 0 18px 0; box-shadow: 0 3px 8px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
                <span style="font-weight: 800; font-size: 1.02rem; color: #1E293B;">💰 나의 예치금 & 환급 현황</span>
                <span style="background-color: {tag_bg}; color: {tag_color}; font-size: 0.78rem; font-weight: bold; padding: 3px 8px; border-radius: 8px; margin-left: 6px;">{member_type_tag}</span>
            </div>
            {status_badge}
        </div>
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.86rem; color: #475569; margin-bottom: 4px;">
                <span><b>{curr_s_label}</b> 출석 달성률 ({curr}회 / {target}회)</span>
                <b>{progress_pct}%</b>
            </div>
            <div style="background-color: #E2E8F0; border-radius: 10px; height: 10px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #4CAF50, #2E7D32); height: 100%; width: {progress_pct}%; border-radius: 10px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        <div style="background-color: #FFFFFF; border-radius: 10px; padding: 10px 14px; border: 1px solid #E2E8F0; font-size: 0.88rem; color: #334155; line-height: 1.45;">
            {status_msg}
            <div style="font-size: 0.8rem; color: #64748B; margin-top: 6px; border-top: 1px dashed #E2E8F0; padding-top: 5px;">
                • 기준: <b>신규 첫 등록</b>은 1시즌(2개월) 내 <b>4회</b> / <b>다음 시즌부터</b>는 <b>3회</b> 출석 시 반환 (정규 1회, 라운징 0.5회 인정)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def sync_accounting_pipeline_with_members():
    """
    회계장부 시트와 회원목록 시트를 연동하여 입출금에 따라 등록 및 환급 상태 자동 동기화
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
    
    updated_count = 0
    # 회계장부 각 워크시트(수입/지출/입출금내역 등) 검사
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
            
            for m_idx, m in enumerate(all_members):
                m_name = str(m.get("이름", '')).strip()
                if not m_name:
                    continue
                
                # 입금 매칭
                if m_name in row_text and (in_amt or in_col is None):
                    target_season = calculate_deposit_season(row_date, row_text)
                    if str(m.get("등록여부")) != "1" or str(m.get("현재등록시즌")) != str(target_season):
                        sheet_row = m_idx + 2
                        ws_mem.update_cell(sheet_row, 3, "1")
                        ws_mem.update_cell(sheet_row, 8, target_season)
                        if not str(m.get("처음등록시즌", "")).strip():
                            ws_mem.update_cell(sheet_row, 9, target_season)
                        updated_count += 1

    fetch_google_sheet_members.clear()
    st.cache_data.clear()
    return True, f"{updated_count}명의 회원이 회계장부와 동기화되었습니다."

