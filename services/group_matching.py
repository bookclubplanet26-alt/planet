"""
services/group_matching.py - 자유책 모임 스마트 조 배치 및 노쇼 재분배 엔진

[핵심 원칙]
1. 가입시즌(처음등록시즌) × 조배치 열(0/1) 4분할 매트릭스 라운드로빈 배정
2. 테이블당 기본 4명 목표 (3~5명 허용)
3. 노쇼/결원 발생 시 [조 해체 및 분산 흡수] 알고리즘 지원
"""

import math
import random
from typing import List, Dict, Any, Tuple


def classify_member(member: Dict[str, Any], cutoff_season: str = "2609") -> str:
    """
    회원의 처음등록시즌과 조배치 속성을 기준으로 4개 버킷 분류:
    - OLD_0: 기존 멤버 + 조배치 0
    - OLD_1: 기존 멤버 + 조배치 1
    - NEW_0: 신규 멤버 + 조배치 0
    - NEW_1: 신규 멤버 + 조배치 1
    """
    raw_season = str(member.get("season", "") or member.get("처음등록시즌", "")).strip()
    raw_attr = str(member.get("group_attr", "") or member.get("조배치", "")).strip()

    # 가입 시즌 판정 (숫자 비교 또는 문자열 비교)
    # 예: "2609" 이상이면 신규, 미만이면 기존
    is_new = False
    try:
        s_val = int("".join(filter(str.isdigit, raw_season))) if any(c.isdigit() for c in raw_season) else 0
        c_val = int("".join(filter(str.isdigit, cutoff_season))) if any(c.isdigit() for c in cutoff_season) else 2609
        if s_val > 0 and c_val > 0:
            is_new = (s_val >= c_val)
        else:
            is_new = (raw_season >= cutoff_season) if raw_season else False
    except Exception:
        is_new = (raw_season >= cutoff_season) if raw_season else False

    # 조배치 속성 판정 (기본값 '0')
    attr = "1" if "1" in raw_attr else "0"

    season_type = "NEW" if is_new else "OLD"
    return f"{season_type}_{attr}"


def calculate_optimal_group_count(total_count: int, target_size: int = 4) -> int:
    """
    전체 인원과 목표 인원(기본 4명)을 바탕으로 조 개수 N을 최적 계산.
    - 조당 인원이 3명 이상 5명 이하가 되도록 조정.
    """
    if total_count <= 0:
        return 0
    if total_count <= 5:
        return 1

    # 기본 조 개수: 반올림
    n_groups = max(1, round(total_count / target_size))

    # 조당 평균 인원이 3.5명 미만인 경우 (예: 6명인데 2개 조로 나누면 3, 3 -> 괜찮지만 5명이면 1개 조)
    avg = total_count / n_groups
    if avg < 3.2 and n_groups > 1:
        n_groups -= 1

    return n_groups


