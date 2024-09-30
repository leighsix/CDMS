import sys
import sqlite3
import csv, json, re
import random
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QHBoxLayout, QSplitter, QComboBox, QLineEdit, QTableWidget, QPushButton, QLabel,
                             QGroupBox, QCheckBox, QHeaderView, QDialog, QTableWidgetItem)
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
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from common_map_view import CommonMapView, DefenseAssetCommonMapView
from enemy_map_view import EnemyBaseWeaponMapView
from setting import MapApp
import mgrs
import folium
import io
import os
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtCore import QDateTime
from PyQt5.QtGui import QPainter, QPixmap
import pandas as pd
from scipy.optimize import linprog

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'

class MissileDefenseApp(QDialog):
    def __init__(self, parent=None):
        super(MissileDefenseApp, self).__init__(parent)
        self.trajectories = []
        self.engagement_zones = {}
        self.optimized_locations = []
        self.fig, self.ax = plt.subplots()
        self.parent = parent
        self.conn = sqlite3.connect(self.parent.db_path)
        self.cursor = self.conn.cursor()
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.setWindowTitle(self.tr("미사일 방어 시뮬레이션"))
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
        # 테이블의 모든 체크박스 해제
        self.cal_assets_table.uncheckAllRows()
        self.unit_filter.setCurrentIndex(0)  # '전체'로 설정
        self.search_filter.clear()  # 검색창 초기화
        self.display_cal_count_combo.setCurrentIndex(0)


        # 테이블의 모든 체크박스 해제
        self.enemy_sites_table.uncheckAllRows()
        self.missile_type_combo.setCurrentIndex(0)  # '전체'로 설정
        self.search_enemy_filter.clear()  # 검색창 초기화
        self.threat_radius_checkbox.setChecked(False)
        self.display_enemy_count_combo.setCurrentIndex(0)


        # 테이블의 모든 체크박스 해제
        self.defense_assets_table.uncheckAllRows()
        self.weapon_systems_combo.setCurrentIndex(0)  # '전체'로 설정
        self.search_defense_filter.clear()  # 검색창 초기화
        self.defense_radius_check.setChecked(False)
        self.display_dal_count_combo2.setCurrentIndex(0)


        # 테이블 데이터 다시 로드
        self.load_cal_assets()
        self.load_enemy_missile_sites()
        self.load_dal_assets()

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
        self.unit_filter.currentTextChanged.connect(self.load_cal_assets)
        self.filter_layout.addWidget(self.unit_filter)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText(self.tr("방어대상자산 또는 지역구분 검색"))
        self.search_filter.textChanged.connect(self.load_cal_assets)
        self.filter_layout.addWidget(self.search_filter)

        self.display_cal_count_combo = QComboBox()
        self.display_cal_count_combo.addItems(["30", "50", "100", "200"])
        self.display_cal_count_combo.currentTextChanged.connect(self.load_cal_assets)
        self.filter_layout.addWidget(self.display_cal_count_combo)
        left_layout.addLayout(self.filter_layout)

        self.cal_assets_table = MyTableWidget()
        self.cal_assets_table.setColumnCount(7)
        self.cal_assets_table.setHorizontalHeaderLabels(
            ["", self.tr("우선순위"), self.tr("구성군"), self.tr("지역구분"), self.tr("방어대상자산"), self.tr("경위도"), self.tr('군사좌표(MGRS)')])

        # 행 번호 숨기기
        self.cal_assets_table.verticalHeader().setVisible(False)
        self.cal_assets_table.setColumnHidden(5, True)
        self.cal_assets_table.setColumnHidden(6, True)


        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.cal_assets_table.horizontalHeader().setFont(font)
        header = self.cal_assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        header.resizeSection(1, 80)

        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.cal_assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()):
            self.cal_assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        left_layout.addWidget(self.cal_assets_table)

        # 페이지네이션 컨트롤 추가
        self.cal_pagination_layout = QHBoxLayout()
        self.cal_prev_button = QPushButton("◀")
        self.cal_next_button = QPushButton("▶")
        self.cal_page_label = QLabel()

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
        self.cal_prev_button.setStyleSheet(button_style)
        self.cal_next_button.setStyleSheet(button_style)

        # 레이아웃에 위젯 추가
        self.cal_pagination_layout.addWidget(self.cal_prev_button)
        self.cal_pagination_layout.addWidget(self.cal_page_label)
        self.cal_pagination_layout.addWidget(self.cal_next_button)

        # 레이아웃 정렬 및 간격 설정
        self.cal_pagination_layout.setAlignment(Qt.AlignCenter)
        self.cal_pagination_layout.setSpacing(10)

        left_layout.addLayout(self.cal_pagination_layout)

        # 버튼 연결
        self.cal_prev_button.clicked.connect(self.cal_prev_page)
        self.cal_next_button.clicked.connect(self.cal_next_page)

        # 초기 페이지 설정
        self.cal_current_page = 1
        self.cal_rows_per_page = 30  # 기본값 설정
        self.cal_total_pages = 1  # 초기값 설정
        self.cal_update_page_label()

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


        # 우측 상단 위젯 (적 기지 테이블)
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)


        # 우측 상단 테이블: 적 미사일 발사기지
        # 필터 추가
        self.enemy_filter_layout = QHBoxLayout()

        # 검색 창
        self.search_enemy_filter = QLineEdit()
        self.search_enemy_filter.setPlaceholderText(self.tr("적 기지명 또는 지역 검색"))
        self.search_enemy_filter.textChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.search_enemy_filter)


        # 무기체계 콤보박스
        self.missile_type_combo = QComboBox()
        with open('missile_info.json', 'r', encoding='utf-8') as file:
            missile_types = json.load(file)
        # '전체' 항목을 포함한 무기체계 목록 생성
        missile_types_list = [self.tr('전체')] + list(missile_types.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.missile_type_combo.addItems(missile_types_list)
        self.missile_type_combo.currentTextChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.missile_type_combo)


        self.display_enemy_count_combo = QComboBox()
        self.display_enemy_count_combo.addItems(["30", "50", "100", "200"])
        self.display_enemy_count_combo.currentTextChanged.connect(self.load_enemy_missile_sites)
        self.enemy_filter_layout.addWidget(self.display_enemy_count_combo)

        # 위협반경 표시 체크박스
        self.threat_radius_checkbox = QCheckBox(self.tr("위협반경 표시"))
        self.threat_radius_checkbox.stateChanged.connect(self.toggle_threat_radius)
        self.enemy_filter_layout.addWidget(self.threat_radius_checkbox)

        top_right_layout.addLayout(self.enemy_filter_layout)

        self.enemy_sites_table = MyTableWidget()
        self.enemy_sites_table.setColumnCount(6)
        self.enemy_sites_table.setHorizontalHeaderLabels(["", self.tr("발사기지"), self.tr("지역"), self.tr("보유미사일"), self.tr("경위도"), self.tr("군사좌표(MGRS)")])
        # 행 번호 숨기기
        self.enemy_sites_table.verticalHeader().setVisible(False)
        self.enemy_sites_table.setColumnHidden(4, True)
        self.enemy_sites_table.setColumnHidden(5, True)

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

        top_right_layout.addWidget(self.enemy_sites_table)

        # 페이지네이션 컨트롤 추가
        self.enemy_pagination_layout = QHBoxLayout()
        self.enemy_prev_button = QPushButton("◀")
        self.enemy_next_button = QPushButton("▶")
        self.enemy_page_label = QLabel()

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
        self.enemy_prev_button.setStyleSheet(button_style)
        self.enemy_next_button.setStyleSheet(button_style)

        # 레이아웃에 위젯 추가
        self.enemy_pagination_layout.addWidget(self.enemy_prev_button)
        self.enemy_pagination_layout.addWidget(self.enemy_page_label)
        self.enemy_pagination_layout.addWidget(self.enemy_next_button)

        # 레이아웃 정렬 및 간격 설정
        self.enemy_pagination_layout.setAlignment(Qt.AlignCenter)
        self.enemy_pagination_layout.setSpacing(10)

        top_right_layout.addLayout(self.enemy_pagination_layout)

        # 버튼 연결
        self.enemy_prev_button.clicked.connect(self.enemy_prev_page)
        self.enemy_next_button.clicked.connect(self.enemy_next_page)

        # 초기 페이지 설정
        self.enemy_current_page = 1
        self.enemy_rows_per_page = 30  # 기본값 설정
        self.enemy_total_pages = 1  # 초기값 설정
        self.enemy_update_page_label()

        # 우측 하단 위젯 (방어 자산 테이블)
        bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(bottom_right_widget)

        # 필터 추가
        self.defense_assets_filter_layout = QHBoxLayout()

        # 검색 창
        self.search_defense_filter = QLineEdit()
        self.search_defense_filter.setPlaceholderText(self.tr("방어자산명 또는 구성군, 지역 검색"))
        self.search_defense_filter.textChanged.connect(self.load_dal_assets)
        self.defense_assets_filter_layout.addWidget(self.search_defense_filter)

        # 무기체계 콤보박스
        self.weapon_systems_combo = QComboBox()
        # weapon_systems.json 파일에서 무기체계 데이터 읽기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_systems = json.load(file)
        weapon_systems_list = [self.tr('전체')] + list(weapon_systems.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.weapon_systems_combo.addItems(weapon_systems_list)
        self.weapon_systems_combo.currentTextChanged.connect(self.load_dal_assets)
        self.defense_assets_filter_layout.addWidget(self.weapon_systems_combo)

        self.display_dal_count_combo = QComboBox()
        self.display_dal_count_combo.addItems(["30", "50", "100", "200"])
        self.display_dal_count_combo.currentTextChanged.connect(self.load_dal_assets)
        self.defense_assets_filter_layout.addWidget(self.display_dal_count_combo)

        # 위협반경 표시 체크박스
        self.defense_radius_checkbox = QCheckBox(self.tr("방어반경 표시"))
        self.defense_radius_checkbox.stateChanged.connect(self.toggle_defense_radius)
        self.defense_assets_filter_layout.addWidget(self.defense_radius_checkbox)


        bottom_right_layout.addLayout(self.defense_assets_filter_layout)

        self.defense_assets_table = MyTableWidget()
        # ... (테이블 설정 - ViewCopWindow 클래스 참고)
        self.defense_assets_table.setColumnCount(9)
        self.defense_assets_table.setHorizontalHeaderLabels(["", self.tr("구성군"),  self.tr("지역"), self.tr("방어자산명"), self.tr("무기체계"), self.tr('위협방위'), self.tr('보유탄수'), self.tr('경위도'), self.tr('군사좌표(MGRS)')])
        # 행 번호 숨기기
        self.defense_assets_table.verticalHeader().setVisible(False)
        self.defense_assets_table.setColumnHidden(5, True)
        self.defense_assets_table.setColumnHidden(6, True)
        self.defense_assets_table.setColumnHidden(7, True)
        self.defense_assets_table.setColumnHidden(8, True)
        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.defense_assets_table.horizontalHeader().setFont(font)
        header = self.defense_assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.defense_assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()):
            self.defense_assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        bottom_right_layout.addWidget(self.defense_assets_table)

        # 페이지네이션 컨트롤 추가
        self.dal_pagination_layout = QHBoxLayout()
        self.dal_prev_button = QPushButton("◀")
        self.dal_next_button = QPushButton("▶")
        self.dal_page_label = QLabel()

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
        self.dal_prev_button.setStyleSheet(button_style)
        self.dal_next_button.setStyleSheet(button_style)

        # 레이아웃에 위젯 추가
        self.dal_pagination_layout.addWidget(self.dal_prev_button)
        self.dal_pagination_layout.addWidget(self.dal_page_label)
        self.dal_pagination_layout.addWidget(self.dal_next_button)

        # 레이아웃 정렬 및 간격 설정
        self.dal_pagination_layout.setAlignment(Qt.AlignCenter)
        self.dal_pagination_layout.setSpacing(10)

        bottom_right_layout.addLayout(self.dal_pagination_layout)

        # 버튼 연결
        self.dal_prev_button.clicked.connect(self.dal_prev_page)
        self.dal_next_button.clicked.connect(self.dal_next_page)

        # 초기 페이지 설정
        self.dal_current_page = 1
        self.dal_rows_per_page = 30  # 기본값 설정
        self.dal_total_pages = 1  # 초기값 설정
        self.dal_update_page_label()


        # 중앙 위젯 (지도)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.map_view = QWebEngineView()  # 지도 표시용 웹뷰
        center_layout.addWidget(self.map_view)

        # 시뮬레이션 버튼
        simulate_button = QPushButton(self.tr("시뮬레이션 실행"))
        simulate_button.clicked.connect(self.run_simulation)
        center_layout.addWidget(simulate_button)

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
        self.mgrs_converter = mgrs.MGRS()

        with open("missile_info.json", "r", encoding="utf-8") as f:
            self.missile_info = json.load(f)
        with open("weapon_systems.json", "r", encoding="utf-8") as f:
            self.weapon_systems_info = json.load(f)


        self.load_cal_assets()
        self.load_enemy_missile_sites()
        self.load_dal_assets()
        # 초기 지도 표시 (필요에 따라 수정)
        self.update_map()

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.update_map()

    def toggle_threat_radius(self, state):
        self.show_threat_radius = state == Qt.Checked
        self.update_map()

    def load_cal_assets(self):
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
        self.cal_rows_per_page = int(self.display_cal_count_combo.currentText())
        self.cal_total_pages = -(-len(filtered_df) // self.cal_rows_per_page)  # 올림 나눗셈

        # 현재 페이지에 해당하는 데이터만 선택
        start_idx = (self.cal_current_page - 1) * self.cal_rows_per_page
        end_idx = start_idx + self.cal_rows_per_page
        page_df = filtered_df.iloc[start_idx:end_idx]

        self.cal_assets_table.uncheckAllRows()
        self.cal_assets_table.setRowCount(len(page_df))
        for row, (_, asset) in enumerate(page_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.cal_assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(asset[['priority', 'unit', 'area', 'target_asset', 'coordinate', 'mgrs']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.cal_assets_table.setItem(row, col, item)

        self.update_map()
        self.cal_update_pagination()

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

        # 페이지네이션 설정
        self.enemy_rows_per_page = int(self.display_enemy_count_combo.currentText())
        self.enemy_total_pages = -(-len(filtered_df) // self.enemy_rows_per_page)  # 올림 나눗셈

        # 현재 페이지에 해당하는 데이터만 선택
        start_idx = (self.enemy_current_page - 1) * self.enemy_rows_per_page
        end_idx = start_idx + self.enemy_rows_per_page
        page_df = filtered_df.iloc[start_idx:end_idx]

        self.enemy_sites_table.uncheckAllRows()
        self.enemy_sites_table.setRowCount(len(page_df))
        for row, (_, base) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.enemy_sites_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(base[['base_name', 'area', 'weapon_system', 'coordinate', 'mgrs']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.enemy_sites_table.setItem(row, col, item)

        self.update_map()
        self.enemy_update_pagination()

    def load_dal_assets(self):
        filtered_df = self.dal_df_ko if self.parent.selected_language == 'ko' else self.dal_df_en

        search_filter_text = self.search_defense_filter.text()
        if search_filter_text:
            filtered_df = filtered_df[
                (filtered_df['asset_name'].str.contains(search_filter_text, case=False)) |
                (filtered_df['unit'].str.contains(search_filter_text, case=False)) |
                (filtered_df['area'].str.contains(search_filter_text, case=False)) |
                (filtered_df['weapon_system'].str.contains(search_filter_text, case=False))
                ]

        weapon_filter_text = self.weapon_systems_combo.currentText()
        if weapon_filter_text != self.tr("전체"):
            filtered_df = filtered_df[
                filtered_df['weapon_system'].apply(lambda x: weapon_filter_text in x.split(', '))]


        # 페이지네이션 설정
        self.dal_rows_per_page = int(self.display_dal_count_combo.currentText())
        self.dal_total_pages = -(-len(filtered_df) // self.dal_rows_per_page)  # 올림 나눗셈

        # 현재 페이지에 해당하는 데이터만 선택
        start_idx = (self.dal_current_page - 1) * self.dal_rows_per_page
        end_idx = start_idx + self.dal_rows_per_page
        page_df = filtered_df.iloc[start_idx:end_idx]

        self.defense_assets_table.uncheckAllRows()
        self.defense_assets_table.setRowCount(len(page_df))
        for row, (_, base) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.defense_assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(base[['unit', 'area', 'asset_name', 'weapon_system', 'threat_degree', 'ammo_count', 'coordinate', 'mgrs']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.defense_assets_table.setItem(row, col, item)

        self.update_map()
        self.dal_update_pagination()

    def update_map(self):
        # 새로운 지도 객체를 생성하되, 현재의 중심 위치와 줌 레벨을 사용합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_defense_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        if selected_assets:
            CommonMapView(selected_assets, self.map)
        if selected_defense_assets:
            DefenseAssetCommonMapView(selected_defense_assets, self.show_defense_radius, self.map)
        if selected_enemy_bases:
            EnemyBaseWeaponMapView(selected_enemy_bases, self.show_threat_radius, self.map)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

    def get_selected_assets(self):
        selected_assets = []
        asset_info_ko = pd.DataFrame()
        asset_info_en = pd.DataFrame()
        for row in range(self.cal_assets_table.rowCount()):
            checkbox_widget = self.cal_assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                priority = int(self.cal_assets_table.item(row, 1).text())
                unit = self.cal_assets_table.item(row, 2).text()
                area = self.cal_assets_table.item(row, 3).text()
                asset_name = self.cal_assets_table.item(row, 4).text()
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
        dal_info_ko = pd.DataFrame()
        dal_info_en = pd.DataFrame()
        for row in range(self.defense_assets_table.rowCount()):
            checkbox_widget = self.defense_assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                unit = self.defense_assets_table.item(row, 1).text()
                area = self.defense_assets_table.item(row, 2).text()
                asset_name = self.defense_assets_table.item(row, 3).text()
                weapon_system = self.defense_assets_table.item(row, 4).text()

                if self.parent.selected_language == 'ko':
                    dal_info_ko = self.dal_df_ko[
                        (self.dal_df_ko['asset_name'] == asset_name) &
                        (self.dal_df_ko['unit'] == unit) &
                        (self.dal_df_ko['area'] == area) &
                        (self.dal_df_ko['weapon_system'] == weapon_system)
                        ]
                else:
                    dal_info_en = self.enemy_bases_df_en[
                        (self.dal_df_en['asset_name'] == asset_name) &
                        (self.dal_df_en['unit'] == unit) &
                        (self.dal_df_en['area'] == area) &
                        (self.dal_df_en['weapon_system'] == weapon_system)
                        ]
                mgrs_coord = dal_info_ko.iloc[0]['mgrs'] if self.parent.selected_language == 'ko' else dal_info_en.iloc[0]['mgrs']
                threat_degree = dal_info_ko.iloc[0]['threat_degree'] if self.parent.selected_language == 'ko' else dal_info_en.iloc[0]['threat_degree']
                selected_defense_assets.append((asset_name, mgrs_coord, weapon_system, threat_degree))
        return selected_defense_assets

    def get_selected_enemy_bases(self):
        selected_enemy_bases = []
        bases_info_ko = pd.DataFrame()
        bases_info_en = pd.DataFrame()
        for row in range(self.enemy_sites_table.rowCount()):
            checkbox_widget = self.enemy_sites_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_sites_table.item(row, 1).text()
                area = self.enemy_sites_table.item(row, 2).text()
                weapon_system = self.enemy_sites_table.item(row, 3).text()
                if self.parent.selected_language == 'ko':
                    bases_info_ko = self.enemy_bases_df_ko[
                        (self.enemy_bases_df_ko['base_name'] == base_name) &
                        (self.enemy_bases_df_ko['area'] == area) &
                        (self.enemy_bases_df_ko['weapon_system'] == weapon_system)
                        ]
                else:
                    bases_info_en = self.enemy_bases_df_en[
                        (self.enemy_bases_df_en['base_name'] == base_name) &
                        (self.enemy_bases_df_en['area'] == area) &
                        (self.enemy_bases_df_en['weapon_system'] == weapon_system)
                        ]
                mgrs_coord = bases_info_ko.iloc[0]['mgrs'] if self.parent.selected_language == 'ko' else bases_info_en.iloc[0]['mgrs']
                selected_enemy_bases.append((base_name, mgrs_coord, weapon_system))
        return selected_enemy_bases

    def cal_update_pagination(self):
        self.cal_page_label.setText(f"{self.cal_current_page} / {self.cal_total_pages}")
        self.cal_prev_button.setEnabled(self.cal_current_page > 1)
        self.cal_next_button.setEnabled(self.cal_current_page < self.cal_total_pages)

    def cal_update_page_label(self):
        self.cal_page_label.setText(f"{self.cal_current_page} / {self.cal_total_pages}")

    def cal_prev_page(self):
        if self.cal_current_page > 1:
            self.cal_current_page -= 1
            self.cal_update_page_label()
            self.load_cal_assets()

    def cal_next_page(self):
        if self.cal_current_page < self.cal_total_pages:
            self.cal_current_page += 1
            self.cal_update_page_label()
            self.load_cal_assets()

    def enemy_update_pagination(self):
        self.enemy_page_label.setText(f"{self.enemy_current_page} / {self.enemy_total_pages}")
        self.enemy_prev_button.setEnabled(self.enemy_current_page > 1)
        self.enemy_next_button.setEnabled(self.enemy_current_page < self.enemy_total_pages)

    def enemy_update_page_label(self):
        self.enemy_page_label.setText(f"{self.enemy_current_page} / {self.enemy_total_pages}")

    def enemy_prev_page(self):
        if self.enemy_current_page > 1:
            self.enemy_current_page -= 1
            self.enemy_update_page_label()
            self.load_enemy_missile_sites()

    def enemy_next_page(self):
        if self.enemy_current_page < self.enemy_total_pages:
            self.enemy_current_page += 1
            self.enemy_update_page_label()
            self.load_enemy_missile_sites()

    def dal_update_pagination(self):
        self.dal_page_label.setText(f"{self.dal_current_page} / {self.dal_total_pages}")
        self.dal_prev_button.setEnabled(self.dal_current_page > 1)
        self.dal_next_button.setEnabled(self.dal_current_page < self.dal_total_pages)

    def dal_update_page_label(self):
        self.dal_page_label.setText(f"{self.dal_current_page} / {self.dal_total_pages}")

    def dal_prev_page(self):
        if self.dal_current_page > 1:
            self.dal_current_page -= 1
            self.dal_update_page_label()
            self.load_dal_assets()

    def dal_next_page(self):
        if self.dal_current_page < self.dal_total_pages:
            self.dal_current_page += 1
            self.dal_update_page_label()
            self.load_dal_assets()

    def calculate_trajectories(self):
        """미사일 궤적을 계산하는 메서드"""
        try:
            m_conv = mgrs.MGRS()

            selected_enemy_bases = self.get_selected_items(self.enemy_sites_table)
            selected_defense_assets = self.get_selected_items(self.defense_assets_table)
            selected_cal_assets = self.get_selected_items(self.cal_assets_table)
            if not selected_enemy_bases or not selected_defense_assets or not selected_cal_assets:
                QMessageBox.warning(self, self.tr("경고"), self.tr("미사일 기지, 방어 자산 또는 방어 대상 자산을 선택하세요."))
                return

            self.trajectories = []
            for defense_asset_dic in selected_defense_assets:
                for enemy_base_dic in selected_enemy_bases:
                    for cal_asset_dic in selected_cal_assets:
                        try:
                            missile_mgrs_full = self.get_mgrs_from_dict(enemy_base_dic)
                            missile_lat, missile_lon = m_conv.toLatLon(missile_mgrs_full)
                            target_mgrs_full = self.get_mgrs_from_dict(cal_asset_dic)
                            target_lat, target_lon = m_conv.toLatLon(target_mgrs_full)

                            distance = self.calculate_distance(missile_lat, missile_lon, target_lat, target_lon)
                            missile_type = self.determine_missile_type(distance, enemy_base_dic.get(self.tr('발사기지')))

                            if missile_type:
                                defense_mgrs_full = self.get_mgrs_from_dict(defense_asset_dic)
                                defense_lat, defense_lon = m_conv.toLatLon(defense_mgrs_full)
                                defense_altitude = 0

                                defense_weapon = defense_asset_dic.get(self.tr('무기체계'))
                                defense_info = (defense_lat, defense_lon, defense_altitude, (self.weapon_systems_info.get(defense_weapon, {}).get('min_radius', 0), self.weapon_systems_info.get(defense_weapon, {}).get('max_radius', 0)),
                                                (self.weapon_systems_info.get(defense_weapon, {}).get('min_altitude', 0),  self.weapon_systems_info.get(defense_weapon, {}).get('max_altitude', 0)),
                                                self.weapon_systems_info.get(defense_weapon, {}).get('angle', 0))

                                trajectory = self.calculate_trajectory((missile_lat, missile_lon), (target_lat, target_lon), missile_type, defense_info)
                                if trajectory:
                                    self.trajectories.append(trajectory)

                        except ValueError as e:
                            print(self.tr(f"MGRS 변환 오류: {e}"))

            QMessageBox.information(self, self.tr("성공"), self.tr("궤적 계산이 완료되었습니다."))

        except Exception as e:
            QMessageBox.critical(self, self.tr("에러"), self.tr(f"궤적 계산 중 오류 발생: {str(e)}"))

    def determine_missile_type(self, distance, base_name):
        """거리와 기지명에 따라 미사일 종류를 결정하는 메서드"""
        available_missiles = []
        self.cursor.execute("SELECT weapon_system FROM enemy_bases_ko WHERE base_name = ?", (base_name,))
        weapons = self.cursor.fetchone()
        if weapons:
            weapons = weapons[0].split(', ')
            for missile_type, info in self.missile_info.items():
                if missile_type in weapons and int(info["min_radius"]) <= distance <= int(info["max_radius"]):
                    available_missiles.append(missile_type)
        if available_missiles:
            return random.choice(available_missiles)
        else:
            return None

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

    def calculate_trajectory(self, missile_base, target, missile_type, defense_unit):
        """미사일 궤적을 계산하는 메서드 (논문 3.1절)"""
        try:
            B_lat, B_lon = missile_base
            T_lat, T_lon = target
            K_lat, K_lon, Kz = defense_unit[:3]  # 방어 유닛 위치 (x, y, z)
            range_tuple = defense_unit[3]  # 방어 유닛 사거리 (최소, 최대)
            altitude_tuple = defense_unit[4]  # 방어 유닛 요격 고도 (최소, 최대)
            angle = defense_unit[5]  # 방어 유닛 방위각

            # 두 지점 간의 거리 계산 (km)
            L = self.calculate_distance(B_lat, B_lon, T_lat, T_lon)

            # 미사일 계수 계산
            coeff = self.missile_info[missile_type]["trajectory_coefficients"]
            alpha = coeff["alpha"]["a1"] * math.exp(coeff["alpha"]["a2"] * L) + \
                    coeff["alpha"]["b1"] * math.exp(coeff["alpha"]["b2"] * L)
            beta = coeff["beta"]["a1"] * math.exp(coeff["beta"]["a2"] * L) + \
                   coeff["beta"]["b1"] * math.exp(coeff["beta"]["b2"] * L)

            # 탄도미사일 궤적 계산
            Mz = altitude_tuple[1]  # 요격 고도 (km)
            d1 = (-beta + math.sqrt(beta ** 2 + 4 * alpha * Mz)) / (2 * alpha)
            d2 = (-beta - math.sqrt(beta ** 2 + 4 * alpha * Mz)) / (2 * alpha)

            # 방위각 계산 (라디안)
            phi = math.atan2(math.sin(math.radians(T_lon - B_lon)) * math.cos(math.radians(T_lat)),
                             math.cos(math.radians(B_lat)) * math.sin(math.radians(T_lat)) -
                             math.sin(math.radians(B_lat)) * math.cos(math.radians(T_lat)) *
                             math.cos(math.radians(T_lon - B_lon)))

            # 두 가능한 미사일 위치 계산
            def calculate_position(d):
                lat_radian = math.asin(math.sin(math.radians(B_lat)) * math.cos(d / 6371) +
                                  math.cos(math.radians(B_lat)) * math.sin(d / 6371) * math.cos(phi))
                lon_radian = math.radians(B_lon) + math.atan2(
                    math.sin(phi) * math.sin(d / 6371) * math.cos(math.radians(B_lat)),
                    math.cos(d / 6371) - math.sin(math.radians(B_lat)) * math.sin(lat_radian))
                return math.degrees(lat_radian), math.degrees(lon_radian)

            M_lat1, M_lon1 = calculate_position(d1)
            M_lat2, M_lon2 = calculate_position(d2)

            # 타겟에 더 가까운 위치 선택
            dist1 = self.calculate_distance(T_lat, T_lon, M_lat1, M_lon1)
            dist2 = self.calculate_distance(T_lat, T_lon, M_lat2, M_lon2)
            M_lat, M_lon = (M_lat1, M_lon1) if dist1 < dist2 else (M_lat2, M_lon2)

            return (missile_base, target, defense_unit, (M_lat, M_lon, Mz))

        except Exception as e:
            print(f"Error calculating trajectory: {e}")
            return None

    def calculate_engagement_zones(self):
        """방공포대 교전가능 공간을 계산하는 메서드 (논문 3.1절 기반)"""
        try:
            self.engagement_zones = {}
            for missile_base, target, defense_unit, (M_lat, M_lon, Mz) in self.trajectories:
                K_lat, K_lon, Kz = defense_unit[:3]  # 방어 유닛 위치 (x, y, z)
                range_tuple = defense_unit[3]  # 방어 유닛 사거리 (최소, 최대)
                altitude_tuple = defense_unit[4]  # 방어 유닛 요격 고도 (최소, 최대)
                angle = defense_unit[5]  # 방어 유닛 방위각

                distance = self.calculate_distance(K_lat, K_lon, M_lat, M_lon) # 방어 유닛과 미사일 간 거리 계산

                # 논문의 식 (4)~(6)을 적용하여 교전 가능성 판단
                if M_lat >= K_lat and abs(math.atan2(M_lat - K_lat, M_lon - K_lon) - math.atan2(target[0] - missile_base[0], target[1] - missile_base[1])) <= math.radians(angle / 2) and range_tuple[0] <= distance <= range_tuple[1]:
                    if defense_unit not in self.engagement_zones:
                        self.engagement_zones[defense_unit] = []
                    self.engagement_zones[defense_unit].append((M_lat, M_lon, Mz)) # 교전 가능한 경우에만 추가
            print(self.engagement_zones)
        except Exception as e:
            QMessageBox.critical(self, "에러", f"교전 가능 공간 계산 중 오류 발생: {str(e)}")

    def optimize_locations(self):
        """최적의 방공포대 위치를 선정하는 메서드 (논문 3.2절 기반 이진 정수 계획법)"""
        try:
            if not hasattr(self, 'engagement_zones'):
                self.calculate_engagement_zones()

            # 이진 정수 계획법을 위한 변수 및 제약 조건 설정
            num_defense_units = len(self.engagement_zones)  # 방어 유닛의 수
            targets = {target for _, target, _, _ in self.trajectories}  # 모든 target을 중복 없이 저장
            num_targets = len(targets)  # target의 수
            c = [1] * num_defense_units  # 목적 함수 계수 (모든 방어 유닛의 비용을 1로 가정)
            A = []  # 제약 조건의 계수 행렬
            b = []  # 제약 조건의 우변 벡터

            # 각 target에 대해 최소 하나 이상의 방어 유닛이 커버하도록 제약 조건 추가
            for target in targets:  # 중복 없이 모든 target에 대해 반복
                constraint = [0] * num_defense_units  # 현재 target에 대한 제약 조건 계수 초기화
                for i, (defense_unit, _) in enumerate(self.engagement_zones.items()):  # 모든 방어 유닛에 대해 반복
                    if any(t == target and defense == defense_unit for _, t, defense, _ in
                           self.trajectories):  # 현재 target을 현재 방어 유닛이 커버하는지 확인
                        constraint[i] = 1  # 커버하면 제약 조건 계수를 1로 설정
                A.append(constraint)  # 제약 조건 계수 행렬에 추가
                b.append(1)  # 제약 조건 우변 벡터에 1 추가 (최소 하나 이상 커버해야 함)

            # 0-1 변수 설정 (각 방어 유닛의 배치 여부를 나타내는 이진 변수)
            bounds = [(0, 1)] * num_defense_units

            # 이진 정수 계획법 해결 (scipy.optimize.linprog 사용)
            res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, integrality=[1] * num_defense_units)

            # 최적 위치 저장
            self.optimized_locations = []
            if res.success:  # 최적해를 찾았을 경우
                for i, x in enumerate(res.x):  # 각 방어 유닛에 대해 반복
                    if round(x) == 1:  # 배치 여부 변수가 1인 경우 (반올림하여 정수로 변환)
                        self.optimized_locations.append(list(self.engagement_zones.keys())[i])  # 최적 위치 목록에 추가
            else:  # 최적해를 찾지 못했을 경우
                QMessageBox.warning(self, "경고", "최적해를 찾지 못했습니다.")
                return

            QMessageBox.information(self, "성공", "위치 최적화가 완료되었습니다.")

        except Exception as e:
            QMessageBox.critical(self, "에러", f"위치 최적화 중 오류 발생: {str(e)}")

    def visualize_results(self):
        """결과를 시각화하는 메서드"""
        try:
            if not hasattr(self, 'ax'):
                figure, self.ax = plt.subplots()
                self.canvas = FigureCanvas(figure)
                self.result_window.layout().addWidget(self.canvas)
            else:
                self.ax.clear()

            # 미사일 궤적 표시
            for missile_base, target, defense_unit, (Mx, My, Mz) in self.trajectories:
                self.ax.plot([missile_base[1], target[1]], [missile_base[0], target[0]], 'r-', linewidth=0.5)
                self.ax.plot([defense_unit[1], target[1]], [defense_unit[0], target[0]], 'b-', linewidth=0.5)

            # 최적 위치 표시
            for location in self.optimized_locations:
                self.ax.plot(location[1], location[0], 'go', markersize=5)

            # 핵심 방어 시설 표시
            selected_cal_assets = self.get_selected_items(self.cal_assets_table)
            for asset in selected_cal_assets:
                lat, lon = self.get_lat_lon_from_mgrs(asset['군사좌표(MGRS)'])
                self.ax.plot(lon, lat, 'rx', markersize=3)

            # 미사일 기지 표시
            selected_enemy_bases = self.get_selected_items(self.enemy_sites_table)
            for base in selected_enemy_bases:
                lat, lon = self.get_lat_lon_from_mgrs(base['군사좌표(MGRS)'])
                self.ax.plot(lon, lat, 'k^', markersize=3)

            # 그래프 레이블 설정
            self.ax.set_xlabel(self.tr('경도'))
            self.ax.set_ylabel(self.tr('위도'))
            self.ax.set_title(self.tr('미사일 방어 시뮬레이션 결과'))

            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, self.tr("에러"), str(e))

    def run_simulation(self):
        """시뮬레이션 실행 메서드"""
        try:
            self.calculate_trajectories()
            self.calculate_engagement_zones()
            self.optimize_locations()
            self.result_window = SimulationResultWindow(self)
            self.visualize_results()  # ax 인자 제거
            self.result_window.canvas.draw()
            self.result_window.show()
        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"시뮬레이션 실행 오류: {e}"))


    def get_mgrs_from_dict(self, data_dict):
        try:
            mgrs = data_dict.get(self.tr('군사좌표(MGRS)'), '')
            if not mgrs:
                raise ValueError(self.tr("MGRS 데이터가 없습니다."))

            # 공백 제거 및 구성 요소 분리
            mgrs_parts = mgrs.replace(' ', '')

            # MGRS 문자열의 길이 확인
            if len(mgrs_parts) != 15:
                raise ValueError(self.tr("MGRS 데이터 형식이 올바르지 않습니다."))

            zone = mgrs_parts[:3]
            square = mgrs_parts[3:5]
            easting = mgrs_parts[5:10]
            northing = mgrs_parts[10:]

            # 구성 요소 검증
            if not zone[0:2].isdigit() or not zone[2].isalpha():
                raise ValueError(self.tr("잘못된 MGRS zone 형식입니다."))
            if not square.isalpha():
                raise ValueError(self.tr("잘못된 MGRS square 형식입니다."))
            if not easting.isdigit() or not northing.isdigit():
                raise ValueError(self.tr("잘못된 MGRS easting 또는 northing 형식입니다."))

            return f'{zone}{square}{easting}{northing}'
        except (TypeError, ValueError) as e:
            raise ValueError(self.tr(f"MGRS 데이터 오류: {e}"))

    @staticmethod
    def get_lat_lon_from_mgrs(mgrs_string):
        """MGRS 좌표를 위도와 경도로 변환하는 메서드"""
        m_conv = mgrs.MGRS()
        # 공백 제거 및 구성 요소 분리
        mgrs_parts = mgrs_string.replace(' ', '')
        lat, lon = m_conv.toLatLon(mgrs_parts)
        return lat, lon

    def get_selected_items(self, table):
        selected_items = []
        for row in range(table.rowCount()):
            if table.cellWidget(row, 0).isChecked():
                row_data = {}
                for col in range(1, table.columnCount()):  # 체크박스 열 제외
                    header = table.horizontalHeaderItem(col).text()
                    row_data[header] = table.item(row, col).text()
                selected_items.append(row_data)
        return selected_items

class SimulationResultWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("시뮬레이션 결과"))
        layout = QVBoxLayout()
        self.figure = plt.Figure(figsize=(5, 3))  # Figure 객체 생성
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.ax = self.figure.subplots()
        self.setLayout(layout)

        # 폰트 설정
        self.ax.set_xlabel(self.tr('경도'), fontname='Malgun Gothic')
        self.ax.set_ylabel(self.tr('위도'), fontname='Malgun Gothic')
        self.ax.set_title(self.tr('미사일 방어 시뮬레이션 결과'), fontname='Malgun Gothic')

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


