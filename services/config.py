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
GOOGLE_SHEET_FACILITATOR_ID = _get_secret("GOOGLE_SHEET_FACILITATOR_ID", "1KRaQb_WylR0c5YcOsTxgKXP6fpwPhbXwfSRWydMyiBk")
ATTENDANCE_WEBHOOK_URL = _get_secret(
    "ATTENDANCE_WEBHOOK_URL", 
    "https://script.google.com/macros/s/AKfycbw1KwJAy3_GGXkQ_pYISTxExafydX2JGPyY6BsS711V1m4s49N7VwDL2dmeJbF8qBFMrA/exec"
)
WEBHOOK_SECRET_KEY = _get_secret("WEBHOOK_SECRET_KEY", "planet_default_auth_key_2026")

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
        "excluded_dates": [],
        "display_name": "2609시즌(9~10월)"
    },
    "2610": {
        "start": "2026-10-03",
        "end": "2026-11-29",
        "excluded_dates": [],
        "display_name": "2610시즌(10~11월)"
    }
}

def get_season_date_config():
    """
    동적 시즌 날짜 범위 설정 반환
    1순위: 구글 스프레드시트 '시즌일정' 탭 동적 캐시
    2순위: SEASON_DATE_CONFIG (fallback)
    """
    try:
        from services.sheets import fetch_google_sheet_seasons
        cfg = fetch_google_sheet_seasons()
        if cfg and isinstance(cfg, dict) and len(cfg) > 0:
            return cfg
    except Exception:
        pass
    return SEASON_DATE_CONFIG

def get_club_season_code(dt=None):
    """
    날짜 기준 소속 시즌 코드 반환 (구글 시트 시즌일정 동적 매핑 우선)
    """
    if dt is None:
        dt = get_current_kst()
    
    if hasattr(dt, 'date'):
        d_val = dt.date()
    else:
        d_val = dt
    
    d_str = d_val.strftime("%Y-%m-%d")
    s_config = get_season_date_config()
    for s_code, s_conf in s_config.items():
        if s_conf.get("start") and s_conf.get("end"):
            if s_conf["start"] <= d_str <= s_conf["end"]:
                return s_code
            
    year_short = dt.strftime("%y")
    return f"{year_short}{dt.month:02d}"

def format_season_display(season_code):
    """
    시즌 코드(예: 2609, 2610)를 친절한 라벨로 변환
    - 시즌일정 탭의 display_name 우선 사용
    - 예: '2609' -> '2609시즌(9~10월)'
    """
    if not season_code:
        return ""
    code_str = str(season_code).strip()
    s_config = get_season_date_config()
    if code_str in s_config and s_config[code_str].get("display_name"):
        return s_config[code_str]["display_name"]

    if len(code_str) == 4 and code_str.isdigit():
        month_start = int(code_str[2:])
        month_end = month_start + 1
        if month_end > 12:
            month_end = 1
        return f"{code_str}시즌({month_start}~{month_end}월)"
    return f"{code_str}시즌"

