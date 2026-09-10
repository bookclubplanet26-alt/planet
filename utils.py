"""
utils.py - 북클럽 플래닛 통합 유틸리티 Facade 브릿지 모듈
- 하위 호환성을 완벽히 보장하기 위해 services 패키지의 모든 서비스/유틸리티를 통합 re-export합니다.
- 모듈별 구현체는 services/ 패키지에서 독립적으로 관리됩니다.
"""

# 1. 설정 및 시간/시즌 유틸리티 (services/config.py)
from services.config import (
    SEASON_DATE_CONFIG,
    GOOGLE_SHEET_ID,
    GOOGLE_SHEET_ATTENDANCE_ID,
    ATTENDANCE_WEBHOOK_URL,
    SERVICE_ACCOUNT_FILE,
    get_current_kst,
    get_club_season_code,
    format_season_display,
)

# 2. GPS 및 현장 위치 계산 모듈 (services/geo.py)
from services.geo import (
    haversine_distance,
    LOCATION_PRESETS,
    get_meeting_target_gps,
    render_geolocation_button,
    render_gps_verifier,
)

# 3. 구글 시트 연동 전담 모듈 (services/sheets.py)
from services.sheets import (
    get_gspread_client,
    fetch_google_sheet_members,
    fetch_google_sheet_attendances,
    fetch_google_sheet_meetings,
    fetch_google_sheet_rsvps,
    get_google_sheet_meetings_list,
    get_all_meetings,
    get_meeting_by_id,
    get_rsvps_for_meeting,
    add_rsvp,
    cancel_rsvp,
    append_attendance_to_google_sheet_async,
    append_meeting_to_google_sheet_async,
    delete_meeting_from_google_sheet_async,
    add_rsvp_to_google_sheet_async,
    cancel_rsvp_from_google_sheet_async,
    fetch_google_sheet_facilitators,
    get_meeting_facilitator,
    get_all_meeting_rsvps_map,
)

# 4. 예치금 및 출석 통계 모듈 (services/accounting.py)
from services.accounting import (
    get_member_attendance_count,
    count_member_season_attendances,
    calculate_deposit_season,
    get_member_deposit_info,
    check_member_season_eligibility,
    format_member_attendance_and_deposit_text,
    render_deposit_refund_card,
)
