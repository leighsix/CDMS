import sys
import sqlite3
import csv, json, re
import random
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QHBoxLayout, QSplitter, QComboBox, QLineEdit, QTableWidget, QPushButton, QLabel,
                             QGroupBox, QCheckBox, QHeaderView, QDialog, QTableWidgetItem)
import matplotlib.pyplot as plt
from simulation_map_view import SimulationCalMapView, SimulationWeaponMapView, SimulationEnemyBaseMapView, SimulationEnemyWeaponMapView
import io
import pandas as pd
from scipy.optimize import linprog
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtCore import QUrl, QSize, QTimer, QTemporaryFile, QDir, QEventLoop, QDateTime
from setting import MapApp
import numpy as np
import math
from geopy import distance
from geopy.point import Point
from simplification.cutil import simplify_coords
from missile_trajectory_calculator import MissileTrajectoryCalculator
from particle_swarm_optimization import ParticleSwarmOptimization, MissileDefenseOptimizer


# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'

class MissileDefenseApp(QDialog):
    def __init__(self, parent=None):
        super(MissileDefenseApp, self).__init__(parent)
        self.trajectories = []
        self.engagement_zones = {}
        self.optimized_locations = []
        self.parent = parent
        self.conn = sqlite3.connect(self.parent.db_path)
        self.cursor = self.conn.cursor()
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.setWindowTitle(self.tr("미사일 방어 시뮬레이션"))
        self.setMinimumSize(1200, 800)
        self.load_dataframes()
        self.trajectory_calculator = MissileTrajectoryCalculator()
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
                self.cal_df_ko = pd.DataFrame(columns=["id", "priority", "unit", "asset_number", "manager", "contact",
                                                       "target_asset", "area", "coordinate", "mgrs", "description",
                                                       "dal_select", "weapon_system", "ammo_count", "threat_degree",
                                                       "engagement_effectiveness", "bmd_priority", "criticality", "vulnerability",
                                                       "threat", "total_score"])
                self.cal_df_en = pd.DataFrame(columns=["id", "priority", "unit", "asset_number", "manager", "contact",
                                                       "target_asset", "area", "coordinate", "mgrs", "description",
                                                       "dal_select", "weapon_system", "ammo_count", "threat_degree",
                                                       "engagement_effectiveness", "bmd_priority", "criticality", "vulnerability",
                                                       "threat", "total_score"])


            try:
                query = "SELECT * FROM dal_assets_priority_ko"
                self.dal_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM dal_assets_priority_en"
                self.dal_df_en = pd.read_sql_query(query, conn,)
            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.dal_df_ko = pd.DataFrame(columns=["id", "priority", "unit", "asset_number", "manager", "contact",
                                                       "target_asset", "area", "coordinate", "mgrs", "description",
                                                       "dal_select", "weapon_system", "ammo_count", "threat_degree",
                                                       "engagement_effectiveness", "bmd_priority", "criticality", "vulnerability",
                                                       "threat", "total_score"])
                self.dal_df_en = pd.DataFrame(columns=["id", "priority", "unit", "asset_number", "manager", "contact",
                                                       "target_asset", "area", "coordinate", "mgrs", "description",
                                                       "dal_select", "weapon_system", "ammo_count", "threat_degree",
                                                       "engagement_effectiveness", "bmd_priority", "criticality", "vulnerability",
                                                       "threat", "total_score"])

            try:
                query = "SELECT * FROM enemy_bases_ko"
                self.enemy_bases_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM enemy_bases_en"
                self.enemy_bases_df_en = pd.read_sql_query(query, conn,)
            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.enemy_bases_df_ko = pd.DataFrame(columns=["id", "base_name", "area", "coordinate", "mgrs", "weapon_system"])
                self.enemy_bases_df_en = pd.DataFrame(columns=["id", "base_name", "area", "coordinate", "mgrs", "weapon_system"])


            try:
                query = "SELECT * FROM weapon_assets_ko"
                self.weapon_assets_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM weapon_assets_en"
                self.weapon_assets_df_en = pd.read_sql_query(query, conn,)

            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.weapon_assets_df_ko = pd.DataFrame(columns=["id", "unit", "area", "asset_name", "coordinate", "mgrs", "weapon_system", "ammo_count", "threat_degree", "dal_select"])
                self.weapon_assets_df_en = pd.DataFrame(columns=["id", "unit", "area", "asset_name", "coordinate", "mgrs", "weapon_system", "ammo_count", "threat_degree", "dal_select"])

        except sqlite3.Error as e:
            print(f"데이터베이스 연결 오류: {e}")

        finally:
            if conn:
                conn.close()

        if self.cal_df_ko.empty and self.dal_df_ko.empty and self.enemy_bases_df_ko.empty and self.weapon_assets_df_ko:
            print("경고: 데이터를 불러오지 못했습니다. 빈 DataFrame을 사용합니다.")

    def refresh(self):
        # 데이터프레임 다시 로드
        self.load_dataframes()

        # 필터 초기화
        # 테이블의 모든 체크박스 해제
        self.assets_table.uncheckAllRows()
        self.unit_filter.setCurrentIndex(0)  # '전체'로 설정
        self.search_filter.clear()  # 검색창 초기화

        # 테이블의 모든 체크박스 해제
        self.enemy_sites_table.uncheckAllRows()
        self.missile_type_combo.setCurrentIndex(0)  # '전체'로 설정
        self.search_enemy_filter.clear()  # 검색창 초기화
        self.threat_radius_checkbox.setChecked(False)

        # 테이블의 모든 체크박스 해제
        self.defense_assets_table.uncheckAllRows()
        self.weapon_systems_combo.setCurrentIndex(0)  # '전체'로 설정
        self.search_defense_filter.clear()  # 검색창 초기화
        self.defense_radius_check.setChecked(False)

        # 테이블 데이터 다시 로드
        self.load_cal_assets()
        self.load_enemy_missile_sites()
        self.load_weapon_assets()

        # 지도 업데이트
        self.update_map()

    def initUI(self):
        """UI 초기화 메서드"""
        # UI 구성 변경
        main_layout = QVBoxLayout(self)
        main_splitter = QSplitter(Qt.Horizontal)

        # 좌측 위젯 (방어 대상 자산 우선순위 테이블)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # ... (필터, 테이블, 페이지네이션 코드 - ViewCopWindow 클래스 참고)
        # 필터 추가
        self.filter_layout = QHBoxLayout()

        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군")])
        self.unit_filter.currentTextChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.unit_filter)

        # 방어대상자산 테이블 검색 기능
        self.filter_layout = QHBoxLayout()
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText(self.tr("방어대상자산 또는 지역구분 검색"))
        self.search_button = QPushButton(self.tr("찾기"))
        self.search_button.clicked.connect(self.load_assets)
        self.filter_layout.addWidget(self.search_filter)
        self.filter_layout.addWidget(self.search_button)
        left_layout.addLayout(self.filter_layout)

        left_layout.addLayout(self.filter_layout)

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

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setContentsMargins(0, 20, 0, 20)
        button_layout.setAlignment(Qt.AlignCenter)  # 버튼을 중앙에 정렬

        self.return_button = QPushButton(self.tr("메인화면"), self)
        self.return_button.clicked.connect(self.parent.show_main_page)
        self.return_button.setFont(QFont("강한공군체", 15, QFont.Bold))
        self.return_button.setFixedSize(250, 50)  # 버튼 크기 고정 (너비 200, 높이 50)
        self.return_button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬
        button_layout.addWidget(self.return_button)
        left_layout.addLayout(button_layout)  # 버튼 레이아웃을 left_layout에 추가

        # 우측 상단 위젯 (적 기지 테이블)
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)



        # 우측 상단 테이블: 적 미사일 발사기지
        top_right_layout.addWidget(QLabel(self.tr("적 미사일 기지 목록")))

        # 필터 추가
        self.enemy_filter_layout = QHBoxLayout()

        # 적 미사일 기지 테이블 검색 기능
        self.enemy_filter_layout = QHBoxLayout()
        self.search_enemy_filter = QLineEdit()
        self.search_enemy_filter.setPlaceholderText(self.tr("적 기지명 또는 지역 검색"))
        self.search_enemy_button = QPushButton(self.tr("찾기"))
        self.search_enemy_button.clicked.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.search_enemy_filter)
        self.enemy_filter_layout.addWidget(self.search_enemy_button)
        top_right_layout.addLayout(self.enemy_filter_layout)

        # 미사일 타입 콤보박스
        self.missile_type_combo = QComboBox()
        with open('missile_info.json', 'r', encoding='utf-8') as file:
            missile_types = json.load(file)
        missile_types_list = [self.tr('전체')] + list(missile_types.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.missile_type_combo.addItems(missile_types_list)
        self.missile_type_combo.currentTextChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.missile_type_combo)

        # 위협반경 표시 체크박스
        self.threat_radius_checkbox = QCheckBox(self.tr("위협반경 표시"))
        self.threat_radius_checkbox.stateChanged.connect(self.toggle_threat_radius)
        self.enemy_filter_layout.addWidget(self.threat_radius_checkbox)

        top_right_layout.addLayout(self.enemy_filter_layout)

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
        for column in range(1, header.count()):
            self.enemy_sites_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        top_right_layout.addWidget(self.enemy_sites_table)

        # 우측 하단 위젯 (방어 자산 테이블)
        bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(bottom_right_widget)

        # 우측 중간 테이블 변경
        bottom_right_layout.addWidget(QLabel(self.tr("무기 자산 목록")))

        # 필터 추가
        self.weapon_filter_layout = QHBoxLayout()
        # 무기 자산 테이블 검색 기능
        self.weapon_filter_layout = QHBoxLayout()
        self.search_weapon_filter = QLineEdit()
        self.search_weapon_filter.setPlaceholderText(self.tr("방공포대 검색"))
        self.search_weapon_button = QPushButton(self.tr("찾기"))
        self.search_weapon_button.clicked.connect(self.load_weapon_assets)
        self.weapon_filter_layout.addWidget(self.search_weapon_filter)
        self.weapon_filter_layout.addWidget(self.search_weapon_button)
        bottom_right_layout.addLayout(self.weapon_filter_layout)

        # 미사일 타입 콤보박스
        self.weapon_type_combo = QComboBox()
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_types = json.load(file)
        weapon_types_list = [self.tr('전체')] + list(weapon_types.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.weapon_type_combo.addItems(weapon_types_list)
        self.weapon_type_combo.currentTextChanged.connect(self.load_weapon_assets)
        self.weapon_filter_layout.addWidget(self.weapon_type_combo)

        # 방어반경 표시 체크박스
        self.defense_radius_checkbox = QCheckBox(self.tr("방어반경 표시"))
        self.defense_radius_checkbox.stateChanged.connect(self.toggle_defense_radius)
        self.weapon_filter_layout.addWidget(self.defense_radius_checkbox)

        bottom_right_layout.addLayout(self.weapon_filter_layout)

        # 방어반경 표시 체크박스
        self.dal_select_checkbox = QCheckBox(self.tr("방어자산만 표시"))
        self.dal_select_checkbox.stateChanged.connect(self.load_weapon_assets)
        bottom_right_layout.addWidget(self.dal_select_checkbox)

        self.weapon_assets_table = MyTableWidget()
        self.weapon_assets_table.setColumnCount(5)  # 체크박스 열 추가
        self.weapon_assets_table.setHorizontalHeaderLabels(
            ["", self.tr("구성군"), self.tr("지역"), self.tr("자산명"), self.tr("무기체계")])
        # 행 번호 숨기기
        self.weapon_assets_table.verticalHeader().setVisible(False)
        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.weapon_assets_table.horizontalHeader().setFont(font)
        header = self.weapon_assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.weapon_assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(1, header.count()):
            self.weapon_assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        bottom_right_layout.addWidget(self.weapon_assets_table)

        # 중앙 위젯 (지도)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(0)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.map_view = QWebEngineView()  # 지도 표시용 웹뷰
        center_layout.addWidget(self.map_view)

        # 시뮬레이션 버튼 레이아웃
        simulate_button_layout = QHBoxLayout()
        simulate_button_layout.setSpacing(20)
        simulate_button_layout.setContentsMargins(0, 20, 0, 20)
        simulate_button_layout.setAlignment(Qt.AlignCenter)

        # 미사일 궤적 분석 버튼
        self.analyze_trajectories_button = QPushButton(self.tr("미사일 궤적분석"))
        self.analyze_trajectories_button.setFont(QFont("강한공군체", 12, QFont.Bold))
        self.analyze_trajectories_button.setFixedSize(200, 30)
        self.analyze_trajectories_button.setStyleSheet("QPushButton { text-align: center; }")

        self.analyze_trajectories_button.clicked.connect(self.run_trajectory_analysis)
        simulate_button_layout.addWidget(self.analyze_trajectories_button)

        # 최적 방공포대 위치 산출 버튼
        self.optimize_locations_button = QPushButton(self.tr("최적 방공포대 위치산출"))
        self.optimize_locations_button.setFont(QFont("강한공군체", 12, QFont.Bold))
        self.optimize_locations_button.setFixedSize(200, 30)
        self.optimize_locations_button.setStyleSheet("QPushButton { text-align: center; }")

        self.optimize_locations_button.clicked.connect(self.run_location_optimization)
        simulate_button_layout.addWidget(self.optimize_locations_button)

        center_layout.addLayout(simulate_button_layout)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        print_button_layout = QHBoxLayout()
        # 지도 출력 버튼
        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 12, QFont.Bold))
        self.print_button.setFixedSize(130, 30)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        print_button_layout.addWidget(self.print_button, alignment=Qt.AlignRight)
        # 수평 레이아웃을 center_layout에 추가
        center_layout.addLayout(print_button_layout)

        # 시뮬레이션 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        center_layout.addWidget(self.result_table)

        # 결과 테이블이 남은 공간을 모두 채우도록 설정
        center_layout.setStretchFactor(self.map_view, 2)
        center_layout.setStretchFactor(self.result_table, 1)

        # QSplitter를 사용하여 지도와 결과 테이블 사이의 크기 조절 가능하게 설정
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.map_view)
        splitter.addWidget(self.result_table)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        center_layout.addWidget(splitter)

        # Splitter에 위젯 추가 및 레이아웃 설정
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(top_right_widget)
        right_splitter.addWidget(bottom_right_widget)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(center_widget)
        main_splitter.addWidget(right_splitter)

        main_layout.addWidget(main_splitter)

        self.setLayout(main_layout)

        # 데이터베이스 연결 및 데이터 로드
        self.load_dataframes()

        with open("missile_info.json", "r", encoding="utf-8") as f:
            self.missile_info = json.load(f)
        with open("weapon_systems.json", "r", encoding="utf-8") as f:
            self.weapon_systems_info = json.load(f)

        self.load_assets()
        self.load_enemy_missile_sites()
        self.load_weapon_assets()
        # 초기 지도 표시 (필요에 따라 수정)
        self.update_map()

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.update_map()

    def toggle_threat_radius(self, state):
        self.show_threat_radius = state == Qt.Checked
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

        self.assets_table.uncheckAllRows()
        self.assets_table.setRowCount(len(filtered_df))
        for row, (_, asset) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(asset[['priority', 'unit', 'area', 'target_asset']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.assets_table.setItem(row, col, item)
        self.update_map()

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
        for row, (_, base) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.enemy_sites_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(base[['base_name', 'coordinate', 'weapon_system']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.enemy_sites_table.setItem(row, col, item)
        self.update_map()

    def load_weapon_assets(self):
        # 테이블 초기화
        weapon_assets_df = self.weapon_assets_df_ko if self.parent.selected_language == 'ko' else self.weapon_assets_df_en
        # 필터링 추가
        search_filter_text = self.search_weapon_filter.text()
        if self.dal_select_checkbox.isChecked():
            weapon_assets_df = weapon_assets_df[weapon_assets_df['dal_select'] == 1]
        if search_filter_text:
            weapon_assets_df = weapon_assets_df[
                (weapon_assets_df['asset_name'].str.contains(search_filter_text, case=False)) |
                (weapon_assets_df['area'].str.contains(search_filter_text, case=False)) |
                (weapon_assets_df['unit'].str.contains(search_filter_text, case=False))
                ]
        weapon_type_filter_text = self.weapon_type_combo.currentText()
        if weapon_type_filter_text != self.tr("전체"):
            weapon_assets_df = weapon_assets_df[weapon_assets_df['weapon_system'] == weapon_type_filter_text]
        self.weapon_assets_table.uncheckAllRows()
        self.weapon_assets_table.setRowCount(len(weapon_assets_df))
        for row, (_, weapons) in enumerate(weapon_assets_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.weapon_assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(weapons[['unit', 'area', 'asset_name', 'weapon_system']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.weapon_assets_table.setItem(row, col, item)
        self.update_map()

    def update_map(self):
        # 새로운 지도 객체를 생성하되, 현재의 중심 위치와 줌 레벨을 사용합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        selected_assets = self.get_selected_assets()
        selected_weapon_assets = self.get_selected_weapon_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        selected_enemy_weapons = self.get_selected_enemy_weapons()
        if selected_assets:
            SimulationCalMapView(selected_assets, self.map)
        if selected_weapon_assets:
            SimulationWeaponMapView(selected_weapon_assets, self.map, self.show_defense_radius)
        if selected_enemy_bases:
            SimulationEnemyBaseMapView(selected_enemy_weapons, self.map)
        if selected_enemy_weapons:
            SimulationEnemyWeaponMapView(selected_enemy_weapons, self.map, self.show_threat_radius)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

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
                dal_select = asset_info_ko.iloc[0]['dal_select']  if self.parent.selected_language == 'ko' else asset_info_en.iloc[0]['dal_select']
                coord = asset_info_ko.iloc[0]['coordinate'] if self.parent.selected_language == 'ko' else asset_info_en.iloc[0]['coordinate']
                selected_assets.append((asset_name, coord, dal_select, priority))
        return selected_assets

    def get_selected_weapon_assets(self):
        weapon_assets = []
        for row in range(self.weapon_assets_table.rowCount()):
            checkbox_widget = self.weapon_assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                unit = self.weapon_assets_table.item(row, 1).text()
                area = self.weapon_assets_table.item(row, 2).text()
                asset_name = self.weapon_assets_table.item(row, 3).text()
                weapon_system = self.weapon_assets_table.item(row, 4).text()

                asset_info = self.weapon_assets_df_ko if self.parent.selected_language == 'ko' else self.weapon_assets_df_en
                asset_info = asset_info[
                    (asset_info['unit'] == unit) &
                    (asset_info['area'] == area) &
                    (asset_info['asset_name'] == asset_name)
                    ]

                if not asset_info.empty:
                    unit = asset_info.iloc[0]['unit']
                    area = asset_info.iloc[0]['area']
                    coord = asset_info.iloc[0]['coordinate']
                    ammo_count = asset_info.iloc[0]['ammo_count']
                    threat_degree = asset_info.iloc[0]['threat_degree']
                    dal_select = asset_info.iloc[0]['dal_select']
                    weapon_assets.append((unit, area, asset_name, coord, weapon_system, ammo_count, threat_degree, dal_select))

        return weapon_assets

    def get_selected_enemy_bases(self):
        selected_enemy_bases = []
        for row in range(self.enemy_sites_table.rowCount()):
            checkbox_widget = self.enemy_sites_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_sites_table.item(row, 1).text()
                coordinate = self.enemy_sites_table.item(row, 2).text()
                weapon_system = self.enemy_sites_table.item(row, 3).text()
                selected_enemy_bases.append((base_name, coordinate, weapon_system))
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
                weapon_systems_list = weapon_system.split(", ")
                for weapon in weapon_systems_list:
                    if self.missile_type_combo.currentText() == self.tr('전체'):
                        selected_enemy_weapons.append((base_name, coordinate, weapon))
                    else:
                        if weapon == self.missile_type_combo.currentText():
                            selected_enemy_weapons.append((base_name, coordinate, weapon))
        return selected_enemy_weapons

    def calculate_trajectories(self):
        """미사일 궤적을 계산하는 메서드 (수정됨)"""
        try:
            selected_enemy_weapons = self.get_selected_enemy_weapons()
            selected_weapon_assets = self.get_selected_weapon_assets()
            selected_assets = self.get_selected_assets()
            if not selected_enemy_weapons or not selected_assets:
                QMessageBox.warning(self, self.tr("경고"), self.tr("미사일 기지 또는 방어 대상 자산을 선택하세요."))
                return

            self.trajectories = []
            self.defense_trajectories = []
            for base_name, missile_lat_lon, enemy_weapon in selected_enemy_weapons:
                for target_name, target_lat_lon, dal_select, priority in selected_assets:
                    try:
                        missile_lat, missile_lon = self.parse_coordinates(missile_lat_lon)
                        target_lat, target_lon = self.parse_coordinates(target_lat_lon)

                        distance = self.trajectory_calculator.calculate_distance(missile_lat, missile_lon,
                                                                                 target_lat, target_lon)
                        missile_type = self.determine_missile_type(distance, base_name)

                        if missile_type:
                            trajectory = self.calculate_trajectory((missile_lat, missile_lon),
                                                                   (target_lat, target_lon), missile_type)
                            if trajectory:
                                # 반환값 형식에 맞춰 데이터 저장
                                result = {
                                    'base_name' :base_name,
                                    'base_coordinate': (missile_lat, missile_lon),
                                    'target_name' : target_name,
                                    'target_coordinate' :(target_lat, target_lon),
                                    'missile_type': missile_type,
                                    'trajectory': trajectory
                                }

                                self.trajectories.append(result)
                                # 방어 가능한 궤적 따로 저장
                                if selected_weapon_assets:
                                    for unit, area, defense_asset_name, defense_lat_lon, weapon_type, ammo_count, threat_degree, dal_select in selected_weapon_assets:
                                        defense_lat, defense_lon = self.parse_coordinates(defense_lat_lon)
                                        threat_azimuth =  int(threat_degree)
                                        if self.check_engagement_possibility(defense_lat, defense_lon, weapon_type,
                                                                             trajectory, threat_azimuth):
                                            defense_result = {
                                                'base_name': base_name,
                                                'base_coordinate': (missile_lat, missile_lon),
                                                'target_name': target_name,
                                                'target_coordinate': (target_lat, target_lon),
                                                'defense_name' : defense_asset_name,
                                                'defense_coordinate': (defense_lat, defense_lon),
                                                'weapon_type': weapon_type,
                                                'missile_type': missile_type,
                                                'trajectory': trajectory
                                            }
                                            self.defense_trajectories.append(defense_result)

                    except ValueError as e:
                        print(self.tr(f"오류 발생: {e}"))

        except Exception as e:
            QMessageBox.critical(self, self.tr("에러"), self.tr(f"궤적 계산 중 오류 발생: {str(e)}"))

    def calculate_trajectory(self, missile_base, target, missile_type):
        """미사일 궤적을 계산하는 메서드 (MissileTrajectoryCalculator 사용)"""
        try:
            return self.trajectory_calculator.calculate_trajectory(missile_base, target, missile_type)
        except Exception as e:
            print(f"Error calculating trajectory: {e}")
            return None

    def update_map_with_trajectories(self):
        """미사일 궤적 및 방어 궤적을 지도에 표시하는 메서드"""
        # 새로운 지도 객체를 생성합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        # 선택된 자산, 방어 자산, 적 기지를 지도에 추가합니다.
        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_weapon_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        selected_enemy_weapons = self.get_selected_enemy_weapons()
        if selected_assets:
            SimulationCalMapView(selected_assets, self.map)
        if selected_defense_assets:
            SimulationWeaponMapView(selected_defense_assets, self.map, self.show_defense_radius)
        if selected_enemy_bases:
            SimulationEnemyBaseMapView(selected_enemy_bases, self.map)
        if selected_enemy_weapons:
            SimulationEnemyWeaponMapView(selected_enemy_bases, self.map, self.show_threat_radius)

        # 궤적을 지도에 추가하는 부분
        if hasattr(self, 'trajectories'):
            trajectory_groups = {}
            for trajectory_data in self.trajectories:
                trajectory = trajectory_data['trajectory']
                start = tuple(trajectory[0][:2])
                end = tuple(trajectory[-1][:2])
                key = (start, end)
                if key not in trajectory_groups:
                    trajectory_groups[key] = []
                trajectory_groups[key].append(trajectory)

            for (start, end), trajectories in trajectory_groups.items():
                representative_trajectory = trajectories[0]
                points = [(float(lat), float(lon)) for lat, lon, _ in representative_trajectory]
                simplified_points = simplify_coords(points, 0.001)

                is_defended = self.is_trajectory_defended(representative_trajectory)
                color = "green" if is_defended else "red"
                folium.PolyLine(
                    locations=simplified_points,
                    color=color,
                    weight=0.5,
                    opacity=0.8
                ).add_to(self.map)

                if is_defended:
                    for defense_tr_dic in self.defense_trajectories:
                        if self.is_same_trajectory(representative_trajectory, defense_tr_dic['trajectory']):
                            defense_coordinate = defense_tr_dic['defense_coordinate']
                            intercept_point = self.find_intercept_point(defense_tr_dic)
                            if intercept_point:
                                folium.PolyLine(
                                    locations=[defense_coordinate, intercept_point[:2]],
                                    color="blue",
                                    weight=0.5,
                                    opacity=0.8
                                ).add_to(self.map)

        # 지도를 HTML로 렌더링하고 웹뷰에 로드합니다.
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

        # 지도 로딩이 완료되었는지 확인합니다.
        self.map_view.loadFinished.connect(self.on_map_load_finished)

        # 지도 업데이트 후 화면을 갱신합니다.
        self.map_view.update()

    def run_trajectory_analysis(self):
        """미사일 궤적 분석 실행 메서드"""
        try:
            self.calculate_trajectories()
            total_trajectories = len(self.trajectories)  # 총 미사일 궤적 수

            # 중복을 제거한 유니크한 방어 가능 궤적 계산
            unique_defensible_trajectories = set()
            for defense_trajectory in self.defense_trajectories:
                # 궤적을 식별할 수 있는 고유한 키 생성 (예: 시작점과 끝점 좌표)
                base_lat, base_lon = defense_trajectory['base_coordinate']
                target_lat, target_lon = defense_trajectory['target_coordinate']
                trajectory_key = (base_lat, base_lon, target_lat, target_lon)
                unique_defensible_trajectories.add(trajectory_key)

            defensible_trajectories = len(unique_defensible_trajectories)  # 유니크한 방어 가능 궤적 수

            # 방어율 계산
            if total_trajectories > 0:
                defense_rate = (defensible_trajectories / total_trajectories) * 100
            else:
                defense_rate = 0

            # 결과 테이블 업데이트
            self.result_table.setRowCount(1)
            self.result_table.setColumnCount(3)
            self.result_table.setHorizontalHeaderLabels(["총 미사일 궤적", "방어 가능 궤적", "방어율"])
            self.result_table.setItem(0, 0, QTableWidgetItem(str(total_trajectories)))
            self.result_table.setItem(0, 1, QTableWidgetItem(str(defensible_trajectories)))
            self.result_table.setItem(0, 2, QTableWidgetItem(f"{defense_rate:.2f}%"))
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.result_table.verticalHeader().setVisible(False)

            # 지도 업데이트 (미사일 궤적 및 방어 궤적 표시)
            self.update_map_with_trajectories()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"미사일 궤적 분석 오류: {e}"))

    def is_trajectory_defended(self, trajectory):
        """주어진 궤적이 방어 가능한지 확인하는 메서드"""
        return any(self.is_same_trajectory(trajectory, defense_tr_dic['trajectory']) for defense_tr_dic in
                   self.defense_trajectories)

    def determine_missile_type(self, distance, base_name):
        """거리와 기지명에 따라 미사일 종류를 결정하는 메서드"""
        available_missiles = []

        # 현재 선택된 언어에 따라 적절한 DataFrame 선택
        df = self.enemy_bases_df_ko if self.parent.selected_language == 'ko' else self.enemy_bases_df_en

        # 해당 기지의 무기 시스템 정보 가져오기
        base_info = df[df['base_name'] == base_name]

        if not base_info.empty:
            weapons = base_info.iloc[0]['weapon_system'].split(', ')

            for missile_type, info in self.missile_info.items():
                if missile_type in weapons and int(info["min_radius"]) <= distance <= int(info["max_radius"]):
                    available_missiles.append(missile_type)

        if available_missiles:
            return random.choice(available_missiles)
        else:
            return None

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(y, x)
        return math.degrees(bearing)

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """두 지점 간의 거리를 계산하는 메서드 (km 단위)"""
        R = 6371  # 지구 반지름 (km)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(
            math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance

    def check_engagement_possibility(self, defense_lat, defense_lon, weapon_type, trajectory, threat_azimuth):
        """미사일 궤적이 방어 가능한지 확인하는 메서드"""
        range_tuple = (self.weapon_systems_info[weapon_type].get('min_radius'),
                       self.weapon_systems_info[weapon_type].get('max_radius'))  # 방어 유닛 사거리 (최소, 최대)
        altitude_tuple = (self.weapon_systems_info[weapon_type].get('min_altitude'),
                          self.weapon_systems_info[weapon_type].get('max_altitude'))  # 방어 유닛 요격 고도 (최소, 최대)
        angle = self.weapon_systems_info[weapon_type].get('angle')  # 방어 유닛 방위각

        for i in range(len(trajectory) - 1):
            start = trajectory[i]
            end = trajectory[i + 1]

            # 선분의 시작점과 끝점에 대해 교전 가능성 확인
            for point in [start, end]:
                M_lat, M_lon, Mz = point
                distance = self.calculate_distance(defense_lat, defense_lon, M_lat, M_lon)

                missile_azimuth = math.atan2(M_lat - defense_lat, M_lon - defense_lon)
                azimuth_diff = abs(missile_azimuth - math.radians(threat_azimuth))

                if (azimuth_diff <= math.radians(angle / 2) or azimuth_diff >= math.radians(360 - angle / 2)) and \
                        range_tuple[0] <= distance <= range_tuple[1] and \
                        altitude_tuple[0] <= Mz <= altitude_tuple[1]:
                    return True  # 선분의 끝점 중 하나라도 교전 가능한 경우

            # 선분이 방어 가능 공간을 통과하는지 확인
            if self.line_intersects_defense_zone(start, end, defense_lat, defense_lon, range_tuple, altitude_tuple,
                                                 angle, threat_azimuth):
                return True

        return False  # 궤적 전체에서 방어 가능한 지점이 없는 경우 False 반환

    def line_intersects_defense_zone(self, start, end, defense_lat, defense_lon, range_tuple, altitude_tuple, angle,
                                     threat_azimuth):
        """선분이 방어 가능 공간을 통과하는지 확인하는 메서드"""
        # 선분을 여러 개의 점으로 나누어 각 점에 대해 교전 가능성 확인
        steps = 100  # 선분을 나눌 점의 개수
        for i in range(1, steps):
            t = i / steps
            M_lat = start[0] + t * (end[0] - start[0])
            M_lon = start[1] + t * (end[1] - start[1])
            Mz = start[2] + t * (end[2] - start[2])

            distance = self.calculate_distance(defense_lat, defense_lon, M_lat, M_lon)
            missile_azimuth = math.atan2(M_lat - defense_lat, M_lon - defense_lon)
            azimuth_diff = abs(missile_azimuth - math.radians(threat_azimuth))

            if (azimuth_diff <= math.radians(angle / 2) or azimuth_diff >= math.radians(360 - angle / 2)) and \
                    range_tuple[0] <= distance <= range_tuple[1] and \
                    altitude_tuple[0] <= Mz <= altitude_tuple[1]:
                return True  # 선분 상의 한 점이라도 교전 가능한 경우

        return False  # 선분이 방어 가능 공간을 통과하지 않는 경우

    def find_intercept_point(self, defense_tr_dic):
        """방어 가능한 교전 지점을 찾는 메서드"""
        defense_lat, defense_lon = defense_tr_dic['defense_coordinate']
        trajectory = defense_tr_dic['trajectory']
        weapon_type = defense_tr_dic['weapon_type']
        defense_altitude_range = (self.weapon_systems_info[weapon_type].get('min_altitude'),
                                  self.weapon_systems_info[weapon_type].get('max_altitude'))
        defense_range = (self.weapon_systems_info[weapon_type].get('min_radius'),
                         self.weapon_systems_info[weapon_type].get('max_radius'))

        for i in range(len(trajectory) - 1):
            start = trajectory[i]
            end = trajectory[i + 1]

            # 선분 위의 점들을 검사
            steps = 100
            for j in range(steps + 1):
                t = j / steps
                lat = start[0] + t * (end[0] - start[0])
                lon = start[1] + t * (end[1] - start[1])
                altitude = start[2] + t * (end[2] - start[2])

                distance = self.calculate_distance(defense_lat, defense_lon, lat, lon)
                if (defense_range[0] <= distance <= defense_range[1] and
                        defense_altitude_range[0] <= altitude <= defense_altitude_range[1]):
                    return lat, lon, altitude

        return None


    def calculate_engagement_zones(self):
        """방공포대 교전가능 공간을 계산하는 메서드 (수정됨)"""
        try:
            self.engagement_zones = []
            self.grid_center={}
            lat_step = 0.2  # 위도 간격 (도)
            lon_step = 0.2  # 경도 간격 (도)

            # 격자 이름 생성을 위한 알파벳과 숫자 리스트
            alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            numbers = range(1, 27)  # 1부터 26까지

            lat_index = 0
            for lat in np.arange(38.5, 33.5, -lat_step):  # 위도 범위 (북에서 남으로)
                lon_index = 0
                for lon in np.arange(125.5, 129.5, lon_step):  # 경도 범위
                    grid_name = f"{alphabet[lon_index]}{numbers[lat_index]}"
                    self.grid_center[grid_name] = {'center': (lat, lon)}
                    lon_index += 1
                lat_index += 1

            for trajectory_dic in self.trajectories:
                for grid_name, grid_info in self.grid_center.items():
                    grid_center = grid_info['center']
                    # 각 격자 중심 위치를 방어 자산 위치로 임시 설정하여 교전 가능성 확인
                    for weapon_type in self.weapon_systems_info.keys():
                        for threat_azimuth in range(0, 360, 30):  # 30도 간격으로 변경
                            base_name = trajectory_dic.get('base_name')
                            missile_lat, missile_lon = trajectory_dic.get('base_coordinate')
                            target_name = trajectory_dic.get('target_name')
                            target_lat, target_lon = trajectory_dic.get('target_coordinate')
                            missile_type = trajectory_dic.get('missile_type')
                            trajectory = trajectory_dic.get('trajectory')

                            if self.check_engagement_possibility(grid_center[0], grid_center[1], weapon_type,
                                                                 trajectory, threat_azimuth):
                                temp_defense_result = {
                                    'base_name': base_name,
                                    'base_coordinate': (missile_lat, missile_lon),
                                    'target_name': target_name,
                                    'target_coordinate': (target_lat, target_lon),
                                    'defense_name': grid_name,
                                    'defense_coordinate': grid_center,
                                    'weapon_type': weapon_type,
                                    'missile_type': missile_type,
                                    'trajectory': trajectory,
                                    'threat_azimuth': threat_azimuth
                                }
                                self.engagement_zones.append(temp_defense_result)

        except Exception as e:
            QMessageBox.critical(self, "에러", f"교전 가능 공간 계산 중 오류 발생: {str(e)}")

    def optimize_locations(self):
        try:
            # 격자 범위 설정
            grid_bounds = np.array([[33.5, 38.5], [125.5, 129.5]])

            # 최적화 객체 생성
            optimizer = MissileDefenseOptimizer(self.trajectories, self.weapon_systems_info, grid_bounds)

            # 방어 시스템 수 설정 (예: 5개)
            num_defense_systems = 5

            # 최적화 실행
            optimized_positions = optimizer.optimize(num_defense_systems)

            # 최적화 결과 저장
            self.optimized_locations = []
            for position in optimized_positions:
                for trajectory in self.trajectories:
                    if optimizer.is_trajectory_defended(trajectory, position):
                        self.optimized_locations.append({
                            'defense_coordinate': tuple(position),
                            'trajectory': trajectory['trajectory'],
                            'base_name': trajectory['base_name'],
                            'target_name': trajectory['target_name'],
                            'missile_type': trajectory['missile_type'],
                            'weapon_type': 'Optimal'  # 실제 무기 유형은 추가 로직으로 결정 가능
                        })

            # 결과 출력 및 지도 업데이트
            self.update_result_table()
            self.update_map_with_optimized_locations()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"최적 방공포대 위치 산출 오류: {e}"))

    def update_result_table(self):
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["최적 위치", "방어 가능 자산", "무기 유형", "위협 방위각"])

        for location in self.optimized_locations:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(str(location['defense_coordinate'])))
            self.result_table.setItem(row, 1, QTableWidgetItem(location['target_name']))
            self.result_table.setItem(row, 2, QTableWidgetItem(location['weapon_type']))
            self.result_table.setItem(row, 3, QTableWidgetItem("N/A"))  # 방위각은 추가 계산 필요

    def run_location_optimization(self):
        try:
            self.calculate_trajectories()
            self.optimize_locations()

            if not self.optimized_locations:
                QMessageBox.warning(self, "경고", "최적화된 위치가 없습니다.")
                return

            self.update_result_table()
            self.update_map_with_optimized_locations()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"최적 방공포대 위치 산출 오류: {e}"))

    def update_map_with_optimized_locations(self):
        """미사일 궤적, 방어 궤적, 격자, 최적 위치를 지도에 표시하는 메서드"""
        # 새로운 지도 객체를 생성합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        # 선택된 자산, 방어 자산, 적 기지를 지도에 추가합니다.
        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_weapon_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        selected_enemy_weapons = self.get_selected_enemy_weapons()
        if selected_assets:
            SimulationCalMapView(selected_assets, self.map)
        if selected_defense_assets:
            SimulationWeaponMapView(selected_defense_assets, self.map, self.show_defense_radius)
        if selected_enemy_bases:
            SimulationEnemyBaseMapView(selected_enemy_bases, self.map)
        if selected_enemy_weapons:
            SimulationEnemyWeaponMapView(selected_enemy_bases, self.map, self.show_threat_radius)

        # 격자 및 라벨 표시
        lat_step = 0.2
        lon_step = 0.2
        grid_color = "gray"
        grid_opacity = 0.5

        for lat in np.arange(33.5, 38.7, lat_step):
            folium.PolyLine(
                locations=[(lat, 125.5), (lat, 129.5)],
                color=grid_color,
                weight=1,
                opacity=grid_opacity
            ).add_to(self.map)

        for lon in np.arange(125.5, 129.7, lon_step):
            folium.PolyLine(
                locations=[(33.5, lon), (38.5, lon)],
                color=grid_color,
                weight=1,
                opacity=grid_opacity
            ).add_to(self.map)

        # 격자 라벨 추가
        # letters = 'ABCDEFGHIJKLMN'
        # for i, lat in enumerate(np.arange(33.5, 38.7, lat_step)):
        #     folium.Marker(
        #         [lat, 125.4],
        #         icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color:{grid_color}">{i + 1}</div>')
        #     ).add_to(self.map)
        #
        # for i, lon in enumerate(np.arange(125.5, 129.7, lon_step)):
        #     folium.Marker(
        #         [38.6, lon],
        #         icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color:{grid_color}">{letters[i]}</div>')
        #     ).add_to(self.map)

        if hasattr(self, 'trajectories'):
            trajectory_groups = {}
            for trajectory_data in self.trajectories:
                trajectory = trajectory_data.get('trajectory')
                if trajectory is None or not isinstance(trajectory, list) or len(trajectory) < 2:
                    continue  # trajectory가 없거나 올바르지 않은 형식인 경우 건너뜁니다.
                start = tuple(trajectory[0][:2])
                end = tuple(trajectory[-1][:2])
                key = (start, end)
                if key not in trajectory_groups:
                    trajectory_groups[key] = []
                trajectory_groups[key].append(trajectory)

            for (start, end), trajectories in trajectory_groups.items():
                # 그룹의 대표 궤적 선택
                representative_trajectory = trajectories[0]
                points = [(float(lat), float(lon)) for lat, lon, _ in representative_trajectory if
                          isinstance(lat, (int, float)) and isinstance(lon, (int, float))]

                if len(points) < 2:
                    continue  # 유효한 포인트가 2개 미만인 경우 건너뜁니다.

                # 궤적 간소화
                simplified_points = simplify_coords(points, 0.001)

                # 방어 가능한 궤적 여부 확인
                is_defended = self.is_trajectory_defended_temp(representative_trajectory)

                # 간소화된 궤적 표시 (방어 가능한 경우 녹색, 그렇지 않은 경우 빨간색)
                color = "green" if is_defended else "red"
                folium.PolyLine(
                    locations=simplified_points,
                    color=color,
                    weight=0.5,
                    opacity=0.8
                ).add_to(self.map)

                # 방어 가능한 궤적에 대해 교전 지점 표시
                if is_defended:
                    for optimized_location_dic in self.optimized_locations:
                        if self.is_same_trajectory(representative_trajectory, optimized_location_dic['trajectory']):
                            temp_defense_coordinate = optimized_location_dic['defense_coordinate']
                            intercept_point = self.find_intercept_point(optimized_location_dic)
                            if intercept_point:
                                folium.PolyLine(
                                    locations=[temp_defense_coordinate, intercept_point[:2]],
                                    color="blue",
                                    weight=0.5,
                                    opacity=0.8
                                ).add_to(self.map)

        # 최적 위치 표시 (작은 녹색 사각형으로 변경)
        for optimized_location_dic in self.optimized_locations:
            folium.Rectangle(
                bounds=[optimized_location_dic.get('defense_coordinate'),
                        optimized_location_dic.get('defense_coordinate')],
                color='green',
                fill=True,
                fillColor='green',
                weight=2,
                fillOpacity=0.8,
                popup=f"최적 위치: {optimized_location_dic.get('defense_coordinate')}",
            ).add_to(self.map)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

        # 지도 로딩이 완료되었는지 확인합니다.
        self.map_view.loadFinished.connect(self.on_map_load_finished)

    def is_trajectory_defended_temp(self, trajectory):
        """주어진 궤적이 방어 가능한지 확인하는 메서드"""
        return any(self.is_same_trajectory(trajectory, optimized_location_dic.get('trajectory', []))
                   for optimized_location_dic in self.optimized_locations
                   if 'trajectory' in optimized_location_dic)

    @staticmethod
    def is_same_trajectory(trajectory1, trajectory2):
        """두 궤적이 동일한지 확인하는 메서드"""
        if not isinstance(trajectory1, list) or not isinstance(trajectory2, list):
            return False
        if len(trajectory1) != len(trajectory2):
            return False
        return all(np.allclose(np.array(p1), np.array(p2)) for p1, p2 in zip(trajectory1, trajectory2))


    @staticmethod
    def on_map_load_finished(result):
        if result:
            print("지도가 성공적으로 로드되었습니다.")
        else:
            print("지도 로딩에 실패했습니다.")

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Simulation Result")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Simulation Result")

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

class CenteredCheckBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def isChecked(self):
        return self.checkbox.isChecked()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

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

class MyTableWidget(QTableWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.setHorizontalHeader(CheckBoxHeader(Qt.Horizontal, self))

    def on_header_clicked(self, checked):
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.checkbox.setChecked(checked)

    def uncheckAllRows(self):
        self.horizontalHeader().isOn = False
        self.horizontalHeader().updateSection(0)
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.setChecked(False)

class MainWindow(QtWidgets.QMainWindow, QObject):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CAL/DAL Management System")
        self.setWindowIcon(QIcon("logo.png"))
        self.setMinimumSize(800, 600)
        self.map_app = MapApp()
        self.selected_language = "ko"  # 기본 언어 설정
        self.central_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(self.central_widget)
        self.db_path = 'assets_management.db'
        self.missile_defense_window = MissileDefenseApp(self)
        self.central_widget.addWidget(self.missile_defense_window)


    def show_main_page(self):
        self.central_widget.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


