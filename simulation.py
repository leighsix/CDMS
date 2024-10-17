import sys
import sqlite3
import csv, json, re
import random
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QHBoxLayout, QSplitter, QComboBox, QLineEdit, QTableWidget, QPushButton, QLabel,
                             QGroupBox, QCheckBox, QHeaderView, QDialog, QTableWidgetItem)
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
from simulation_map_view import SimulationCalMapView, SimulationWeaponMapView, SimulationEnemyBaseWeaponMapView
from setting import MapApp
import mgrs
import io
from PyQt5 import QtWidgets, QtGui
import pandas as pd
from scipy.optimize import linprog
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import folium
from branca.element import Figure
import os
import numpy as np
import math
from geopy import distance
from geopy.point import Point
from simplification.cutil import simplify_coords


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
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
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
                self.cal_df_ko = pd.DataFrame(columns=["id", "priority", "unit", "target_asset", "area", "coordinate", "mgrs", "criticality", "vulnerability", "threat", "bonus", "total_score"])
                self.cal_df_en = pd.DataFrame(columns=["id", "priority", "unit", "target_asset", "area", "coordinate", "mgrs", "criticality", "vulnerability", "threat", "bonus", "total_score"])


            try:
                query = "SELECT * FROM dal_assets_priority_ko"
                self.dal_df_ko = pd.read_sql_query(query, conn,)
                query = "SELECT * FROM dal_assets_priority_en"
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
        self.analyze_trajectories_button = QPushButton(self.tr("미사일 궤적 분석"))
        self.analyze_trajectories_button.clicked.connect(self.run_trajectory_analysis)
        simulate_button_layout.addWidget(self.analyze_trajectories_button)

        # 최적 방공포대 위치 산출 버튼
        self.optimize_locations_button = QPushButton(self.tr("최적 방공포대 위치 산출"))
        self.optimize_locations_button.clicked.connect(self.run_location_optimization)
        simulate_button_layout.addWidget(self.optimize_locations_button)

        center_layout.addLayout(simulate_button_layout)

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
                (filtered_df['target_asset'].str.contains(search_filter_text, case=False)) |
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
            for col, value in enumerate(base[['unit', 'area', 'target_asset', 'weapon_system', 'threat_degree',
                                              'ammo_count', 'coordinate', 'mgrs']], start=1):
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
            SimulationCalMapView(selected_assets, self.map)
        if selected_defense_assets:
            SimulationWeaponMapView(selected_defense_assets, self.show_defense_radius, self.map)
        if selected_enemy_bases:
            SimulationEnemyBaseWeaponMapView(selected_enemy_bases, self.show_threat_radius, self.map)

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
        """미사일 궤적을 계산하는 메서드 (수정됨)"""
        try:
            selected_enemy_bases = self.get_selected_items(self.enemy_sites_table)
            selected_defense_assets = self.get_selected_items(self.defense_assets_table)
            selected_cal_assets = self.get_selected_items(self.cal_assets_table)
            if not selected_enemy_bases or not selected_cal_assets:
                QMessageBox.warning(self, self.tr("경고"), self.tr("미사일 기지 또는 방어 대상 자산을 선택하세요."))
                return

            self.trajectories = []
            self.defense_trajectories = []
            for enemy_base_dic in selected_enemy_bases:
                for cal_asset_dic in selected_cal_assets:
                    try:
                        base_name = enemy_base_dic.get(self.tr('발사기지'))
                        missile_lat, missile_lon = self.parse_coordinates(enemy_base_dic.get('경위도'))
                        target_name = cal_asset_dic.get(self.tr('방어대상자산'))
                        target_lat, target_lon = self.parse_coordinates(cal_asset_dic.get('경위도'))

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
                                if selected_defense_assets:
                                    for defense_asset_dic in selected_defense_assets:
                                        defense_name = defense_asset_dic.get(self.tr('방어자산명'))
                                        defense_lat, defense_lon = self.parse_coordinates(defense_asset_dic.get('경위도'))
                                        weapon_type = defense_asset_dic.get(self.tr('무기체계'))
                                        threat_azimuth =  int(defense_asset_dic.get(self.tr('위협방위')))
                                        if self.check_engagement_possibility(defense_lat, defense_lon, weapon_type,
                                                                             trajectory, threat_azimuth):
                                            defense_result = {
                                                'base_name': base_name,
                                                'base_coordinate': (missile_lat, missile_lon),
                                                'target_name': target_name,
                                                'target_coordinate': (target_lat, target_lon),
                                                'defense_name' : defense_name,
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
        selected_defense_assets = self.get_selected_defense_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        if selected_assets:
            CommonCalMapView(selected_assets, self.map)
        if selected_defense_assets:
            CommonWeaponMapView(selected_defense_assets, self.show_defense_radius, self.map)
        if selected_enemy_bases:
            EnemyBaseWeaponMapView(selected_enemy_bases, self.show_threat_radius, self.map)

        # 궤적을 지도에 추가합니다.
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
                # 그룹의 대표 궤적 선택
                representative_trajectory = trajectories[0]
                points = [(float(lat), float(lon)) for lat, lon, _ in representative_trajectory]

                # 궤적 간소화
                simplified_points = simplify_coords(points, 0.001)

                # 방어 가능한 궤적 여부 확인
                is_defended = self.is_trajectory_defended(representative_trajectory)

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

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

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

        for M_lat, M_lon, Mz in trajectory:
            distance = self.calculate_distance(defense_lat, defense_lon, M_lat, M_lon)  # 방어 유닛과 미사일 간 거리 계산

            # 미사일의 방위각 계산
            missile_azimuth = math.atan2(M_lat - defense_lat, M_lon - defense_lon)

            # 위협방위와의 각도 차이 계산
            azimuth_diff = abs(missile_azimuth - math.radians(threat_azimuth))

            # 논문의 식 (4)~(6)을 적용하여 교전 가능성 판단
            if (azimuth_diff <= math.radians(angle / 2) or azimuth_diff >= math.radians(360 - angle / 2)) and \
                    range_tuple[0] <= distance <= range_tuple[1] and \
                    altitude_tuple[0] <= Mz <= altitude_tuple[1]:
                return True  # 교전 가능한 경우 True 반환

        return False  # 궤적 전체에서 방어 가능한 지점이 없는 경우 False 반환

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

    def update_map_with_optimized_locations(self):
        """미사일 궤적, 방어 궤적, 격자, 최적 위치를 지도에 표시하는 메서드"""
        # 새로운 지도 객체를 생성합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        # 선택된 자산, 방어 자산, 적 기지를 지도에 추가합니다.
        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_defense_assets()
        selected_enemy_bases = self.get_selected_enemy_bases()
        if selected_assets:
            CommonCalMapView(selected_assets, self.map)
        if selected_defense_assets:
            CommonWeaponMapView(selected_defense_assets, self.show_defense_radius, self.map)
        if selected_enemy_bases:
            EnemyBaseWeaponMapView(selected_enemy_bases, self.show_threat_radius, self.map)

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

    def optimize_locations(self):
        try:
            # 방어 시스템의 교전 구역 계산
            self.calculate_engagement_zones()

            # 후보 방어 위치 목록 생성 (중복 제거)
            candidate_locations = list(set([zone['defense_name'] for zone in self.engagement_zones]))
            num_candidate_locations = len(candidate_locations)

            # 목표물 위치 목록 생성 (중복 제거)
            bases = set([(zone['base_name'], zone['base_coordinate']) for zone in self.engagement_zones])
            num_bases = len(bases)

            # 목표물 위치 목록 생성 (중복 제거)
            targets = set([(zone['target_name'], zone['target_coordinate']) for zone in self.engagement_zones])
            num_targets = len(targets)

            # 목적 함수: 각 위치의 비용을 1로 가정하고 총 비용 최소화
            c = np.ones(num_candidate_locations)

            # 제약 조건 행렬(A)과 벡터(b) 초기화
            A = []
            b = []

            # 각 목표물에 대한 제약 조건 생성
            for target in targets:
                for base in bases:
                    constraint = [0] * num_candidate_locations
                    for i, location in enumerate(candidate_locations):
                        # 현재 위치가 해당 목표물을 방어할 수 있는지 확인
                        if any(zone['defense_name'] == location and
                                # zone['base_name'] == base[0] and
                                # zone['base_coordinate'] == base[1] and
                                zone['target_name'] == target[0] and
                                zone['target_coordinate'] == target[1]
                            for zone in self.engagement_zones):
                            constraint[i] = 1
                    A.append(constraint)
                    b.append(1)  # 각 목표물은 최소 1개의 방어 시스템으로 방어되어야 함

            # NumPy 배열로 변환
            A = np.array(A)
            b = np.array(b)

            # 각 변수(위치)의 범위 설정: 0(미선택) 또는 1(선택)
            bounds = [(0, 1)] * num_candidate_locations

            # 선형 계획법 문제 해결
            # A와 b를 음수로 변환하여 '이상' 제약 조건을 '이하' 제약 조건으로 변경
            res = linprog(c, A_ub=-A, b_ub=-b, bounds=bounds, method='highs')

            self.optimized_locations = []
            if res.success:
                # 최적화 결과 처리
                for i, x in enumerate(res.x):
                    if x > 0.5:  # 0.5 초과 값을 가진 위치를 선택 (반올림 효과)
                        optimal_location = candidate_locations[i]
                        # 선택된 위치에 해당하는 모든 교전 구역 추가
                        optimal_zones = [zone for zone in self.engagement_zones if
                                         zone['defense_name'] == optimal_location]
                        self.optimized_locations.extend(optimal_zones)
            else:
                # 최적해를 찾지 못한 경우 경고 메시지 표시
                QMessageBox.warning(self, self.tr("경고"), self.tr("최적해를 찾지 못했습니다."))
                return

        except Exception as e:
            # 오류 발생 시 에러 메시지 표시
            QMessageBox.critical(self, self.tr("에러"), self.tr(f"위치 최적화 중 오류 발생: {str(e)}"))
            return

    def run_location_optimization(self):
        """최적 방공포대 위치 산출 실행 메서드"""
        try:
            self.calculate_trajectories()
            self.optimize_locations()

            if not hasattr(self, 'optimized_locations') or not self.optimized_locations:
                QMessageBox.warning(self, "경고", "최적화된 위치가 없습니다.")
                return

            # 결과 테이블 업데이트
            self.result_table.setRowCount(0)  # 기존 행 모두 제거
            self.result_table.setColumnCount(4)
            self.result_table.setHorizontalHeaderLabels(["최적 위치", "방어 가능 자산", "무기 유형", "위협 방위각"])
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.result_table.verticalHeader().setVisible(False)

            defensible_assets = {}
            for optimized_location in self.optimized_locations:
                temp_defense_name = optimized_location.get('defense_name')
                target_name = optimized_location.get('target_name')
                weapon_type = optimized_location.get('weapon_type')
                threat_azimuth = optimized_location.get('threat_azimuth')

                if temp_defense_name not in defensible_assets:
                    defensible_assets[temp_defense_name] = {
                        'assets': set(),
                        'weapons': set(),
                        'azimuths': set()
                    }
                defensible_assets[temp_defense_name]['assets'].add(target_name)
                defensible_assets[temp_defense_name]['weapons'].add(weapon_type)
                defensible_assets[temp_defense_name]['azimuths'].add(str(threat_azimuth))

            for temp_defense_name, data in defensible_assets.items():
                row_position = self.result_table.rowCount()
                self.result_table.insertRow(row_position)
                self.result_table.setItem(row_position, 0, QTableWidgetItem(temp_defense_name))
                self.result_table.setItem(row_position, 1, QTableWidgetItem(', '.join(sorted(data['assets']))))
                self.result_table.setItem(row_position, 2, QTableWidgetItem(', '.join(sorted(data['weapons']))))
                self.result_table.setItem(row_position, 3, QTableWidgetItem(', '.join(sorted(data['azimuths']))))

            # 지도 업데이트
            self.update_map_with_optimized_locations()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"최적 방공포대 위치 산출 오류: {e}"))

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

    def find_intercept_point(self, defense_tr_dic):
        """방어 가능한 교전 지점을 찾는 메서드"""
        defense_lat, defense_lon = defense_tr_dic['defense_coordinate']
        trajectory = defense_tr_dic['trajectory']
        weapon_type = defense_tr_dic['weapon_type']
        defense_altitude_range = (self.weapon_systems_info[weapon_type].get('min_altitude'), self.weapon_systems_info[weapon_type].get('max_altitude'))
        defense_range = (self.weapon_systems_info[weapon_type].get('min_radius'), self.weapon_systems_info[weapon_type].get('max_radius'))

        for point in trajectory:
            lat, lon, altitude = point
            distance = self.calculate_distance(defense_lat, defense_lon, lat, lon)
            if (defense_range[0] <= distance <= defense_range[1] and
                    defense_altitude_range[0] <= altitude <= defense_altitude_range[1]):
                return lat, lon, altitude

        return None

    @staticmethod
    def on_map_load_finished(result):
        if result:
            print("지도가 성공적으로 로드되었습니다.")
        else:
            print("지도 로딩에 실패했습니다.")

    @staticmethod
    def get_selected_items(table):
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
        self.parent = parent
        self.setWindowTitle(self.tr("시뮬레이션 결과"))
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        # Folium 맵을 표시할 QWebEngineView 생성
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # MissileDefenseApp에서 필요한 속성들을 가져옵니다
        self.trajectories = self.parent.trajectories
        self.optimized_locations = self.parent.optimized_locations
        self.cal_assets_table = self.parent.cal_assets_table
        self.enemy_sites_table = self.parent.enemy_sites_table
        self.get_selected_items = self.parent.get_selected_items
        self.get_lat_lon_from_mgrs = self.parent.get_lat_lon_from_mgrs

