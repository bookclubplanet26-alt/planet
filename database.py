import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "club.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 회원 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        email TEXT,
        deposit_status TEXT DEFAULT '대기', -- 대기, 승인, 미입금
        deposit_amount INTEGER DEFAULT 20000,
        fav_genre TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 모임 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        book_title TEXT NOT NULL,
        author TEXT,
        meeting_date TEXT NOT NULL, -- YYYY-MM-DD
        meeting_time TEXT NOT NULL, -- HH:MM
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        max_participants INTEGER DEFAULT 8,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # RSVP (참가 신청) 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rsvps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        member_name TEXT NOT NULL,
        member_phone TEXT NOT NULL,
        participation_type TEXT DEFAULT '자유책',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(meeting_id, member_id),
        FOREIGN KEY (meeting_id) REFERENCES meetings(id),
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
    """)

    # 컬럼 추가 마이그레이션 호환
    try:
        cursor.execute("ALTER TABLE rsvps ADD COLUMN participation_type TEXT DEFAULT '자유책'")
    except sqlite3.OperationalError:
        pass

    # 출석 기록 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        member_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        distance_m REAL NOT NULL,
        book_read TEXT DEFAULT '자유책',
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(meeting_id, member_id),
        FOREIGN KEY (meeting_id) REFERENCES meetings(id),
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
    """)

    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN book_read TEXT DEFAULT '자유책'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN book_review TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN is_lounging INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()

    # 시드 데이터 삽입 (초기 데이터가 없을 경우)
    cursor.execute("SELECT COUNT(*) FROM members")
    if cursor.fetchone()[0] == 0:
        seed_data(cursor)
        conn.commit()

    conn.close()

def seed_data(cursor):
    # 샘플 회원
    sample_members = [
        ("김독서", "010-1234-5678", "book_kim@email.com", "승인", 20000, "인문/철학"),
        ("이문학", "010-2345-6789", "lee_lit@email.com", "승인", 20000, "소설/문학"),
        ("박과학", "010-3456-7890", "park_sci@email.com", "대기", 20000, "과학/지식"),
        ("최에세이", "010-4567-8901", "choi_essay@email.com", "승인", 20000, "에세이/자기계발"),
    ]
    cursor.executemany("""
    INSERT INTO members (name, phone, email, deposit_status, deposit_amount, fav_genre)
    VALUES (?, ?, ?, ?, ?, ?)
    """, sample_members)

    # 샘플 모임 (서울 시청, 강남역, 홍대입구 북카페 등 주요 GPS 좌표 포함)
    sample_meetings = [
        ("토요일 아침 문학 클럽", "데미안", "헤르만 헤세", "2026-08-15", "10:30", "강남 북카페 북클럽 플래닛", 37.4979, 127.0276, 6, "헤르만 헤세의 데미안을 함께 읽고 '자아 찾기'를 주제로 깊은 대화를 나눕니다."),
        ("수요일 저녁 인문학 모임", "사피엔스", "유발 하라리", "2026-08-19", "19:30", "홍대입구 문학살롱", 37.5563, 126.9226, 8, "인류의 역사와 미래에 대해 자유롭게 의견을 공유하는 저녁 정기 모임입니다."),
        ("일요일 오후 과학독서회", "코스모스", "칼 세이건", "2026-08-23", "14:00", "광화문 교보문고 미팅룸", 37.5709, 126.9778, 5, "우주와 인간의 존재에 관한 칼 세이건의 통찰을 나눕니다."),
    ]
    cursor.executemany("""
    INSERT INTO meetings (title, book_title, author, meeting_date, meeting_time, location_name, latitude, longitude, max_participants, description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_meetings)

    # 샘플 RSVP
    cursor.execute("""
    INSERT INTO rsvps (meeting_id, member_id, member_name, member_phone, participation_type)
    VALUES (1, 1, '김독서', '010-1234-5678', '자유책')
    """)
    cursor.execute("""
    INSERT INTO rsvps (meeting_id, member_id, member_name, member_phone, participation_type)
    VALUES (1, 2, '이문학', '010-2345-6789', '라운징')
    """)

# CRUD 함수들
def get_all_members():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY id DESC")
    members = cursor.fetchall()
    conn.close()
    return members

def add_member(name, phone, email, fav_genre):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO members (name, phone, email, fav_genre, deposit_status)
        VALUES (?, ?, ?, ?, '대기')
        """, (name, phone, email, fav_genre))
        conn.commit()
        return True, "회원가입이 완료되었습니다! 예치금 입금 확인 후 승인 처리됩니다."
    except sqlite3.IntegrityError:
        return False, "이미 등록된 전화번호입니다. 확인 후 다시 시도해 주세요."
    finally:
        conn.close()

def update_deposit_status(member_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET deposit_status = ? WHERE id = ?", (status, member_id))
    conn.commit()
    conn.close()

def get_all_meetings():
    try:
        from utils import get_google_sheet_meetings_list
        gs_meetings = get_google_sheet_meetings_list()
        if gs_meetings:
            return gs_meetings
    except Exception:
        pass

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings ORDER BY meeting_date ASC, meeting_time ASC")
    meetings = cursor.fetchall()
    conn.close()
    return meetings

def get_meeting_by_id(meeting_id):
    try:
        meetings = get_all_meetings()
        for m in meetings:
            if m['id'] == meeting_id or str(m['id']) == str(meeting_id):
                return m
    except Exception:
        pass

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    conn.close()
    return meeting

def add_meeting(title, book_title, author, meeting_date, meeting_time, location_name, latitude, longitude, max_participants, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO meetings (title, book_title, author, meeting_date, meeting_time, location_name, latitude, longitude, max_participants, description)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, book_title, author, meeting_date, meeting_time, location_name, latitude, longitude, max_participants, description))
    conn.commit()
    conn.close()

