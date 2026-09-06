import unittest
from datetime import date
from collections import Counter

from services.geo import haversine_distance
from services.config import format_season_display
from services.accounting import calculate_deposit_season

class TestPlanetCoreLogic(unittest.TestCase):
    """
    북클럽 플래닛 핵심 비즈니스 로직 단위 테스트
    """

    def test_haversine_distance_zero(self):
        """동일한 좌표 간의 거리는 0m여야 함"""
        lat, lng = 37.5699, 126.9823
        dist = haversine_distance(lat, lng, lat, lng)
        self.assertAlmostEqual(dist, 0.0, places=2)

    def test_haversine_distance_calculation(self):
        """종각역(37.5699, 126.9823)과 역삼역(37.5007, 127.0366) 간 거리 계산 (약 9.2km)"""
        dist = haversine_distance(37.5699, 126.9823, 37.5007, 127.0366)
        self.assertTrue(9000 <= dist <= 9500, f"예상 거리 범위(9000~9500m) 벗어남: {dist}m")

    def test_season_formatting(self):
        """시즌 코드 포맷팅 검증"""
        self.assertEqual(format_season_display("2609"), "2609시즌(9~10월)")
        self.assertEqual(format_season_display("2612"), "2612시즌(12~1월)")
        self.assertEqual(format_season_display(""), "")

    def test_calculate_deposit_season_cutoff(self):
        """20일 컷오프 규칙 검증: 20일 이상은 익월 시즌, 19일 이하는 당월 시즌"""
        # 8월 25일 입금 -> 2609 시즌 (조기 입금)
        self.assertEqual(calculate_deposit_season(deposit_date=date(2026, 8, 25)), "2609")
        # 9월 5일 입금 -> 2609 시즌 (당월 입금)
        self.assertEqual(calculate_deposit_season(deposit_date=date(2026, 9, 5)), "2609")
        # 12월 22일 입금 -> 2701 시즌 (연도 넘어감)
        self.assertEqual(calculate_deposit_season(deposit_date=date(2026, 12, 22)), "2701")

    def test_calculate_deposit_season_memo_priority(self):
        """적요/메모에 명시된 시즌 코드가 날짜보다 1순위로 우선 적용되는지 검증"""
        # 날짜는 8월 5일이지만 적요에 '2610'이 적힌 경우 -> 2610
        self.assertEqual(calculate_deposit_season(deposit_date=date(2026, 8, 5), memo="홍길동 2610"), "2610")
        # 적요에 '10월'이 적힌 경우 -> 2610
        self.assertEqual(calculate_deposit_season(deposit_date=date(2026, 8, 5), memo="홍길동 10월 회비"), "2610")

    def test_duplicate_name_detection_logic(self):
        """동명이인 감지 및 식별자 판별 단위 테스트"""
        members = [
            {"이름": "김민수", "닉네임": "달빛", "전화번호": "010-1111-2222"},
            {"이름": "김민수", "닉네임": "햇살", "전화번호": "010-3333-4444"},
            {"이름": "이영희", "닉네임": "별님", "전화번호": "010-5555-6666"}
        ]
        
        # 1. 이름 빈도 카운트
        name_counts = Counter([m["이름"] for m in members])
        duplicate_names = {name for name, count in name_counts.items() if count > 1}
        
        self.assertIn("김민수", duplicate_names)
        self.assertNotIn("이영희", duplicate_names)

        # 2. 적요에 식별자(전화번호 뒤 4자리)가 있는 경우
        memo1 = "김민수4444"
        matched_member = None
        for m in members:
            if m["이름"] in memo1 and m["전화번호"][-4:] in memo1:
                matched_member = m
                break
        self.assertIsNotNone(matched_member)
        self.assertEqual(matched_member["닉네임"], "햇살")

        # 3. 적요에 식별자가 없어 특정할 수 없는 경우 (단순 '김민수')
        memo2 = "김민수"
        identified = []
        for m in members:
            if m["이름"] in memo2:
                # 닉네임이나 전화번호 뒤 4자리 확인
                if m["닉네임"] in memo2 or m["전화번호"][-4:] in memo2:
                    identified.append(m)
        self.assertEqual(len(identified), 0)  # 특정 불가 -> 보류 대상

if __name__ == "__main__":
    unittest.main()
