import io
import os
import requests
import threading
import pandas as pd
import streamlit as st
import gspread

from services.config import (
    GOOGLE_SHEET_ID, GOOGLE_SHEET_ATTENDANCE_ID,
    SERVICE_ACCOUNT_FILE, get_current_kst
)

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
    백그라운드 비동기 스레드로 웹훅 URL에 POST 전송 (요청 대기시간 0초)
    """
    try:
        if webhook_url:
            requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

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
                    return True, df
                except Exception:
                    continue
    except Exception:
        pass
    return False, None

def get_google_sheet_meetings_list():
    """
    구글 시트 '모임목록' 탭에서 모임 레코드 리스트 추출
    """
    ok, df = fetch_google_sheet_meetings()
    if not ok or df is None or df.empty:
        return []

    meetings = []
    for idx, row in df.iterrows():
        title = str(row.get('모임명', '')).strip()
        date_str = str(row.get('모임일자', '')).strip()
        time_str = str(row.get('모임시간', '')).strip()
        loc_name = str(row.get('장소명', '')).strip()
        book_title = str(row.get('도서명', '')).strip()
        author = str(row.get('저자', '')).strip()
        desc = str(row.get('설명', '')).strip()
        
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
                "description": desc
            })
    return meetings

def append_attendance_to_google_sheet_async(webhook_url, checked_at, email, name, year, season, meeting_name, book_read, book_review="", is_lounging=0, book_author="", rating=5):
    """
    백그라운드 비동기 스레드로 구글 시트에 출석 정보 전송 (사용자 대기시간 0초)
    """
    if not webhook_url:
        return False
    
    full_book_info = book_read
    review_parts = []
    if book_author:
        review_parts.append(f"✍️ {book_author}")
    if rating:
        review_parts.append("⭐" * int(rating))
    if book_review:
        review_parts.append(f"💬 {book_review}")
        
    if review_parts:
        full_book_info = f"{book_read} ({' | '.join(review_parts)})"

    payload = {
        "checked_at": checked_at,
        "email": email,
        "name": name,
        "year": year,
        "season": season,
        "meeting_name": meeting_name,
        "book_read": full_book_info,
        "book_review": book_review,
        "review": book_review,
        "감상평": book_review,
        "is_lounging": is_lounging,
        "lounging": is_lounging,
        "라운징": is_lounging,
        "book_author": book_author,
        "rating": rating
    }
    
    try:
        fetch_google_sheet_attendances.clear()
        st.cache_data.clear()
    except Exception:
        pass
    
    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
    t.start()
    return True

def append_meeting_to_google_sheet_async(webhook_url, title, book_title, author, meeting_date, meeting_time, location_name, max_participants=8, description="", season="", jijung_leader="", kakao_url=""):
    """
    새로 개설된 모임 정보를 구글 시트 웹훅으로 비동기 전송
    """
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
        "type": "add_meeting",
        "action": "add_meeting",
        "title": title,
        "book_title": book_title,
        "author": author,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "location_name": location_name,
        "max_participants": max_participants,
        "description": description,
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

    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
    t.start()
    return True

def delete_meeting_from_google_sheet_async(webhook_url, title, meeting_date=""):
    """
    구글 시트에서 모임 삭제 요청 전송
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
            ws = sh.worksheet("신청명단") if "신청명단" in [w.title for w in sh.worksheets()] else None
            if ws:
                ws.append_row(row_data)
                return
    except Exception:
        pass

    try:
        if webhook_url:
            requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

def add_rsvp_to_google_sheet_async(webhook_url, meeting_name, member_name, email, participation_type="자유책", meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에 참가 신청 정보 전송 (대기시간 0초)
    """
    if not webhook_url:
        return False

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
        "참여방식": participation_type,
        "방식": participation_type
    }

    row_data = [
        now_str,
        meeting_name,
        meeting_date if meeting_date else "",
        member_name,
        email,
        participation_type
    ]

    try:
        fetch_google_sheet_rsvps.clear()
        st.cache_data.clear()
    except Exception:
        pass

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
            ws = sh.worksheet("신청명단") if "신청명단" in [w.title for w in sh.worksheets()] else None
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
            requests.post(webhook_url, json=payload, timeout=8)
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

    t = threading.Thread(target=_async_cancel_rsvp, args=(webhook_url, payload, meeting_name, email, member_name, meeting_date), daemon=True)
    t.start()
    return True