def delete_meeting(meeting_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rsvps WHERE meeting_id = ?", (meeting_id,))
    cursor.execute("DELETE FROM attendance WHERE meeting_id = ?", (meeting_id,))
    cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()
    return True

import pandas as pd

def get_rsvps_for_meeting(meeting_id):
    meeting = get_meeting_by_id(meeting_id)
    m_title = meeting['title'] if meeting and (isinstance(meeting, dict) or hasattr(meeting, '__getitem__')) else ""
    m_date = str(meeting['meeting_date']).strip() if meeting and (isinstance(meeting, dict) or hasattr(meeting, '__getitem__')) and 'meeting_date' in meeting else ""

    rsvps = []
    seen_identifiers = set()

    try:
        from utils import fetch_google_sheet_rsvps
        ok, df = fetch_google_sheet_rsvps()
        if ok and df is not None and not df.empty:
            m_col = next((c for c in df.columns if any(k in str(c) for k in ["모임명", "모임", "title"])), df.columns[0])
            date_col = next((c for c in df.columns if any(k in str(c) for k in ["모임일자", "일자", "날짜", "date"])), None)
            name_col = next((c for c in df.columns if any(k in str(c) for k in ["회원명", "이름", "성함", "name"])), None)
            email_col = next((c for c in df.columns if any(k in str(c) for k in ["이메일", "email", "mail"])), None)
            type_col = next((c for c in df.columns if any(k in str(c) for k in ["참여방식", "방식", "type"])), None)

            for idx, row in df.iterrows():
                row_m = str(row.get(m_col, '')).strip()
                row_d = str(row.get(date_col, '')).strip() if date_col and pd.notna(row.get(date_col)) else ""

                # 모임명 비교
                title_match = m_title and (row_m == m_title or m_title in row_m or row_m in m_title)
                
                # 모임일자 비교 (시트에 모임일자 값이 등록된 경우에만 검증)
                date_match = True
                if row_d and m_date:
                    date_match = (row_d == m_date or m_date in row_d or row_d in m_date)

                if title_match and date_match:
                    r_name = str(row.get(name_col, '')).strip() if name_col and pd.notna(row.get(name_col)) else "회원"
                    r_email = str(row.get(email_col, '')).strip() if email_col and pd.notna(row.get(email_col)) else ""
                    r_type = str(row.get(type_col, '자유책')).strip() if type_col and pd.notna(row.get(type_col)) else "자유책"

                    identifier = r_email.strip().lower() if r_email else r_name.strip()
                    if identifier:
                        seen_identifiers.add(identifier)

                    rsvps.append({
                        "id": idx + 1,
                        "meeting_id": meeting_id,
                        "member_id": hash(r_email) % 100000 if r_email else idx + 100,
                        "member_name": r_name,
                        "member_phone": r_email,
                        "participation_type": r_type
                    })
    except Exception:
        pass

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rsvps WHERE meeting_id = ?", (meeting_id,))
        db_rsvps = cursor.fetchall()
        conn.close()
        for row in db_rsvps:
            r_phone = str(row['member_phone'] or '').strip().lower()
            r_name = str(row['member_name'] or '').strip()
            identifier = r_phone if r_phone else r_name
            if identifier not in seen_identifiers:
                rsvps.append(dict(row))
                seen_identifiers.add(identifier)
    except Exception:
        pass

    return rsvps

def add_rsvp(meeting_id, member_id, member_name, member_phone, participation_type="자유책"):
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return False, "존재하지 않는 모임입니다."

    max_p = meeting['max_participants'] if isinstance(meeting, dict) or hasattr(meeting, '__getitem__') else getattr(meeting, 'max_participants', 8)

    conn = get_connection()
    cursor = conn.cursor()

    if participation_type != "대기":
        cursor.execute("SELECT COUNT(*) FROM rsvps WHERE meeting_id = ? AND (participation_type IS NULL OR participation_type != '대기')", (meeting_id,))
        confirmed_count = cursor.fetchone()[0]

        if confirmed_count >= max_p and max_p < 900:
            conn.close()
            return False, "모임 정원이 마감되어 대기 신청만 가능합니다."

    try:
        cursor.execute("""
        INSERT INTO rsvps (meeting_id, member_id, member_name, member_phone, participation_type)
        VALUES (?, ?, ?, ?, ?)
        """, (meeting_id, member_id, member_name, member_phone, participation_type))
        conn.commit()
        conn.close()
        msg_type = "대기 신청" if participation_type == "대기" else "참가 신청"
        return True, f"{msg_type}이 성공적으로 완료되었습니다!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "이미 이 모임에 신청하셨습니다."

def cancel_rsvp(meeting_id, member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rsvps WHERE meeting_id = ? AND member_id = ?", (meeting_id, member_id))
    conn.commit()
    conn.close()



def get_attendances_for_meeting(meeting_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE meeting_id = ?", (meeting_id,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_member_attendance_count(email, display_name=""):
    conn = get_connection()
    cursor = conn.cursor()
    name_only = display_name.split(" - ")[0].strip() if " - " in display_name else display_name
    cursor.execute("""
    SELECT book_read, is_lounging FROM attendance 
    WHERE member_name LIKE ? OR member_name LIKE ? OR member_id IN (
        SELECT id FROM members WHERE email = ?
    )
    """, (f"%{email}%", f"%{name_only}%", email))
    rows = cursor.fetchall()
    conn.close()

    total = 0.0
    for row in rows:
        b_read = str(row[0] or '')
        r_dict = dict(row)
        l_flag = r_dict.get('is_lounging', 0)
        if l_flag == 1 or "라운징" in b_read:
            total += 0.5
        else:
            total += 1.0

    if total.is_integer():
        return int(total)
    return total

