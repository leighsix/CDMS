import sys, os, io, mgrs
import folium, re, json
import sqlite3
import pandas as pd
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from common_map_view import CommonMapView, DefenseAssetCommonMapView
from PyQt5.QtCore import QUrl, QTemporaryFile, QSize
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QUrl, QSize, QTimer, QTemporaryFile, QDir, QEventLoop, QDateTime
from enemy_map_view import EnemyBaseMapView, EnemyWeaponMapView
from setting import MapApp
from math import radians, sin, cos, atan2, sqrt, degrees

class ViewCopWindow(QDialog):
    def __init__(self, parent):
        super(ViewCopWindow, self).__init__(parent)
        self.parent = parent
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.setWindowTitle(self.tr("공통상황도"))
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.load_dataframes()
        self.initUI()
        self.show_defense_radius = False
        self.show_threat_radius = False
        self.update_map()  # 초기 지도 로드

    def load_dataframes(self):
        try:
            conn = sqlite3.connect(self.parent.db_path)

            try:
                query = "SELECT * FROM cal_assets_priority_ko"
                self.cal_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM cal_assets_priority_en"
                self.cal_df_en = pd.read_sql_query(query, conn,)

            except sqlite3.OperationalError:
                print("assets_priority 테이블이 존재하지 않습니다.")
                self.cal_df_ko = pd.DataFrame(columns=["id", "priority", "unit", "target_asset", "area", "coordinate", "mgrs", "criticality", "vulnerability", "threat", "bonus", "total_score"])
                self.cal_df_en = pd.DataFrame(columns=["id", "priority", "unit", "target_asset", "area", "coordinate", "mgrs", "criticality", "vulnerability", "threat", "bonus", "total_score"])


            try:
                query = "SELECT * FROM dal_assets_ko"
                self.dal_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM dal_assets_en"
                self.dal_df_en = pd.read_sql_query(query, conn,)
            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.dal_df_ko = pd.DataFrame(columns=["id", "unit", "area", "asset_name", "coordinate", "mgrs", "weapon_system", "ammo_count", "threat_degree"])
                self.dal_df_en = pd.DataFrame(columns=["id", "unit", "area", "asset_name", "coordinate", "mgrs", "weapon_system", "ammo_count", "threat_degree"])

            try:
                query = "SELECT * FROM enemy_bases_ko"
                self.enemy_bases_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM enemy_bases_en"
                self.enemy_bases_df_en = pd.read_sql_query(query, conn,)
            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.enemy_bases_df_ko = pd.DataFrame(columns=["id", "base_name", "area", "coordinate", "mgrs", "weapon_system"])
                self.enemy_bases_df_en = pd.DataFrame(columns=["id", "base_name", "area", "coordinate", "mgrs", "weapon_system"])
        except sqlite3.Error as e:
            print(f"데이터베이스 연결 오류: {e}")

        finally:
            if conn:
                conn.close()

        if self.cal_df_ko.empty and self.dal_df_ko.empty and self.enemy_bases_df_ko.empty:
            print("경고: 데이터를 불러오지 못했습니다. 빈 DataFrame을 사용합니다.")

    def refresh(self):
        # 데이터프레임 다시 로드
        self.load_dataframes()

        # 필터 초기화
        self.unit_filter.setCurrentIndex(0)  # '전체'로 설정
        self.search_filter.clear()  # 검색창 초기화
        self.display_count_combo.setCurrentIndex(0)  # '전체'로 설정

        # 테이블의 모든 체크박스 해제
        self.assets_table.uncheckAllRows()
        for weapon_system, checkbox in self.defense_assets_checkboxes.items():
            if checkbox.isChecked():
                checkbox.setChecked(False)
        self.radius_checkbox.setChecked(False)

        # 테이블의 모든 체크박스 해제
        self.enemy_sites_table.uncheckAllRows()
        self.missile_type_combo.setCurrentIndex(0)  # '전체'로 설정
        self.search_enemy_filter.clear()  # 검색창 초기화
        self.threat_radius_checkbox.setChecked(False)

        # 테이블 데이터 다시 로드
        self.load_assets()
        self.load_enemy_missile_sites()

        # 지도 업데이트
        self.update_map()

    def initUI(self):
        main_layout = QHBoxLayout()

        # QSplitter 생성
        main_splitter = QSplitter(Qt.Horizontal)

        # 좌측 레이아웃 (필터 및 테이블)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 필터 추가
        self.filter_layout = QHBoxLayout()

        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군")])
        self.unit_filter.currentTextChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.unit_filter)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText(self.tr("방어대상자산 또는 지역구분 검색"))
        self.search_filter.textChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.search_filter)

        self.display_count_combo = QComboBox()
        self.display_count_combo.addItems(["30", "50", "100", "200"])
        self.display_count_combo.currentTextChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.display_count_combo)
        left_layout.addLayout(self.filter_layout)

        # 테이블
        self.assets_table = MyTableWidget()
        self.assets_table.setColumnCount(5)
        self.assets_table.setHorizontalHeaderLabels(
            ["", self.tr("우선순위"), self.tr("구성군"), self.tr("지역구분"), self.tr("방어대상자산")])

        # 행 번호 숨기기
        self.assets_table.verticalHeader().setVisible(False)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        header.resizeSection(1, 80)

        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()):
            self.assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        left_layout.addWidget(self.assets_table)

        # 페이지네이션 컨트롤 추가
        self.pagination_layout = QHBoxLayout()
        self.prev_button = QPushButton("◀")
        self.next_button = QPushButton("▶")
        self.page_label = QLabel()

        # 스타일 설정
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)

        # 레이아웃에 위젯 추가
        self.pagination_layout.addWidget(self.prev_button)
        self.pagination_layout.addWidget(self.page_label)
        self.pagination_layout.addWidget(self.next_button)

        # 레이아웃 정렬 및 간격 설정
        self.pagination_layout.setAlignment(Qt.AlignCenter)
        self.pagination_layout.setSpacing(10)

        left_layout.addLayout(self.pagination_layout)

        # 버튼 연결
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        # 초기 페이지 설정
        self.current_page = 1
        self.rows_per_page = 30  # 기본값 설정
        self.total_pages = 1  # 초기값 설정
        self.update_page_label()

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setContentsMargins(0, 20, 0, 20)
        button_layout.setAlignment(Qt.AlignCenter)  # 버튼을 중앙에 정렬

        self.return_button = QPushButton(self.tr("메인화면으로 돌아가기"), self)
        self.return_button.clicked.connect(self.parent.show_main_page)
        self.return_button.setFont(QFont("강한공군체", 15, QFont.Bold))
        self.return_button.setFixedSize(250, 50)  # 버튼 크기 고정 (너비 200, 높이 50)
        self.return_button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬
        button_layout.addWidget(self.return_button)
        left_layout.addLayout(button_layout)  # 버튼 레이아웃을 left_layout에 추가

        # 중앙 레이아웃 (지도)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        # 무기체계 체크박스 그룹
        weapon_group = QGroupBox(self.tr("무기체계"))
        weapon_layout = QHBoxLayout()
        weapon_layout.setContentsMargins(10, 5, 10, 5)  # 여백 조정
        weapon_layout.setSpacing(10)  # 체크박스 간 간격 조정
        self.defense_assets_checkboxes = {}
        defense_assets = self.get_defense_assets()
        for asset in defense_assets:
            checkbox = QCheckBox(asset)
            checkbox.stateChanged.connect(self.update_map)
            self.defense_assets_checkboxes[asset] = checkbox
            weapon_layout.addWidget(checkbox)
        weapon_group.setLayout(weapon_layout)
        weapon_group.setFixedHeight(weapon_layout.sizeHint().height() + 20)  # 높이 조정
        center_layout.addWidget(weapon_group)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        checkbox_button_layout = QHBoxLayout()

        # 방어반경 표시 체크박스
        self.radius_checkbox = QCheckBox(self.tr("방어반경 표시"), self)
        self.radius_checkbox.stateChanged.connect(self.toggle_defense_radius)
        checkbox_button_layout.addWidget(self.radius_checkbox)

        # 지도 출력 버튼
        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.setFixedSize(230, 50)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        checkbox_button_layout.addWidget(self.print_button, alignment=Qt.AlignRight)

        # 수평 레이아웃을 center_layout에 추가
        center_layout.addLayout(checkbox_button_layout)

        # 지도 뷰
        self.map_view = QWebEngineView()
        center_layout.addWidget(self.map_view)

        # 우측 레이아웃 (새로운 테이블들)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 우측 상단 테이블: 적 미사일 발사기지
        # 필터 추가
        self.enemy_filter_layout = QHBoxLayout()

        # 검색 창
        self.search_enemy_filter = QLineEdit()
        self.search_enemy_filter.setPlaceholderText(self.tr("적 기지명 또는 지역 검색"))
        self.search_enemy_filter.textChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.search_enemy_filter)

        # 미사일 타입 콤보박스
        self.missile_type_combo = QComboBox()
        self.missile_type_combo.addItems(["전체", "Scud-B", "Scud-C", "Nodong"])
        self.missile_type_combo.currentTextChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.missile_type_combo)

        # 위협반경 표시 체크박스
        self.threat_radius_checkbox = QCheckBox(self.tr("위협반경 표시"))
        self.threat_radius_checkbox.stateChanged.connect(self.toggle_threat_radius)
        self.enemy_filter_layout.addWidget(self.threat_radius_checkbox)

        right_layout.addLayout(self.enemy_filter_layout)

        self.enemy_sites_table = MyTableWidget()
        self.enemy_sites_table.setColumnCount(4)
        self.enemy_sites_table.setHorizontalHeaderLabels(["", self.tr("발사기지"), self.tr("경위도"), self.tr("보유미사일")])
        # 행 번호 숨기기
        self.enemy_sites_table.verticalHeader().setVisible(False)
        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.enemy_sites_table.horizontalHeader().setFont(font)
        header = self.enemy_sites_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.enemy_sites_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()):
            self.enemy_sites_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        right_layout.addWidget(self.enemy_sites_table)

        # 우측 중간 테이블
        self.threat_cal_table = QTableWidget()
        self.threat_cal_table.setColumnCount(4)
        self.threat_cal_table.setHorizontalHeaderLabels([self.tr("우선순위"), self.tr("방어대상자산"), self.tr("적 기지"), self.tr("적 미사일")])
        self.threat_cal_table.verticalHeader().setVisible(False)
        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.threat_cal_table.horizontalHeader().setFont(font)
        header = self.threat_cal_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 50)


        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.threat_cal_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(header.count()):
            self.threat_cal_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        right_layout.addWidget(QLabel(self.tr("위협반경 내 CAL 목록")))
        right_layout.addWidget(self.threat_cal_table)

        # 우측 하단 테이블
        self.no_defense_cal_table = QTableWidget()
        self.no_defense_cal_table.setColumnCount(4)
        self.no_defense_cal_table.setHorizontalHeaderLabels([self.tr("우선순위"), self.tr("방어대상자산"), self.tr("적 기지"), self.tr("적 미사일")])
        self.no_defense_cal_table.verticalHeader().setVisible(False)
        self.no_defense_cal_table.horizontalHeader().setFont(font)
        header = self.no_defense_cal_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 50)

        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.no_defense_cal_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(header.count()):
            self.no_defense_cal_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        right_layout.addWidget(QLabel(self.tr("방어반경 외곽 CAL 목록")))
        right_layout.addWidget(self.no_defense_cal_table)

        # 위젯들을 QSplitter에 추가
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(center_widget)
        main_splitter.addWidget(right_widget)

        # QSplitter를 메인 레이아웃에 추가
        main_layout.addWidget(main_splitter)

        self.setLayout(main_layout)

        # 초기 분할 비율 설정 (예: 2:5:3)
        main_splitter.setSizes([200, 500, 300])

        self.load_assets()
        self.load_enemy_missile_sites()

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.threat_cal_table.clearContents()
        self.threat_cal_table.setRowCount(0)
        self.no_defense_cal_table.clearContents()
        self.no_defense_cal_table.setRowCount(0)
        self.update_map()

    def toggle_threat_radius(self, state):
        self.show_threat_radius = state == Qt.Checked
        self.threat_cal_table.clearContents()
        self.threat_cal_table.setRowCount(0)
        self.no_defense_cal_table.clearContents()
        self.no_defense_cal_table.setRowCount(0)
        self.update_map()

    def load_assets(self):
        filtered_df = self.cal_df_ko if self.parent.selected_language == 'ko' else self.cal_df_en

        unit_filter_text = self.unit_filter.currentText()
        if unit_filter_text != self.tr("전체"):
            filtered_df = filtered_df[filtered_df['unit'] == unit_filter_text]

        search_filter_text = self.search_filter.text()
        if search_filter_text:
            filtered_df = filtered_df[
                (filtered_df['target_asset'].str.contains(search_filter_text, case=False)) |
                (filtered_df['area'].str.contains(search_filter_text, case=False))
                ]

        filtered_df = filtered_df.sort_values('priority')

        # 페이지네이션 설정
        self.rows_per_page = int(self.display_count_combo.currentText())
        self.total_pages = -(-len(filtered_df) // self.rows_per_page)  # 올림 나눗셈

        # 현재 페이지에 해당하는 데이터만 선택
        start_idx = (self.current_page - 1) * self.rows_per_page
        end_idx = start_idx + self.rows_per_page
        page_df = filtered_df.iloc[start_idx:end_idx]

        self.assets_table.uncheckAllRows()
        self.assets_table.setRowCount(len(page_df))
        self.update_map()
        for row, (_, asset) in enumerate(page_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(asset[['priority', 'unit', 'area', 'target_asset']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.assets_table.setItem(row, col, item)

        self.update_pagination()

    def load_enemy_missile_sites(self):
        filtered_df = self.enemy_bases_df_ko if self.parent.selected_language == 'ko' else self.enemy_bases_df_en

        search_filter_text = self.search_enemy_filter.text()
        if search_filter_text:
            filtered_df = filtered_df[
                (filtered_df['base_name'].str.contains(search_filter_text, case=False)) |
                (filtered_df['area'].str.contains(search_filter_text, case=False)) |
                (filtered_df['weapon_system'].str.contains(search_filter_text, case=False))
                ]

        missile_filter_text = self.missile_type_combo.currentText()
        if missile_filter_text != self.tr("전체"):
            filtered_df = filtered_df[
                filtered_df['weapon_system'].apply(lambda x: missile_filter_text in x.split(', '))]

        self.enemy_sites_table.uncheckAllRows()
        self.enemy_sites_table.setRowCount(len(filtered_df))
        self.update_map()
        for row, (_, base) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.enemy_sites_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(base[['base_name', 'coordinate', 'weapon_system']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.enemy_sites_table.setItem(row, col, item)

    def load_threat_cal(self):
        self.threat_cal_table.clearContents()
        self.threat_cal_table.setRowCount(0)
        selected_assets = self.get_selected_assets()
        selected_enemy_weapons = self.get_selected_enemy_weapons()
        m_conv = mgrs.MGRS()

        threatened_assets = {}

        for enemy_base, enemy_mgrs, enemy_weapon in selected_enemy_weapons:
            zone, square, easting, northing = self.parse_mgrs(enemy_mgrs)
            mgrs_full_str = f'{zone}{square}{easting}{northing}'
            enemy_lat, enemy_lon = m_conv.toLatLon(mgrs_full_str)
            enemy_radius = self.get_weapon_radius(enemy_weapon)

            for asset_name, asset_mgrs, priority in selected_assets:
                zone, square, easting, northing = self.parse_mgrs(asset_mgrs)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                asset_lat, asset_lon = m_conv.toLatLon(mgrs_full_str)
                distance = self.calculate_distance(enemy_lat, enemy_lon, asset_lat, asset_lon)

                if distance <= enemy_radius:
                    if asset_name not in threatened_assets:
                        threatened_assets[asset_name] = {"priority": priority, "threats": []}
                    threatened_assets[asset_name]["threats"].append((enemy_base, enemy_weapon))

        for row, (asset_name, asset_info) in enumerate(threatened_assets.items()):
            self.threat_cal_table.insertRow(row)

            priority_item = QTableWidgetItem(str(asset_info["priority"]))
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.threat_cal_table.setItem(row, 0, priority_item)  # 우선순위

            asset_name_item = QTableWidgetItem(asset_name)
            asset_name_item.setTextAlignment(Qt.AlignCenter)
            self.threat_cal_table.setItem(row, 1, asset_name_item)  # 자산 이름

            enemy_bases = ", ".join(set(threat[0] for threat in asset_info["threats"]))
            enemy_bases_item = QTableWidgetItem(enemy_bases)
            enemy_bases_item.setTextAlignment(Qt.AlignCenter)
            self.threat_cal_table.setItem(row, 2, enemy_bases_item)  # 적 기지

            enemy_weapons = ", ".join(set(threat[1] for threat in asset_info["threats"]))
            enemy_weapons_item = QTableWidgetItem(enemy_weapons)
            enemy_weapons_item.setTextAlignment(Qt.AlignCenter)
            self.threat_cal_table.setItem(row, 3, enemy_weapons_item)  # 적 무기

    def load_no_defense_cal(self):
        self.no_defense_cal_table.clearContents()
        self.no_defense_cal_table.setRowCount(0)

        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_defense_assets()

        m_conv = mgrs.MGRS()

        # weapon_systems.json 파일 로드
        with open('weapon_systems.json', 'r', encoding='utf-8') as f:
            weapon_systems = json.load(f)

        undefended_assets = []

        for asset_name, asset_mgrs, priority in selected_assets:
            zone, square, easting, northing = self.parse_mgrs(asset_mgrs)
            mgrs_full_str = f'{zone}{square}{easting}{northing}'
            asset_lat, asset_lon = m_conv.toLatLon(mgrs_full_str)
            is_defended = False

            for defense_name, defense_mgrs, defense_weapon, threat_degree in selected_defense_assets:
                zone, square, easting, northing = self.parse_mgrs(defense_mgrs)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                defense_lat, defense_lon = m_conv.toLatLon(mgrs_full_str)

                if defense_weapon not in weapon_systems:
                    print(f"경고: {defense_weapon}에 대한 정보가 없습니다.")
                    continue

                defense_radius = int(weapon_systems[defense_weapon]['radius'])
                defense_angle = int(weapon_systems[defense_weapon]['angle'])

                distance = self.calculate_distance(asset_lat, asset_lon, defense_lat, defense_lon)

                if distance <= defense_radius:
                    if defense_angle == 360:
                        is_defended = True
                        break
                    else:
                        # 방위각 계산
                        bearing = self.calculate_bearing(defense_lat, defense_lon, asset_lat, asset_lon)

                        # 위협 방위 범위 계산
                        threat_min = (float(threat_degree) - defense_angle / 2) % 360
                        threat_max = (float(threat_degree) + defense_angle / 2) % 360

                        # 위협 방위 범위 내에 있는지 확인
                        if threat_min < threat_max:
                            if threat_min <= bearing <= threat_max:
                                is_defended = True
                                break
                        else:  # 범위가 0도를 걸치는 경우
                            if bearing >= threat_min or bearing <= threat_max:
                                is_defended = True
                                break

            if not is_defended:
                undefended_assets.append((asset_name, asset_mgrs, priority))

        # 테이블에 데이터 추가
        for row, asset in enumerate(undefended_assets):
            self.no_defense_cal_table.insertRow(row)

            for col, value in enumerate([asset[2], asset[0]]):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.no_defense_cal_table.setItem(row, col, item)

            for threat_row in range(self.threat_cal_table.rowCount()):
                threat_priority = self.threat_cal_table.item(threat_row, 0).text()
                threat_asset_name = self.threat_cal_table.item(threat_row, 1).text()

                if threat_priority == str(asset[2]) and threat_asset_name == asset[0]:
                    for col in range(self.no_defense_cal_table.columnCount()):
                        item = self.no_defense_cal_table.item(row, col)
                        if item:
                            item.setBackground(QColor(255, 200, 200))

                    enemy_bases = self.threat_cal_table.item(threat_row, 2).text()
                    enemy_weapons = self.threat_cal_table.item(threat_row, 3).text()

                    for col, value in enumerate([enemy_bases, enemy_weapons], start=2):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(Qt.AlignCenter)
                        self.no_defense_cal_table.setItem(row, col, item)
                        item.setBackground(QColor(255, 200, 200))

                    break

    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = sin(dlon) * cos(lat2)
        x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        initial_bearing = atan2(y, x)
        initial_bearing = degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        return compass_bearing

    def parse_mgrs(self, mgrs_string):
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        # 두 지점 간의 거리를 계산하는 함수 (Haversine 공식 사용)

        R = 6371000  # 지구의 반경 (미터)

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @staticmethod
    def get_weapon_radius(weapon):
        # JSON 파일 경로
        json_file_path = 'missile_info.json'

        # JSON 파일이 존재하는지 확인
        if not os.path.exists(json_file_path):
            print(f"오류: {json_file_path} 파일을 찾을 수 없습니다.")
            return 0

        try:
            # JSON 파일 읽기
            with open(json_file_path, 'r', encoding='utf-8') as file:
                weapon_data = json.load(file)

            # 무기 정보 가져오기
            weapon_info = weapon_data.get(weapon, {})

            # 반경 정보 반환 (정수로 변환)
            return int(weapon_info.get('radius', 0))

        except json.JSONDecodeError:
            print(f"오류: {json_file_path} 파일의 JSON 형식이 올바르지 않습니다.")
            return 0
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return 0

    @staticmethod
    def get_defense_radius(weapon):
        # JSON 파일에서 무기체계 정보 로드
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_systems = json.load(file)

        # 방어 무기 종류에 따른 방어 반경 반환
        if weapon in weapon_systems:
            return int(weapon_systems[weapon]['radius'])
        else:
            return 0

    def update_pagination(self):
        self.page_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def update_page_label(self):
        self.page_label.setText(f"{self.current_page} / {self.total_pages}")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_label()
            self.load_assets()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_label()
            self.load_assets()

    def get_defense_assets(self):
        return self.dal_df_en['weapon_system'].unique().tolist()

    def update_map(self):
        # 새로운 지도 객체를 생성하되, 현재의 중심 위치와 줌 레벨을 사용합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_defense_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        selected_enemy_weapons = self.get_selected_enemy_weapons()
        self.threat_cal_table.clearContents()
        self.threat_cal_table.setRowCount(0)
        self.no_defense_cal_table.clearContents()
        self.no_defense_cal_table.setRowCount(0)
        if selected_assets:
            CommonMapView(selected_assets, self.map)
        if selected_defense_assets:
            DefenseAssetCommonMapView(selected_defense_assets, self.show_defense_radius, self.map)
        if selected_enemy_bases:
            EnemyBaseMapView(selected_enemy_bases, self.map)
        if selected_enemy_weapons:
            EnemyWeaponMapView(selected_enemy_weapons, self.show_threat_radius, self.map)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)
        if selected_assets and selected_enemy_weapons and self.show_threat_radius:
            self.load_threat_cal()
        if selected_assets and selected_defense_assets and self.show_defense_radius:
            self.load_no_defense_cal()

    def get_selected_assets(self):
        selected_assets = []
        asset_info_ko = pd.DataFrame()
        asset_info_en = pd.DataFrame()
        for row in range(self.assets_table.rowCount()):
            checkbox_widget = self.assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                priority = int(self.assets_table.item(row, 1).text())
                unit = self.assets_table.item(row, 2).text()
                area = self.assets_table.item(row, 3).text()
                asset_name = self.assets_table.item(row, 4).text()
                if self.parent.selected_language == 'ko':
                    asset_info_ko = self.cal_df_ko[
                        (self.cal_df_ko['target_asset'] == asset_name) &
                        (self.cal_df_ko['area'] == area) &
                        (self.cal_df_ko['unit'] == unit)
                        ]
                else:
                    asset_info_en = self.cal_df_en[
                        (self.cal_df_en['target_asset'] == asset_name) &
                        (self.cal_df_en['area'] == area) &
                        (self.cal_df_en['unit'] == unit)
                        ]
                mgrs_coord = asset_info_ko.iloc[0]['mgrs'] if self.parent.selected_language == 'ko' else asset_info_en.iloc[0]['mgrs']
                selected_assets.append((asset_name, mgrs_coord, priority))
        return selected_assets

    def get_selected_defense_assets(self):
        selected_defense_assets = []
        for weapon_system, checkbox in self.defense_assets_checkboxes.items():
            if checkbox.isChecked():
                assets = self.dal_df_ko[self.dal_df_ko['weapon_system'] == weapon_system]
                for _, asset in assets.iterrows():
                    selected_defense_assets.append((asset['asset_name'], asset['mgrs'], weapon_system, asset['threat_degree']))
        return selected_defense_assets

    def get_selected_enemy_bases(self):
        selected_enemy_bases = []
        bases_info_ko = pd.DataFrame()
        bases_info_en = pd.DataFrame()
        for row in range(self.enemy_sites_table.rowCount()):
            checkbox_widget = self.enemy_sites_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_sites_table.item(row, 1).text()
                coordinate = self.enemy_sites_table.item(row, 2).text()
                weapon_system = self.enemy_sites_table.item(row, 3).text()
                if self.parent.selected_language == 'ko':
                    bases_info_ko = self.enemy_bases_df_ko[
                        (self.enemy_bases_df_ko['base_name'] == base_name) &
                        (self.enemy_bases_df_ko['coordinate'] == coordinate) &
                        (self.enemy_bases_df_ko['weapon_system'] == weapon_system)
                        ]
                else:
                    bases_info_en = self.enemy_bases_df_en[
                        (self.enemy_bases_df_en['base_name'] == base_name) &
                        (self.enemy_bases_df_en['coordinate'] == coordinate) &
                        (self.enemy_bases_df_en['weapon_system'] == weapon_system)
                        ]
                mgrs_coord = bases_info_ko.iloc[0]['mgrs'] if self.parent.selected_language == 'ko' else bases_info_en.iloc[0]['mgrs']
                selected_enemy_bases.append((base_name, mgrs_coord, weapon_system))
        return selected_enemy_bases

    def get_selected_enemy_weapons(self):
        selected_enemy_weapons = []
        weapon_info_ko = pd.DataFrame()
        weapon_info_en = pd.DataFrame()
        for row in range(self.enemy_sites_table.rowCount()):
            checkbox_widget = self.enemy_sites_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_sites_table.item(row, 1).text()
                coordinate = self.enemy_sites_table.item(row, 2).text()
                weapon_system = self.enemy_sites_table.item(row, 3).text()
                if self.parent.selected_language == 'ko':
                    weapon_info_ko = self.enemy_bases_df_ko[
                        (self.enemy_bases_df_ko['base_name'] == base_name) &
                        (self.enemy_bases_df_ko['coordinate'] == coordinate) &
                        (self.enemy_bases_df_ko['weapon_system'] == weapon_system)
                        ]
                else:
                    weapon_info_en = self.enemy_bases_df_en[
                        (self.enemy_bases_df_en['base_name'] == base_name) &
                        (self.enemy_bases_df_en['coordinate'] == coordinate) &
                        (self.enemy_bases_df_en['weapon_system'] == weapon_system)
                        ]
                mgrs_coord = weapon_info_ko.iloc[0]['mgrs'] if self.parent.selected_language == 'ko' else weapon_info_en.iloc[0]['mgrs']
                weapon_systems_list = weapon_system.split(", ")
                for weapon in weapon_systems_list:
                    if self.missile_type_combo.currentText() == self.tr('전체'):
                        selected_enemy_weapons.append((base_name, mgrs_coord, weapon))
                    else:
                        if weapon == self.missile_type_combo.currentText():
                            selected_enemy_weapons.append((base_name, mgrs_coord, weapon))
        return selected_enemy_weapons

    def print_map(self):
        self.printer = QPrinter(QPrinter.HighResolution)
        self.printer.setPageOrientation(QPageLayout.Landscape)
        self.printer.setPageSize(QPageSize(QPageSize.A4))
        self.printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

        self.preview = QPrintPreviewDialog(self.printer, self)
        self.preview.setMinimumSize(1000, 800)
        self.preview.paintRequested.connect(self.handle_print_requested)
        self.preview.finished.connect(self.print_finished)
        self.preview.exec_()

    def handle_print_requested(self, printer):
        try:
            painter = QPainter()
            painter.begin(printer)

            page_rect = printer.pageRect(QPrinter.DevicePixel)

            title_font = QFont("Arial", 16, QFont.Bold)
            painter.setFont(title_font)
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")

            full_map = self.map_view.grab()

            combined_image = full_map.toImage()

            content_rect = page_rect.adjusted(0, title_rect.height() + 10, 0, -30)
            scaled_image = combined_image.scaled(QSize(int(content_rect.width()), int(content_rect.height())),
                                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)

            x = int(content_rect.left() + (content_rect.width() - scaled_image.width()) / 2)
            y = int(content_rect.top() + (content_rect.height() - scaled_image.height()) / 2)
            painter.drawImage(x, y, scaled_image)

            info_font = QFont("Arial", 8)
            painter.setFont(info_font)
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            info_text = self.tr(f"인쇄 일시: {current_time}")
            painter.drawText(page_rect.adjusted(10, -20, -10, -10), Qt.AlignBottom | Qt.AlignRight, info_text)

            painter.end()
        except Exception as e:
            print(self.tr(f"인쇄 중 오류 발생: {str(e)}"))
            self.print_success = False
        else:
            self.print_success = True

    def print_finished(self, result):
        if self.print_success:
            QMessageBox.information(self, self.tr("인쇄 완료"), self.tr("지도가 성공적으로 출력되었습니다."))
        else:
            QMessageBox.warning(self, self.tr("인쇄 실패"), self.tr("지도 출력 중 오류가 발생했습니다."))

class CheckBoxHeader(QHeaderView):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.isOn = False

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(rect.x() + rect.width() // 2 - 12, rect.y() + rect.height() // 2 - 12, 24, 24)
            option.state = QStyle.State_Enabled | QStyle.State_Active
            if self.isOn:
                option.state |= QStyle.State_On
            else:
                option.state |= QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = self.logicalIndexAt(event.pos().x())
            if x == 0:
                self.isOn = not self.isOn
                self.updateSection(0)
                self.parent().on_header_clicked(self.isOn)
        super().mousePressEvent(event)

class CenteredCheckBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("QCheckBox::indicator { width: 24px; height: 24px; }")
        layout.addWidget(self.checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def isChecked(self):
        return self.checkbox.isChecked()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

class MyTableWidget(QTableWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.header_checked = False
        self.setHorizontalHeader(CheckBoxHeader(Qt.Horizontal, self))


    def on_header_clicked(self, checked):
        self.header_checked = checked
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.checkbox.setChecked(checked)

    def uncheckAllRows(self):
        self.header_checked = False
        # 헤더 체크박스도 해제
        self.horizontalHeader().isOn = False
        self.horizontalHeader().updateSection(0)

class MainWindow(QtWidgets.QMainWindow, QObject):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CAL/DAL Management System")
        self.setWindowIcon(QIcon("logo.png"))
        self.setMinimumSize(800, 600)
        self.map_app = MapApp()
        self.selected_language = "en"  # 기본 언어 설정
        self.central_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(self.central_widget)
        self.db_path = 'assets_management.db'
        self.view_cop_window = ViewCopWindow(self)
        self.central_widget.addWidget(self.view_cop_window)


    def show_main_page(self):
        self.central_widget.setCurrentIndex(0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())