class MissileTrajectoryCalculator:
    def __init__(self):
        self.EARTH_RADIUS = 6371  # 지구 반지름 (km)
        self.G = 9.81  # 중력 가속도 (m/s^2)

        with open('missile_info.json', 'r', encoding='utf-8') as f:
            self.missile_info = json.load(f)

    def calculate_trajectory(self, missile_base, target, missile_type):
        B_lat, B_lon = missile_base
        T_lat, T_lon = target

        L = self.calculate_distance(B_lat, B_lon, T_lat, T_lon)

        # 미사일 타입에 따른 계수 선택
        coeffs = self.missile_info[missile_type]['trajectory_coefficients']

        # 논문 3.1절의 계산식 사용
        alpha = coeffs['alpha']['a1'] * L + coeffs['alpha']['a2']
        beta = coeffs['beta']['a1'] * L + coeffs['beta']['b1']

        try:
            x, y, z = self.calculate_ballistic_trajectory(L, alpha, beta)
            bearing = self.calculate_bearing(B_lat, B_lon, T_lat, T_lon)
            trajectory = self.convert_trajectory_to_coordinates(B_lat, B_lon, T_lat, T_lon, bearing, x, y, z)

            return trajectory

        except Exception as e:
            print(f"궤적 계산 중 오류 발생: {e}")
            return None

    @staticmethod
    def calculate_ballistic_trajectory(distance, alpha, beta):
        t = np.linspace(0, 1, 1000)
        x = distance * t
        y = alpha * x * (1 - x / distance) + beta * x * (1 - x / distance) * (x / distance)
        y = y / 1000  # Convert meters to kilometers
        z = np.zeros_like(x)
        return x, y, z

    def convert_trajectory_to_coordinates(self, start_lat, start_lon, end_lat, end_lon, bearing, x, y, z):
        trajectory = []
        start = Point(start_lat, start_lon)

        for i in range(len(x)):
            point = self.calculate_point_at_distance_and_bearing(start, x[i], bearing)
            if point:
                trajectory.append((point[0], point[1], y[i]))  # y is already in km

        if trajectory:
            trajectory[-1] = (end_lat, end_lon, 0)

        return trajectory

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        return distance.great_circle((lat1, lon1), (lat2, lon2)).km

    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        initial_bearing = math.atan2(y, x)
        return math.degrees(initial_bearing)

    def calculate_point_at_distance_and_bearing(self, start, distance, bearing):
        start_lat = math.radians(start.latitude)
        start_lon = math.radians(start.longitude)
        bearing = math.radians(bearing)
        angular_distance = distance / self.EARTH_RADIUS

        end_lat = math.asin(
            math.sin(start_lat) * math.cos(angular_distance) +
            math.cos(start_lat) * math.sin(angular_distance) * math.cos(bearing)
        )

        cos_end_lat = math.cos(end_lat)
        if abs(cos_end_lat) < 1e-10:
            return None

        end_lon = start_lon + math.atan2(
            math.sin(bearing) * math.sin(angular_distance) * math.cos(start_lat),
            math.cos(angular_distance) - math.sin(start_lat) * math.sin(end_lat)
        )

        return math.degrees(end_lat), math.degrees(end_lon)


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


