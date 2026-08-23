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
ATTENDANCE_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzM2xLKrQCHdBKqZ8oMwJtVFRUED9gxSdQbzag5I56G5JxEkOLxxcvVar5Hujgj83WM4Q/exec"

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

def fetch_google_sheet_members():
    """
    사용자의 구글 시트에서 회원 명단(이메일, 이름, 닉네임, 등록여부 등)을 실시간으로 가져오는 함수
    """
    urls = [
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0",
        f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&gid=0"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200 and "html" not in res.text[:100].lower():
                raw_bytes = res.content
                # utf-8, cp949 인코딩 순차 시도
                for enc in ["utf-8", "cp949", "euc-kr"]:
                    try:
                        df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
                        if len(df.columns) > 1:
                            return True, df, None
                    except Exception:
                        continue
        except Exception as e:
            continue
            
    return False, None, "구글 시트 공유 설정('링크가 있는 모든 사용자에게 공개') 확인이 필요합니다."

@st.cache_data(ttl=10, show_spinner=False)
def fetch_google_sheet_attendances():
    """
    출석전용 구글 시트(1k1lJmH6fmsPKD8h_-QMbTVy6nrh-RTJt-fUJAQWukKE)에서 실시간 출석 기록을 가져오는 함수 (10초 캐싱으로 대폭 속도 향상)
    """
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ATTENDANCE_ID}/export?format=csv&gid=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            df = pd.read_csv(io.BytesIO(res.content), encoding="utf-8")
            return True, df
    except Exception:
        pass
    return False, None

def get_member_attendance_count(email, name=""):
    """
    구글 시트 출석 기록에서 해당 회원의 이번 시즌 출석 횟수를 실시간 집계 (라운징 0.5회, 정규 1회)
    """
    ok, df = fetch_google_sheet_attendances()
    if not ok or df is None or df.empty:
        return 0
    
    current_season = get_club_season_code()
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
        
        # 시즌 체크 (시즌 값이 없거나 현재 시즌과 일치하는 경우)
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

def append_attendance_to_google_sheet_async(webhook_url, checked_at, email, name, year, season, meeting_name, book_read, book_review="", is_lounging=0):
    """
    백그라운드 비동기 스레드(Async Thread)로 구글 시트에 전송하여 사용자 대기시간 0초로 단축!
    - is_lounging: 라운징 선택시 1, 아니면 0
    """
    import threading
    if not webhook_url:
        return False
    
    full_book_info = book_read
    if book_review:
        full_book_info = f"{book_read} (💬 {book_review})"

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
        "라운징": is_lounging
    }
    
    # 캐시 지우기 (다음번 조회시 반영)
    st.cache_data.clear()
    
    # 백그라운드 비동기 스레드 시작
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
