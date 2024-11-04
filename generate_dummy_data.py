import random, os
import mgrs
import sqlite3

# 한국 주요 도시와 영어 이름 매칭
cities = {
    "서울": "Seoul", "부산": "Busan", "인천": "Incheon", "대구": "Daegu", "대전": "Daejeon",
    "광주": "Gwangju", "울산": "Ulsan", "세종": "Sejong", "수원": "Suwon", "창원": "Changwon"}

# 군 단위 한영 매칭
units = {"지상군": "Ground Force", "해군": "Navy", "공군": "Air Force", "기타": "Other"}

engagement_effectiveness = {None : None, "1단계: 원격발사대":"Level 1: Remote Launcher", "2단계: 단층방어" : "Level 2: Single-Layered Defense",
                            "3단계: 중첩방어" : "Level 3: Overlapping layered Defense", "4단계: 다층방어": "Level 4: Multi-layered Defense"}

bmd_priority = {None:None, "지휘통제시설":"C2", "비행단" : "Fighter Group",
                "군수기지" : "Logistics Base", "해군기지": "Naval Base",
                "주요레이다" : "Radar Site"}

weapons = ["KM-SAM2", "PAC-2", "PAC-3", "MSE", "L-SAM", "THAAD"]


def convert_to_mgrs(lat, lon):
    m = mgrs.MGRS()
    return m.toMGRS(lat, lon)

def making_weapon_systems():
    # 5:1:1:1:1:1 비율로 무기 선택
    weights = [5, 1, 1, 1, 1, 1]  # KM-SAM2가 5배 높은 확률
    selected_weapons = random.choices(weapons, weights=weights, k=random.randint(1, 2))

    weapon_counts = []
    total_count = 0

    for weapon in selected_weapons:
        count = random.randint(1, 10)
        weapon_counts.append(f"{weapon}({count})")
        total_count += count

    weapon = ", ".join(weapon_counts)
    ammo_count = total_count

    return weapon, ammo_count

def random_angle():
    angle = random.randint(300, 420)
    if angle > 360:
        angle -= 360
    return angle

