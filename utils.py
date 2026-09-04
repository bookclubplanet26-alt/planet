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

def get_club_season_code(dt=None):
    """
    2달 간격 시즌 코드 (시작 월 기준 매월 롤링 시즌)
    - 2601: 1월~2월 시즌
    - 2602: 2월~3월 시즌
    ...
    - 2608: 8월~9월 시즌 (현재 8월)
    """
    if dt is None:
        from datetime import datetime
        dt = datetime.now()
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
        if hasattr(st, "secrets") and ("gcp_service_account" in st.secrets or "text" in str(st.secrets)):
            from google.oauth2.service_account import Credentials
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            if "gcp_service_account" in st.secrets:
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
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

def _async_send_post(webhook_url, payload):
    try:
        requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

def append_attendance_to_google_sheet_async(webhook_url, checked_at, email, name, year, season, meeting_name, book_read, book_review="", is_lounging=0, book_author="", rating=5):
    """
    백그라운드 비동기 스레드(Async Thread)로 구글 시트에 전송하여 사용자 대기시간 0초로 단축!
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
    
    # 캐시 지우기 (다음번 조회시 반영)
    st.cache_data.clear()
    
    # 백그라운드 비동기 스레드 시작
    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
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

def add_rsvp_to_google_sheet_async(webhook_url, meeting_name, member_name, email, participation_type="자유책", meeting_date=""):
    """
    백그라운드 비동기 스레드로 구글 시트 신청명단에 참가 신청 정보 전송 (대기시간 0초)
    """
    import threading
    if not webhook_url:
        return False

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    try:
        fetch_google_sheet_rsvps.clear()
        st.cache_data.clear()
    except Exception:
        pass

    t = threading.Thread(target=_async_send_post, args=(webhook_url, payload), daemon=True)
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
