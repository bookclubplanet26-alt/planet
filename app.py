import runpy
# Streamlit Cloud 배포 핫 리로드 트리거 (v2026.10.09_04 - 모임일정 상단 탭 원복 및 관리자 인증 시 사이드바 App 바로가기 메뉴에 조배치 탭 동적 연동)
runpy.run_path("바로가기.py")