def generate_dummy_weapon(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS weapon_assets_ko (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree INTEGER,
                dal_select BOOLEAN
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS weapon_assets_en (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree INTEGER,
                dal_select BOOLEAN
            )
    ''')
    try:
        for i in range(5):  # 40개의 더미 데이터 생성
            unit_ko = random.choice(list(units.keys()))
            unit_en = units[unit_ko]
            area_ko = random.choice(list(cities.keys()))
            area_en = cities[area_ko]
            weapon_asset_num = random.randint(1, 100)
            weapon_asset_ko = f"방어포대{weapon_asset_num}"
            weapon_asset_en = f"Defense Missile{weapon_asset_num}"

            # 한국 내 좌표 생성
            lat = random.uniform(34.4, 38.2)
            lon = random.uniform(126.0, 129.8)
            coordinate = f"N{lat:.5f},E{lon:.5f}"

            # MGRS 변환
            m = mgrs.MGRS()
            mgrs_coord = m.toMGRS(lat, lon)
            weights = [5, 1, 1, 1, 1, 1]  # KM-SAM2가 5배 높은 확률
            weapon = random.choices(weapons, weights=weights)[0]
            ammo_count = random.randint(1, 10)  # 각 무기 시스템의 개수 (1~5 사이)
            threat_degree = random_angle()
            dal_select = 0

            # 한국어 데이터 삽입
            cursor.execute('''
                   INSERT INTO weapon_assets_ko (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, 
                   threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_ko, area_ko, weapon_asset_ko, coordinate, mgrs_coord, weapon, ammo_count, threat_degree, dal_select))

            # 영어 데이터 삽입
            cursor.execute('''
                   INSERT INTO weapon_assets_en (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, 
                   threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_en, area_en, weapon_asset_en, coordinate, mgrs_coord, weapon, ammo_count, threat_degree, dal_select))
        conn.commit()
        print("40개의 더미 데이터가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"더미 데이터 생성 중 오류 발생: {str(e)}")
    finally:
        conn.close()

def generate_dummy_cal(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 기존 테이블 삭제 및 새로 생성
    cursor.execute('DROP TABLE IF EXISTS cal_assets_ko')
    cursor.execute('DROP TABLE IF EXISTS cal_assets_en')

    cursor.execute('''
        CREATE TABLE cal_assets_ko (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit TEXT,
            asset_number TEXT,
            manager TEXT,
            contact TEXT,
            target_asset TEXT,
            area TEXT,
            coordinate TEXT,
            mgrs TEXT,
            description TEXT,
            dal_select INTEGER,
            weapon_system TEXT,
            ammo_count INTEGER,
            threat_degree INTEGER,
            engagement_effectiveness TEXT,
            bmd_priority TEXT,
            criticality REAL,
            criticality_bonus_center REAL,
            criticality_bonus_function REAL,
            vulnerability_damage_protection REAL,
            vulnerability_damage_dispersion REAL,
            vulnerability_recovery_time REAL,
            vulnerability_recovery_ability REAL,
            threat_attack REAL,
            threat_detection REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE cal_assets_en (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit TEXT,
            asset_number TEXT,
            manager TEXT,
            contact TEXT,
            target_asset TEXT,
            area TEXT,
            coordinate TEXT,
            mgrs TEXT,
            description TEXT,
            dal_select INTEGER,
            weapon_system TEXT,
            ammo_count INTEGER,
            threat_degree INTEGER,
            engagement_effectiveness TEXT,
            bmd_priority TEXT,
            criticality REAL,
            criticality_bonus_center REAL,
            criticality_bonus_function REAL,
            vulnerability_damage_protection REAL,
            vulnerability_damage_dispersion REAL,
            vulnerability_recovery_time REAL,
            vulnerability_recovery_ability REAL,
            threat_attack REAL,
            threat_detection REAL
        )
    ''')

    try:
        for i in range(40):  # 40개의 더미 데이터 생성
            id = i+1
            unit_ko = random.choice(list(units.keys()))
            unit_en = units[unit_ko]
            asset_number = f"A{random.randint(1000, 9999)}"
            manager = f"관리자{random.randint(1, 100)}"
            contact = f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
            target_asset_num = random.randint(1, 100)
            target_asset_ko = f"자산{target_asset_num}"
            target_asset_en = f"Asset{target_asset_num}"
            area_ko = random.choice(list(cities.keys()))
            area_en = cities[area_ko]

            # 한국 내 좌표 생성
            lat = random.uniform(33.5, 38.0)
            lon = random.uniform(126.5, 129.5)
            coordinate = f"N{lat:.5f},E{lon:.5f}"

            # MGRS 변환
            m = mgrs.MGRS()
            mgrs_coord = m.toMGRS(lat, lon)

            description_ko = f"더미 자산 설명 {random.randint(1, 1000)}"
            description_en = f"asset explanation {random.randint(1, 1000)}"

            dal_select = random.choice([0, 1])
            if dal_select == 1:
                weapon = making_weapon_systems()[0]
                ammo_count = making_weapon_systems()[1]
                threat_degree = random_angle()
            else:
                weapon = None
                ammo_count = 0
                threat_degree = None
            engagement_effectiveness_ko = random.choice(list(engagement_effectiveness.keys()))
            engagement_effectiveness_en = engagement_effectiveness[engagement_effectiveness_ko]
            bmd_priority_ko = random.choice(list(bmd_priority.keys()))
            bmd_priority_en = bmd_priority[bmd_priority_ko]
            criticality = random.choice([2.0, 4.0, 6.0, 8.0, 10.0])
            criticality_bonus_center = random.choice([0, 0.5])
            criticality_bonus_function = random.choice([0, 0.5])
            vulnerability_damage_protection = random.choice([1.0, 2.0, 3.0])
            vulnerability_damage_dispersion = random.choice([1.0, 2.0, 3.0])
            vulnerability_recovery_time = random.choice([0.5, 1.0, 1.5, 2.0])
            vulnerability_recovery_ability = random.choice([0.5, 1.5, 2.0])
            threat_attack = random.choice([1.0, 3.0, 5.0])
            threat_detection = random.choice([1.0, 3.0, 5.0])

            # 한국어 데이터 삽입
            cursor.execute('''
                   INSERT INTO cal_assets_ko(
                        unit, asset_number, manager, contact, target_asset,
                        area, coordinate, mgrs, description,
                        dal_select, weapon_system, ammo_count, threat_degree, engagement_effectiveness, bmd_priority,
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_ko, asset_number, manager, contact, target_asset_ko, area_ko, coordinate, mgrs_coord, description_ko,
            dal_select, weapon, ammo_count, threat_degree, engagement_effectiveness_ko, bmd_priority_ko,
            criticality, criticality_bonus_center, criticality_bonus_function,
            vulnerability_damage_protection, vulnerability_damage_dispersion,
            vulnerability_recovery_time, vulnerability_recovery_ability,
            threat_attack, threat_detection))

            # 영어 데이터 삽입
            cursor.execute('''
                    INSERT INTO cal_assets_en(
                        unit, asset_number, manager, contact, target_asset,
                        area, coordinate, mgrs, description,
                        dal_select, weapon_system, ammo_count, threat_degree, engagement_effectiveness, bmd_priority,
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_en, asset_number, manager, contact, target_asset_en, area_en, coordinate, mgrs_coord, description_en,
            dal_select, weapon, ammo_count, threat_degree, engagement_effectiveness_en, bmd_priority_en,
            criticality, criticality_bonus_center, criticality_bonus_function,
            vulnerability_damage_protection, vulnerability_damage_dispersion,
            vulnerability_recovery_time, vulnerability_recovery_ability,
            threat_attack, threat_detection))

        conn.commit()
        print("40개의 더미 데이터가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"더미 데이터 생성 중 오류 발생: {str(e)}")
    finally:
        conn.close()

def generate_dummy_weapon_from_cal(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 기존 테이블 삭제 및 새로 생성
        cursor.execute('DROP TABLE IF EXISTS weapon_assets_ko')
        cursor.execute('DROP TABLE IF EXISTS weapon_assets_en')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weapon_assets_ko (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree INTEGER,
                dal_select BOOLEAN
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weapon_assets_en (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree INTEGER,
                dal_select BOOLEAN
            )
        ''')
        # cal_assets_ko 테이블에서 dal_select가 1인 데이터 가져오기
        cursor.execute("SELECT * FROM cal_assets_ko WHERE dal_select = 1")
        cal_assets = cursor.fetchall()

        for asset in cal_assets:
            unit = asset[1]
            area = asset[6]
            asset_name = asset[5]
            coordinate = asset[7]
            mgrs = asset[8]
            weapon_systems = asset[11]  # 여러 무기 시스템을 포함하는 문자열
            threat_degree = asset[13]
            dal_select = asset[10]

            # 무기 시스템 분리
            weapon_list = weapon_systems.split(',')
            for weapon_item in weapon_list:
                weapon_system, count = weapon_item.strip().split('(')
                ammo_count = int(count[:-1])  # 괄호 제거 및 정수로 변환

                # 한국어 데이터 삽입
                cursor.execute('''
                    INSERT INTO weapon_assets_ko (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, 
                    threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select))

                # 영어 데이터 가져오기
                cursor.execute("SELECT * FROM cal_assets_en WHERE id = ?", (asset[0],))
                en_asset = cursor.fetchone()

                # 영어 데이터 삽입
                cursor.execute('''
                    INSERT INTO weapon_assets_en (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, 
                    threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (en_asset[1], en_asset[6], en_asset[5], coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select))

        conn.commit()
        print("무기 자산 데이터가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"무기 자산 데이터 생성 중 오류 발생: {str(e)}")
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = "assets_management.db"  # 데이터베이스 파일 경로를 지정하세요
    generate_dummy_cal(db_path)
    generate_dummy_weapon_from_cal(db_path)
    generate_dummy_weapon(db_path)