def assign_groups(
    participants: List[Dict[str, Any]],
    target_size: int = 4,
    cutoff_season: str = "2609",
    seed: int = None
) -> List[Dict[str, Any]]:
    """
    4분할 매트릭스 라운드로빈 방식으로 참가자를 균등하게 조 배치.
    
    반환 형태:
    [
        {
            "group_num": 1,
            "table_name": "1조 (테이블 A)",
            "members": [...],
            "stats": {"total": 4, "old": 2, "new": 2, "attr_0": 2, "attr_1": 2}
        },
        ...
    ]
    """
    if not participants:
        return []

    if seed is not None:
        random.seed(seed)

    # 1. 4개 버킷 분류
    buckets = {
        "OLD_0": [],
        "OLD_1": [],
        "NEW_0": [],
        "NEW_1": []
    }

    for p in participants:
        cat = classify_member(p, cutoff_season=cutoff_season)
        p_copy = dict(p)
        p_copy["category"] = cat
        p_copy["is_new"] = cat.startswith("NEW")
        p_copy["attr"] = cat.split("_")[1]
        buckets[cat].append(p_copy)

    # 2. 각 버킷 내 무작위 셔플
    for cat in buckets:
        random.shuffle(buckets[cat])

    # 3. 조 개수 결정
    total_count = len(participants)
    n_groups = calculate_optimal_group_count(total_count, target_size=target_size)

    # 각 조 초기화
    groups_data = [{"group_num": i + 1, "members": []} for i in range(n_groups)]

    # 4. 라운드로빈 배정: 버킷 순환
    # 버킷 우선순위: 인원이 많은 버킷부터 번갈아가며 분배
    sorted_buckets = sorted(buckets.keys(), key=lambda k: len(buckets[k]), reverse=True)

    group_idx = 0
    for b_key in sorted_buckets:
        for member in buckets[b_key]:
            groups_data[group_idx % n_groups]["members"].append(member)
            group_idx += 1

    # 5. 조별 통계 및 결과 포맷팅
    result = []
    for g in groups_data:
        m_list = g["members"]
        stats = {
            "total": len(m_list),
            "old": sum(1 for m in m_list if not m["is_new"]),
            "new": sum(1 for m in m_list if m["is_new"]),
            "attr_0": sum(1 for m in m_list if m["attr"] == "0"),
            "attr_1": sum(1 for m in m_list if m["attr"] == "1"),
        }
        result.append({
            "group_num": g["group_num"],
            "table_name": f"{g['group_num']}조",
            "members": m_list,
            "stats": stats
        })

    return result


def dissolve_and_redistribute_group(
    groups: List[Dict[str, Any]],
    dissolve_group_index: int
) -> List[Dict[str, Any]]:
    """
    [노쇼/결원 대응: 2번 조 해체 및 분산 흡수]
    특정 조(dissolve_group_index)를 해체하고, 남은 인원들을 타 조들에 1명씩 최적으로 분산 흡수.
    - 인원이 적은 조 우선 배치
    - 해당 조의 (기존/신규, 0/1) 속성 균형이 개선되는 방향으로 매칭
    """
    if not groups or dissolve_group_index < 0 or dissolve_group_index >= len(groups):
        return groups

    if len(groups) <= 1:
        # 조가 1개뿐이면 해체 불가
        return groups

    # 해체할 조 복사 및 분리
    target_group = groups[dissolve_group_index]
    remaining_groups = [g for i, g in enumerate(groups) if i != dissolve_group_index]
    orphaned_members = list(target_group["members"])

    # 분산 배치 알고리즘
    for member in orphaned_members:
        # 각 남은 조에 넣었을 때의 점수(불균형 페널티) 계산
        best_g_idx = 0
        min_penalty = float("inf")

        for idx, g in enumerate(remaining_groups):
            m_count = len(g["members"])
            # 1. 인원 수 페널티 (인원이 적은 조 선호)
            penalty = m_count * 10

            # 2. 속성 밸런스 페널티 계산 (시뮬레이션)
            curr_old = g["stats"]["old"] + (1 if not member["is_new"] else 0)
            curr_new = g["stats"]["new"] + (1 if member["is_new"] else 0)
            curr_0 = g["stats"]["attr_0"] + (1 if member["attr"] == "0" else 0)
            curr_1 = g["stats"]["attr_1"] + (1 if member["attr"] == "1" else 0)

            # 신규/기존 편차 + 속성 0/1 편차
            balance_diff = abs(curr_old - curr_new) + abs(curr_0 - curr_1)
            penalty += balance_diff

            if penalty < min_penalty:
                min_penalty = penalty
                best_g_idx = idx

        # 최적 조에 흡수
        chosen_group = remaining_groups[best_g_idx]
        chosen_group["members"].append(member)
        # 통계 갱신
        m_list = chosen_group["members"]
        chosen_group["stats"] = {
            "total": len(m_list),
            "old": sum(1 for m in m_list if not m["is_new"]),
            "new": sum(1 for m in m_list if m["is_new"]),
            "attr_0": sum(1 for m in m_list if m["attr"] == "0"),
            "attr_1": sum(1 for m in m_list if m["attr"] == "1"),
        }

    # 조 번호 재정렬
    for i, g in enumerate(remaining_groups):
        g["group_num"] = i + 1
        g["table_name"] = f"{i + 1}조"

    return remaining_groups


