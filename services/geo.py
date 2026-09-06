import math
import streamlit.components.v1 as components

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    위도, 경도 좌표간 거리를 하버사인(Haversine) 공식을 이용하여 미터(m) 단위로 계산
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
    
    return R * c

# 주요 장소 프리셋
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

import os
_GPS_COMP_DIR = os.path.join(os.path.dirname(__file__), "gps_component")
_planet_gps = components.declare_component("planet_gps", path=_GPS_COMP_DIR)

def render_gps_verifier(target_name="할리스 종각역점", already_verified=False, key="planet_gps_loc"):
    """
    모임 현장 위치(GPS) 인증을 위한 네이티브 플래닛 컴포넌트 렌더링
    - 버튼과 장소 안내 텍스트가 한 줄(Flexbox)에 완벽하게 일체화
    - 모던하고 깔끔한 한국어 [📍 위치 인증] 버튼 및 반응형 상태 전환
    """
    try:
        return _planet_gps(
            target_name=target_name,
            already_verified=already_verified,
            key=key,
            default=None
        )
    except Exception:
        return None

def render_geolocation_button():
    """
    현장 출석 인증 버튼 HTML 컴포넌트를 렌더링
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
