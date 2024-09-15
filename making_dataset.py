import pandas as pd
import numpy as np
import random
from faker import Faker
import sqlite3

# Faker 인스턴스 생성
fake_ko = Faker('ko_KR')
fake_en = Faker('en_US')
fake_ar = Faker('ar_SA')

# 아랍어 문장 생성 함수
def generate_arabic_sentence():
    words = [fake_ar.word() for _ in range(10)]
    return ' '.join(words)

# 한국어 문장 생성 함수
def generate_korean_sentence():
    return ' '.join(fake_ko.words(nb=20))

def generate_random_mgrs(language):
    if language == 'Korean':
        # 한국어의 경우 기존 코드 유지
        zone = '52S'
        grid_letters = ['CG', 'DG', 'CF', 'DF', 'CE', 'DE', 'EE', 'CD']
        grid = random.choice(grid_letters)
        easting = random.randint(0, 99999)
        northing = random.randint(0, 99999)

    elif language == 'English' or 'Arabic':
        # UAE의 MGRS 그리드 영역
        zones = ['39Q', '40Q','40R']
        zone = random.choice(zones)
        if zone == '39Q':
            grid_letters = ['XG', 'YG', 'XF', 'YF']
            grid =random.choice(grid_letters)
            if grid == 'XG':
                easting = random.randint(0, 99999)
                northing = random.randint(0, 50000)
            elif grid == 'YG':
                easting = random.randint(0, 99999)
                northing = random.randint(0, 50000)
            elif grid == 'XF':
                easting = random.randint(0, 99999)
                northing = random.randint(40000, 99999)
            elif grid == 'YF':
                easting = random.randint(0, 99999)
                northing = random.randint(30000, 99999)
        elif zone == '40Q':
            grid_letters = ['BM', 'BL', 'CM', 'CL']
            grid = random.choice(grid_letters)
            if grid == 'BM':
                easting = random.randint(0, 99999)
                northing = random.randint(0, 50000)
            elif grid == 'BL':
                easting = random.randint(0, 99999)
                northing = random.randint(0, 99999)
            elif grid == 'CM':
                easting = random.randint(0, 40000)
                northing = random.randint(0, 50000)
            elif grid == 'CL':
                easting = random.randint(0, 30000)
                northing = random.randint(0, 99999)
        elif zone == '40R':
            grid_letters = ['BM', 'BN', 'CM', 'CN', 'DN', 'CP', 'DP']
            grid = random.choice(grid_letters)
            if grid == 'BM':
                easting = random.randint(0, 99999)
                northing = random.randint(60000,99999)
            elif grid == 'BN':
                easting = random.randint(40000, 99999)
                northing = random.randint(0,60000)
            elif grid == 'CM':
                easting = random.randint(0, 99999)
                northing = random.randint(60000,99999)
            elif grid == 'CN':
                easting = random.randint(0, 99999)
                northing = random.randint(0,99999)
            elif grid == 'DN':
                easting = random.randint(30000, 99999)
                northing = random.randint(60000,99999)
            elif grid == 'CP':
                easting = random.randint(30000, 99999)
                northing = random.randint(0,50000)
            elif grid == 'DP':
                easting = random.randint(0, 30000)
                northing = random.randint(0, 70000)

    mgrs = f"{zone} {grid} {easting:05d} {northing:05d}"
    return mgrs

# weapon_system 생성 함수
def generate_weapon_system():
    weapon_systems = ["KM-SAM2", "PAC-2", "PAC-3", "MSE", "L-SAM", "THAAD"]
    probabilities = [0.3, 0.3, 0.2, 0.1, 0.05, 0.05]
    return random.choices(weapon_systems, probabilities)[0]

# 데이터 생성 함수
def generate_data(language, index):
    if language == 'Korean':
        fake = fake_ko
        unit = random.choice(['지상군', '공군', '해군', '기타'])
        description = generate_korean_sentence()
    elif language == 'English':
        fake = fake_en
        unit = random.choice(['Ground Forces', 'Navy', 'Air Force', 'Others'])
        description = fake.text(max_nb_chars=100)
    else:  # Arabic
        fake = fake_ar
        unit = random.choice(['القوات البرية', 'البحرية', 'سلاح الجو', 'أخرى'])
        description = generate_arabic_sentence()
    return {
        'id': index,
        'unit': unit,
        'asset_number': random.randint(0, 5000),
        'manager': fake.name(),
        'contact': fake.phone_number(),
        'target_asset': fake.company(),
        'area': fake.city(),
        'mgrs': generate_random_mgrs(language),
        'description': description,
        '중요도': random.choice([10.0, 8.0, 6.0, 4.0, 2.0]),
        '중요도_가점_중심': random.choice([0, 0.5]),
        '중요도_가점_기능': random.choice([0, 0.5]),
        '취약성_피해민감도_방호강도': random.choice([3.0, 2.0, 1.0]),
        '취약성_피해민감도_분산배치': random.choice([3.0, 2.0, 1.0]),
        '취약성_복구가능성_복구시간': random.choice([2.0, 1.5, 1.0]),
        '취약성_복구가능성_복구능력': random.choice([2.0, 1.5, 0.5]),
        '위협_공격가능성': random.choice([5.0, 3.0, 1.0]),
        '위협_탐지가능성': random.choice([5.0, 3.0, 1.0]),
        'language': language
    }

