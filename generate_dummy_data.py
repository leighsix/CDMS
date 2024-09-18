import random
import mgrs
import sqlite3

# 한국 주요 도시와 영어 이름 매칭
cities = {
    "서울": "Seoul", "부산": "Busan", "인천": "Incheon", "대구": "Daegu", "대전": "Daejeon",
    "광주": "Gwangju", "울산": "Ulsan", "세종": "Sejong", "수원": "Suwon", "창원": "Changwon"}

# 군 단위 한영 매칭
units = {
    "지상군": "Ground Forces", "해군": "Navy", "공군": "Air Force", "기타": "Other"}

def convert_to_mgrs(lat, lon):
    m = mgrs.MGRS()
    return m.toMGRS(lat, lon)

def generate_dummy_cal(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        for _ in range(200):  # 10개의 더미 데이터 생성
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
            lat = random.uniform(33.0, 38.0)
            lon = random.uniform(126.0, 129.5)
            coordinate = f"N{lat:.5f},E{lon:.5f}"

            # MGRS 변환
            m = mgrs.MGRS()
            mgrs_coord = m.toMGRS(lat, lon)

            description = f"더미 자산 설명 {random.randint(1, 1000)}"

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
                INSERT INTO cal_assets_ko (unit, asset_number, manager, contact, target_asset, area, coordinate, mgrs, description,
                criticality, criticality_bonus_center, criticality_bonus_function, 
                vulnerability_damage_protection, vulnerability_damage_dispersion,
                vulnerability_recovery_time, vulnerability_recovery_ability, 
                threat_attack, threat_detection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_ko, asset_number, manager, contact, target_asset_ko, area_ko, coordinate, mgrs_coord, description,
            criticality, criticality_bonus_center, criticality_bonus_function,
            vulnerability_damage_protection, vulnerability_damage_dispersion,
            vulnerability_recovery_time, vulnerability_recovery_ability,
            threat_attack, threat_detection))

            # 영어 데이터 삽입
            cursor.execute('''
                INSERT INTO cal_assets_en (unit, asset_number, manager, contact, target_asset, area, coordinate, mgrs, description,
                criticality, criticality_bonus_center, criticality_bonus_function, 
                vulnerability_damage_protection, vulnerability_damage_dispersion,
                vulnerability_recovery_time, vulnerability_recovery_ability, 
                threat_attack, threat_detection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            unit_en, asset_number, manager, contact, target_asset_en, area_en, coordinate, mgrs_coord, description,
            criticality, criticality_bonus_center, criticality_bonus_function,
            vulnerability_damage_protection, vulnerability_damage_dispersion,
            vulnerability_recovery_time, vulnerability_recovery_ability,
            threat_attack, threat_detection))

        conn.commit()
        print("10개의 더미 데이터가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"더미 데이터 생성 중 오류 발생: {str(e)}")
    finally:
        conn.close()


def generate_dummy_dal(db_path, num_records=100):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        dummy_data = []
        for i in range(1, num_records + 1):
            record = {"구성군": random.choice(list(units.keys())), "지역구분": random.choice(list(cities.keys())),
                      "방어자산명": f"방어자산{i}", "위도": random.uniform(33.0, 38.0), "경도": random.uniform(126.0, 129.5),
                      "무기체계": random.choice(["KM-SAM2", "PAC-2", "PAC-3", "MSE", "L-SAM", "THAAD"]),
                      "보유탄수": random.randint(10, 100), "위협방위": f"{random.randint(0, 359):03d}"}

            record["구성군_영문"] = units[record["구성군"]]
            record["지역구분_영문"] = cities[record["지역구분"]]
            record["방어자산명_영문"] = f"Defense Asset {i}"
            record["군사좌표(MGRS)"] = convert_to_mgrs(record["위도"], record["경도"])
            dummy_data.append(record)
        # 테이블이 없으면 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dal_assets_ko (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dal_assets_en (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                area TEXT,
                asset_name TEXT,
                coordinate TEXT,
                mgrs TEXT,
                weapon_system TEXT,
                ammo_count INTEGER,
                threat_degree TEXT
            )
        ''')

        for record in dummy_data:
            cursor.execute('''
                INSERT INTO dal_assets_ko (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record["구성군"], record["지역구분"], record["방어자산명"], f"{record['위도']},{record['경도']}",
                record["군사좌표(MGRS)"], record["무기체계"], record["보유탄수"], record["위협방위"]
            ))

            cursor.execute('''
                INSERT INTO dal_assets_en (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record["구성군_영문"], record["지역구분_영문"], record["방어자산명_영문"], f"{record['위도']},{record['경도']}",
                record["군사좌표(MGRS)"], record["무기체계"], record["보유탄수"], record["위협방위"]
            ))

        conn.commit()
        print("더미 데이터가 성공적으로 데이터베이스에 저장되었습니다.")
    except Exception as e:
        print(f"더미 데이터 저장 중 오류 발생: {str(e)}")
    finally:
        conn.close()




if __name__ == "__main__":
    db_path = "assets_management.db"  # 데이터베이스 파일 경로를 지정하세요
    generate_dummy_cal(db_path)
    generate_dummy_dal(db_path, 30)