import os
import streamlit as st
from datetime import datetime, timezone, timedelta

def _get_secret(key, default_val):
    """
    st.secrets에서 키를 우선 탐색하고, 없으면 기본값을 반환
    """
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default_val

# 구글 시트 ID 및 Webhook 설정 (st.secrets 우선 조회, 미설정 시 기존 기본값 자동 fallback)
GOOGLE_SHEET_ID = _get_secret("GOOGLE_SHEET_ID", "1UbvS5tDzQvGlOh-TVagtYJ31pW9u8CNw-wENIK8iK48")
GOOGLE_SHEET_ATTENDANCE_ID = _get_secret("GOOGLE_SHEET_ATTENDANCE_ID", "1k1lJmH6fmsPKD8h_-QMbTVy6nrh-RTJt-fUJAQWukKE")
ATTENDANCE_WEBHOOK_URL = _get_secret(
    "ATTENDANCE_WEBHOOK_URL", 
    "https://script.google.com/macros/s/AKfycbw1KwJAy3_GGXkQ_pYISTxExafydX2JGPyY6BsS711V1m4s49N7VwDL2dmeJbF8qBFMrA/exec"
)

# GCP 서비스 계정 키 파일 경로 (st.secrets 또는 환경변수 우선 조회, 없으면 일반 service_account.json)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SERVICE_ACCOUNT_FILE = _get_secret(
    "SERVICE_ACCOUNT_FILE", 
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.join(PROJECT_ROOT, "service_account.json"))
)

def get_current_kst():
    """
    대한민국 표준시(KST, UTC+9) datetime 객체 반환
    - Streamlit Cloud(Linux UTC) 환경에서도 언제나 정확한 한국 시간 보장
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=9)))


# 시즌별 공식 운영 날짜 범위 및 제외일 매핑 테이블
SEASON_DATE_CONFIG = {
    "2609": {
        "start": "2026-09-05",
        "end": "2026-11-01",
        "excluded_dates": ["2026-09-26", "2026-09-27"],
        "display_name": "2609시즌(9~10월)"
    }
}

def get_club_season_code(dt=None):
    """
    날짜 기준 소속 시즌 코드 반환 (공식 시즌 날짜 범위 우선 매핑)
    - 2609 시즌: 2026-09-05 ~ 2026-11-01 (11월 1일도 2609 시즌으로 완벽 매핑)
    - 그 외: 기존 2달 롤링 규칙
    """
    if dt is None:
        dt = get_current_kst()
    
    if hasattr(dt, 'date'):
        d_val = dt.date()
    else:
        d_val = dt
    
    d_str = d_val.strftime("%Y-%m-%d")
    for s_code, s_conf in SEASON_DATE_CONFIG.items():
        if s_conf["start"] <= d_str <= s_conf["end"]:
            return s_code
            
    year_short = dt.strftime("%y")
    return f"{year_short}{dt.month:02d}"

def format_season_display(season_code):
    """
    시즌 코드(예: 2609, 2610)를 친절한 라벨로 변환
    - 예: '2609' -> '2609시즌(9~10월)'
    """
    if not season_code:
        return ""
    code_str = str(season_code).strip()
    if len(code_str) == 4 and code_str.isdigit():
        month_start = int(code_str[2:])
        month_end = month_start + 1
        if month_end > 12:
            month_end = 1
        return f"{code_str}시즌({month_start}~{month_end}월)"
    return f"{code_str}시즌"