# 데이터 생성
data = []
for lang in ['Korean', 'English', 'Arabic']:
    for i in range(500):
        data.append(generate_data(lang, i + (500 * ['Korean', 'English', 'Arabic'].index(lang))))

# 데이터프레임 생성
df = pd.DataFrame(data)

# 데이터 타입 지정
df = df.astype({
    'id': 'int64',
    'unit': 'object',
    'asset_number': 'object',
    'manager': 'object',
    'contact': 'object',
    'target_asset': 'object',
    'area': 'object',
    'mgrs': 'object',
    'description': 'object',
    '중요도': 'float64',
    '중요도_가점_중심': 'float64',
    '중요도_가점_기능': 'float64',
    '취약성_피해민감도_방호강도': 'float64',
    '취약성_피해민감도_분산배치': 'float64',
    '취약성_복구가능성_복구시간': 'float64',
    '취약성_복구가능성_복구능력': 'float64',
    '위협_공격가능성': 'float64',
    '위협_탐지가능성': 'float64',
    'language': 'object'
})

# 중복되지 않는 asset_number 생성
unique_asset_numbers = random.sample(range(5001), 1500)
df['asset_number'] = unique_asset_numbers


# defense_assets 데이터 생성 함수
def generate_defense_assets_data(language, index):
    if language == 'Korean':
        fake = fake_ko
        unit = random.choice(['지상군', '공군', '해군', '기타'])
    elif language == 'English':
        fake = fake_en
        unit = random.choice(['Ground Forces', 'Navy', 'Air Force', 'Others'])
    else:  # Arabic
        fake = fake_ar
        unit = random.choice(['القوات البرية', 'البحرية', 'سلاح الجو', 'أخرى'])

    # 330~030 방향으로 위협방위 랜덤 생성
    threat_degree = random.choice(list(range(330, 360)) + list(range(0, 31)))

    return {
        'id': index,
        'unit': unit,
        'area': fake.city(),
        'asset_name': fake.company(),
        'mgrs': generate_random_mgrs(language),
        'weapon_system': generate_weapon_system(),
        'ammo_count': random.randint(0, 100),
        'threat_degree': threat_degree,  # threat_degree 추가
        'language': language
    }

# defense_assets 데이터 생성
defense_assets_data = []

for lang in ['Korean', 'English', 'Arabic']:
    for i in range(30):
        defense_assets_data.append(generate_defense_assets_data(lang, i + (30 * ['Korean', 'English', 'Arabic'].index(lang))))

# defense_assets 데이터프레임 생성
defense_assets_df = pd.DataFrame(defense_assets_data)


# defense_assets 데이터프레임 생성 시 데이터 타입 지정
defense_assets_df = defense_assets_df.astype({
    'unit': 'object',
    'area': 'object',
    'asset_name': 'object',
    'mgrs': 'object',
    'weapon_system': 'object',
    'ammo_count': 'int',
    'threat_degree': 'int',  # threat_degree 데이터 타입 지정
    'language': 'object'
})



# 데이터베이스 연결
conn = sqlite3.connect('assets.db')
cursor = conn.cursor()

# assets 테이블 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    unit TEXT,
    asset_number INTEGER,
    manager TEXT,
    contact TEXT,
    target_asset TEXT,
    area TEXT,
    mgrs TEXT,
    description TEXT,
    중요도 FLOAT,
    중요도_가점_중심 FLOAT,
    중요도_가점_기능 FLOAT,
    취약성_피해민감도_방호강도 FLOAT,
    취약성_피해민감도_분산배치 FLOAT,
    취약성_복구가능성_복구시간 FLOAT,
    취약성_복구가능성_복구능력 FLOAT,
    위협_공격가능성 FLOAT,
    위협_탐지가능성 FLOAT,
    language VARCHAR(10)
)
''')

# defense_assets 테이블 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS defense_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit TEXT,
    area TEXT,
    asset_name TEXT,
    mgrs TEXT,
    weapon_system TEXT,
    ammo_count INTEGER,
    threat_degree INTEGER, 
    language TEXT
)
''')

# 데이터 삽입
df.to_sql('assets', conn, if_exists='replace', index=False)
defense_assets_df.to_sql('defense_assets', conn, if_exists='replace', index=False)

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("데이터가 'assets.db' 데이터베이스에 저장되었습니다.")

# 데이터 확인 (선택사항)
conn = sqlite3.connect('assets.db')
df_check_assets = pd.read_sql_query("SELECT * FROM assets LIMIT 5", conn)
df_check_defense_assets = pd.read_sql_query("SELECT * FROM defense_assets LIMIT 5", conn)
print(df_check_assets)
print(df_check_defense_assets)
conn.close()