def remove_member_from_groups(groups: List[Dict[str, Any]], member_name: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    [개별 결원/노쇼 제외]
    모든 조에서 특정 회원(member_name)을 찾아서 제거하고 해당 조의 stats를 갱신.
    반환: (갱신된 groups, 변경된 조의 index 또는 -1)
    """
    if not groups or not member_name:
        return groups, -1

    changed_group_idx = -1
    for g_idx, g in enumerate(groups):
        m_list = g["members"]
        target_m = next((m for m in m_list if m["name"] == member_name), None)
        if target_m:
            m_list.remove(target_m)
            changed_group_idx = g_idx
            # 통계 갱신
            g["stats"] = {
                "total": len(m_list),
                "old": sum(1 for m in m_list if not m["is_new"]),
                "new": sum(1 for m in m_list if m["is_new"]),
                "attr_0": sum(1 for m in m_list if m["attr"] == "0"),
                "attr_1": sum(1 for m in m_list if m["attr"] == "1"),
            }
            break

    return groups, changed_group_idx


def fill_vacancy_from_largest_group(groups: List[Dict[str, Any]], target_group_idx: int) -> Tuple[List[Dict[str, Any]], str]:
    """
    [스마트 1인 보충]
    인원이 부족한 조(target_group_idx)에 대해, 가장 인원이 많은 조(5인 이상 조) 중
    신규/기존 밸런스를 가장 잘 맞출 수 있는 회원 1명을 자동으로 타겟 조로 이동.
    반환: (갱신된 groups, 이동된 회원 이름 또는 None)
    """
    if not groups or target_group_idx < 0 or target_group_idx >= len(groups):
        return groups, None

    target_g = groups[target_group_idx]
    target_count = len(target_g["members"])

    # 1. 인원이 가장 많은 조 후보 찾기 (현재 조보다 인원이 2명 이상 많거나 5명 이상인 조)
    donor_candidates = [
        (idx, g) for idx, g in enumerate(groups) 
        if idx != target_group_idx and len(g["members"]) >= 5
    ]
    if not donor_candidates:
        # 5명 조가 없으면 4명 조 중에서도 현재 타겟이 2명 이하일 경우 허용
        if target_count <= 2:
            donor_candidates = [
                (idx, g) for idx, g in enumerate(groups) 
                if idx != target_group_idx and len(g["members"]) >= 4
            ]

    if not donor_candidates:
        return groups, None

    # 가장 인원 많은 조 우선 (내림차순)
    donor_candidates.sort(key=lambda item: len(item[1]["members"]), reverse=True)
    donor_idx, donor_g = donor_candidates[0]

    # 2. 이동시킬 최적의 1인 선발 (타겟 조의 밸런스를 개선하는 회원)
    best_member = None
    min_penalty = float("inf")

    t_old = target_g["stats"]["old"]
    t_new = target_g["stats"]["new"]

    for m in donor_g["members"]:
        # 타겟 조에 추가했을 때 밸런스 점수
        sim_old = t_old + (1 if not m["is_new"] else 0)
        sim_new = t_new + (1 if m["is_new"] else 0)
        penalty = abs(sim_old - sim_new)

        if penalty < min_penalty:
            min_penalty = penalty
            best_member = m

    if not best_member:
        best_member = donor_g["members"][-1]

    # 3. 회원 이동 및 양쪽 통계 갱신
    donor_g["members"].remove(best_member)
    target_g["members"].append(best_member)

    for g in [donor_g, target_g]:
        m_list = g["members"]
        g["stats"] = {
            "total": len(m_list),
            "old": sum(1 for m in m_list if not m["is_new"]),
            "new": sum(1 for m in m_list if m["is_new"]),
            "attr_0": sum(1 for m in m_list if m["attr"] == "0"),
            "attr_1": sum(1 for m in m_list if m["attr"] == "1"),
        }

    return groups, best_member["name"]

