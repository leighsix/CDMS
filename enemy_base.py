import sys
import sqlite3
import folium
import sys, io
import re, mgrs
import pandas as pd
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QMainWindow, QStackedWidget, QMessageBox,
                             QComboBox, QLineEdit, QFormLayout, QGroupBox,
                             QCheckBox, QHeaderView, QDialog, QApplication)
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtCore import QUrl, QSize, QTimer, QTemporaryFile, QDir, QEventLoop, QDateTime
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
from addasset import AutoSpacingLineEdit, UnderlineEdit
from setting import MapApp
from enemy_map_view import EnemyBaseMapView, EnemyWeaponMapView

class EnemyBaseInputDialog(QDialog):
    def __init__(self, parent, edit_mode=False, enemy_data=None):
        super(EnemyBaseInputDialog, self).__init__(parent)
        self.parent = parent
        self.edit_mode = edit_mode
        self.enemy_data = enemy_data
        self.setWindowTitle(self.tr("적 미사일 발사기지 입력"))
        self.setMinimumSize(800, 600)
        self.enemy_id = None
        self.enemy_base_fields = {}
        self.initUI()

    def initUI(self):
        # 메인 레이아웃 설정
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 적 미사일 기지 정보를 위한 그룹박스 생성
        enemy_base_group = QGroupBox(self.tr("적 미사일 기지 정보"))
        enemy_base_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        enemy_base_layout = QVBoxLayout(enemy_base_group)

        # 스크롤 영역 생성
        self.enemy_base_scroll = QScrollArea()
        self.enemy_base_scroll.setWidgetResizable(True)
        enemy_base_container = QWidget()
        enemy_base_layout_main = QGridLayout(enemy_base_container)
        enemy_base_layout_main.setVerticalSpacing(20)
        enemy_base_layout_main.setColumnStretch(1, 1)

        # 레이블 및 입력 필드 정의
        labels = [
            (self.tr("기지명"), self.tr("(영문)")),
            (self.tr("지역"), self.tr("(영문)")),
            (self.tr("위도"), self.tr("경도")),
            self.tr("군사좌표(MGRS)"),
            self.tr("무기체계")
        ]

        # 필드를 저장할 딕셔너리 초기화
        self.enemy_base_fields = {}

        row = 0  # 행 번호 초기화
        for label in labels:
            hbox = QHBoxLayout()  # 수평 레이아웃 생성

            if isinstance(label, tuple):  # 레이블이 튜플인 경우 (예: 기지명과 영문)
                label_widget = QLabel(label[0])
                sub_label_widget = QLabel(label[1])
                input_widgets = []

                for i, sub_label in enumerate(label):
                    if label == (self.tr("위도"), self.tr("경도")):
                        input_widget = CoordinateEdit(sub_label)
                        input_widget.editingFinished.connect(self.convert_to_mgrs)
                    else:
                        input_widget = UnderlineEdit()
                    input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    input_widgets.append(input_widget)

                hbox.addWidget(label_widget)
                hbox.addWidget(input_widgets[0])
                hbox.addWidget(sub_label_widget)
                hbox.addWidget(input_widgets[1])

                self.enemy_base_fields[label] = tuple(input_widgets)

                # 레이블 위젯 스타일 설정
                for widget in [label_widget, sub_label_widget]:
                    widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
                    widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                    widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    widget.setFixedWidth(75)

            else:  # 레이블이 단일 문자열인 경우
                label_widget = QLabel(label)
                if label == self.tr("군사좌표(MGRS)"):
                    input_widget = AutoSpacingLineEdit()
                    input_widget.setPlaceholderText("99A AA 99999 99999")
                elif label == self.tr("무기체계"):
                    self.weapon_system_input = QWidget()
                    weapon_layout = QHBoxLayout(self.weapon_system_input)
                    self.weapon_checkboxes = []
                    weapon_systems = ["Scud-B", "Scud-C", "Nodong"]
                    for system in weapon_systems:
                        checkbox = QCheckBox(system)
                        checkbox.setStyleSheet("font: 바른공군체; font-size: 13pt;")
                        self.weapon_checkboxes.append(checkbox)
                        weapon_layout.addWidget(checkbox)
                    self.weapon_system_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    input_widget = self.weapon_system_input
                else:
                    input_widget = UnderlineEdit()

                input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")

                hbox.addWidget(label_widget)
                hbox.addWidget(input_widget)

                self.enemy_base_fields[label] = input_widget

            # 레이블 위젯 스타일 설정
            label_widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
            label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label_widget.setFixedWidth(150)

            # 메인 레이아웃에 수평 레이아웃 추가
            enemy_base_layout_main.addLayout(hbox, row, 0, 1, 4)
            row += 1

        # 레이아웃 설정
        enemy_base_layout_main.setColumnStretch(0, 0)
        enemy_base_layout_main.setColumnStretch(1, 1)
        enemy_base_layout_main.setRowStretch(len(labels) - 1, 1)

        # 스크롤 영역에 위젯 설정
        self.enemy_base_scroll.setWidget(enemy_base_container)
        enemy_base_layout.addWidget(self.enemy_base_scroll)
        layout.addWidget(enemy_base_group)

        # 저장 버튼 생성 및 설정
        self.save_button = QPushButton(self.tr("저장"))
        self.save_button.clicked.connect(self.save_data)
        self.save_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold; padding: 10px;")
        self.save_button.setFixedSize(150, 50)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 메인 레이아웃 설정
        self.setLayout(layout)

        # 창 제목 및 아이콘 설정
        if self.edit_mode:
            self.setWindowTitle(self.tr("적 미사일 기지 정보 수정"))
            self.setWindowIcon(QIcon("logo.png"))
            if hasattr(self, 'enemy_data') and self.enemy_data:
                self.populate_fields()
        else:
            self.setWindowTitle(self.tr("적 미사일 기지 정보 입력"))
            self.setWindowIcon(QIcon("logo.png"))

    def convert_to_mgrs(self):
        lat_widget, lon_widget = self.enemy_base_fields[(self.tr("위도"), self.tr("경도"))]
        lat_input = lat_widget.text()
        lon_input = lon_widget.text()

        try:
            lat = float(lat_input[1:])  # 'N' 또는 'S' 제거
            lon = float(lon_input[1:])  # 'E' 또는 'W' 제거

            if lat_input.startswith('S'):
                lat = -lat
            if lon_input.startswith('W'):
                lon = -lon

            m = mgrs.MGRS()
            mgrs_coord = m.toMGRS(lat, lon)
            self.enemy_base_fields[self.tr("군사좌표(MGRS)")].setText(mgrs_coord)
        except ValueError as e:
            print(f"좌표 변환 오류: {e}")

    def save_data(self):
        try:
            # 선택된 무기체계 가져오기
            selected_weapons = [checkbox.text() for checkbox in self.weapon_checkboxes if checkbox.isChecked()]
            weapon_system = ", ".join(selected_weapons)  # 선택된 무기체계를 쉼표로 구분된 문자열로 변환
            enemy_data = {}
            for label, field in self.enemy_base_fields.items():
                if isinstance(field, QTextEdit):
                    enemy_data[label] = field.toPlainText().strip()
                elif isinstance(field, QLineEdit):
                    enemy_data[label] = field.text().strip()
                elif isinstance(field, tuple):
                    enemy_data[label] = tuple(
                        f.text().strip() if isinstance(f, QLineEdit) else f.toPlainText().strip() for f in field)

            # 새로운 형식으로 변경
            lat_lon_key = (self.tr("위도"), self.tr("경도"))
            lat, lon = enemy_data[lat_lon_key]
            lat_lon = f"{lat},{lon}"

            try:
                cursor = self.parent.parent.conn.cursor()
                if self.edit_mode:
                    cursor.execute(
                        "UPDATE enemy_bases_ko SET base_name=?, area=?, coordinate=?, mgrs=?, weapon_system=? WHERE id=?",
                        (enemy_data[(self.tr("기지명"), self.tr("(영문)"))][0],
                         enemy_data[(self.tr("지역"), self.tr("(영문)"))][0], lat_lon,
                         enemy_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, self.enemy_id)
                    )

                    cursor.execute(
                        "UPDATE enemy_bases_en SET base_name=?, area=?, coordinate=?, mgrs=?, weapon_system=? WHERE id=?",
                        (enemy_data[(self.tr("기지명"), self.tr("(영문)"))][1],
                         enemy_data[(self.tr("지역"), self.tr("(영문)"))][1], lat_lon,
                         enemy_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, self.enemy_id)
                    )
                else:
                    cursor.execute("SELECT MAX(id) FROM enemy_bases_ko")
                    max_id = cursor.fetchone()[0]
                    new_id = 1 if max_id is None else max_id + 1
                    cursor.execute(
                        "INSERT INTO enemy_bases_ko (id, base_name, area, coordinate, mgrs, weapon_system) VALUES (?, ?, ?, ?, ?, ?)",
                        (new_id, enemy_data[(self.tr("기지명"), self.tr("(영문)"))][0],
                         enemy_data[(self.tr("지역"), self.tr("(영문)"))][0], lat_lon,
                         enemy_data[self.tr("군사좌표(MGRS)")], weapon_system))
                    cursor.execute(
                        "INSERT INTO enemy_bases_en (id, base_name, area, coordinate, mgrs, weapon_system) VALUES (?, ?, ?, ?, ?, ?)",
                        (new_id, enemy_data[(self.tr("기지명"), self.tr("(영문)"))][1],
                         enemy_data[(self.tr("지역"), self.tr("(영문)"))][1], lat_lon,
                         enemy_data[self.tr("군사좌표(MGRS)")], weapon_system))
                self.parent.parent.conn.commit()
                self.accept()
                if self.edit_mode:
                    QMessageBox.information(self, self.tr("성공"), self.tr("적 기지 정보가 성공적으로 수정되었습니다."))
                else:
                    QMessageBox.information(self, self.tr("성공"), self.tr("적 기지 정보가 성공적으로 저장되었습니다."))
            except sqlite3.Error as e:
                QMessageBox.critical(self, self.tr("오류"), self.tr(f"데이터베이스 오류: {e}"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("오류"), self.tr(f"예기치 않은 오류 발생: {e}"))
        finally:
            self.parent.load_all_enemy_bases()

    def populate_fields(self):
        if self.enemy_data:
            self.enemy_id = self.enemy_data[0]
            cursor = self.parent.parent.conn.cursor()
            cursor.execute(f"SELECT * FROM enemy_bases_en WHERE id = ?", (self.enemy_id,))
            enemy_data2 = cursor.fetchone()
            coord_str = self.enemy_data[3]
            lat, lon = coord_str.split(',')
            for label, field in self.enemy_base_fields.items():
                if isinstance(field, tuple):
                    if label == (self.tr("기지명"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(self.enemy_data[1])
                        f2.setText(str(enemy_data2[1]))
                    elif label == (self.tr("지역"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(str(self.enemy_data[2]))
                        f2.setText(str(enemy_data2[2]))
                    elif label == (self.tr("위도"), self.tr("경도")):
                        f1, f2 = field
                        f1.setText(lat)
                        f2.setText(lon)

                else:
                    if label == self.tr("군사좌표(MGRS)"):
                        field.setText(self.enemy_data[4])
                    elif label == self.tr("무기체계"):
                        stored_weapons = self.enemy_data[5].split(", ")
                        for checkbox in self.weapon_checkboxes:
                            checkbox.setChecked(checkbox.text() in stored_weapons)

class EnemyBaseWindow(QDialog):
    def __init__(self, parent):
        super(EnemyBaseWindow, self).__init__(parent)
        self.parent = parent
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.setWindowTitle("적 미사일 발사기지 정보")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.initUI()
        self.load_all_enemy_bases()
        self.show_threat_radius = False
        self.update_map()  # 초기 지도 로드

    def load_all_enemy_bases(self):
        query = f"SELECT id, base_name, area, coordinate, mgrs, weapon_system FROM enemy_bases_{self.parent.selected_language}"
        cursor = self.parent.cursor
        cursor.execute(query, )
        enemy_bases = cursor.fetchall()

        self.enemy_base_table.setRowCount(len(enemy_bases))
        for row_idx, enemy_base in enumerate(enemy_bases):
            checkbox_widget = CenteredCheckBox()
            self.enemy_base_table.setCellWidget(row_idx, 0, checkbox_widget)
            checkbox_widget.checkbox.stateChanged.connect(self.update_map)


            for col_idx, item in enumerate(enemy_base[1:], start=1):  # id 열 제외
                table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.enemy_base_table.setItem(row_idx, col_idx, table_item)

            # id를 첫 번째 열의 UserRole에 저장
            self.enemy_base_table.item(row_idx, 1).setData(Qt.UserRole, enemy_base[0])
        self.enemy_base_table.setColumnHidden(4, True)

    def refresh(self):
        # 데이터프레임 다시 로드
        self.load_all_enemy_bases()

        # 필터 초기화
        self.search_filter.clear()  # 검색창 초기화

        # 테이블의 모든 체크박스 해제
        self.enemy_base_table.uncheckAllRows()
        for weapon_system, checkbox in self.enemy_weapon_system_checkboxes.items():
            if checkbox.isChecked():
                checkbox.setChecked(False)
        self.radius_checkbox.setChecked(False)

        # 테이블 데이터 다시 로드
        self.load_enemy_bases()

        # 지도 업데이트
        self.update_map()

    def initUI(self):
        main_layout = QHBoxLayout()

        # QSplitter 생성
        splitter = QSplitter(Qt.Horizontal)

        # 좌측 레이아웃 (필터 및 테이블)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 필터 추가
        self.filter_layout = QHBoxLayout()

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText(self.tr("기지명 또는 지역 검색"))
        self.search_filter.textChanged.connect(self.load_enemy_bases)
        self.filter_layout.addWidget(self.search_filter)

        self.display_count_combo = QComboBox()
        self.display_count_combo.addItems(["30", "50", "100"])
        self.display_count_combo.currentTextChanged.connect(self.load_enemy_bases)
        self.filter_layout.addWidget(self.display_count_combo)
        left_layout.addLayout(self.filter_layout)

        # 테이블
        self.enemy_base_table = MyTableWidget()
        self.enemy_base_table.setColumnCount(6)
        self.enemy_base_table.setHorizontalHeaderLabels(
            ["", self.tr("기지명"), self.tr("지역"), self.tr("경위도"), self.tr("군사좌표(MGRS"), self.tr("무기체계")])

        # 행 번호 숨기기
        self.enemy_base_table.verticalHeader().setVisible(False)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.enemy_base_table.horizontalHeader().setFont(font)
        header = self.enemy_base_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setMinimumSectionSize(80)  # 최소 열 너비 설정
        header.resizeSection(0, 30)


        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.enemy_base_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(1, header.count()):
            self.enemy_base_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        left_layout.addWidget(self.enemy_base_table)

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


        self.enemy_base_input_button = QPushButton(self.tr("적 기지 입력"), self)
        self.correction_button = QPushButton(self.tr("수정"), self)
        self.delete_button = QPushButton(self.tr("삭제"), self)
        self.return_button = QPushButton(self.tr("메인화면"), self)
        self.enemy_base_input_button.clicked.connect(self.add_enemy_base)
        self.correction_button.clicked.connect(self.correct_enemy_base)
        self.delete_button.clicked.connect(self.delete_enemy_base)
        self.return_button.clicked.connect(self.parent.show_main_page)

        # 각 버튼에 폰트 적용
        button_layout = QHBoxLayout()
        button_layout.setSpacing(1)
        button_layout.setContentsMargins(0, 1, 0, 1)
        for button in [self.enemy_base_input_button, self.correction_button,
                       self.delete_button, self.return_button]:
            button.setFont(QFont("강한공군체", 13, QFont.Bold))
            button.setFixedSize(120, 40)
            button.setStyleSheet("QPushButton { text-align: center; }")
        button_layout.addWidget(self.enemy_base_input_button)
        button_layout.addWidget(self.correction_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.return_button)

        left_layout.addLayout(button_layout)  # addWidget 대신 addLayout 사용


        # 우측 레이아웃 (지도 및 체크박스)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 무기체계 체크박스 그룹
        weapon_group = QGroupBox(self.tr("무기체계"))
        weapon_layout = QHBoxLayout()
        weapon_layout.setContentsMargins(10, 5, 10, 5)  # 여백 조정
        weapon_layout.setSpacing(10)  # 체크박스 간 간격 조정
        self.enemy_weapon_system_checkboxes = {}
        enemy_weapon_system = ["Scud-B", "Scud-C", "Nodong"]
        for weapon in enemy_weapon_system:
            checkbox = QCheckBox(weapon)
            checkbox.stateChanged.connect(self.update_map)
            self.enemy_weapon_system_checkboxes[weapon] = checkbox
            weapon_layout.addWidget(checkbox)
        weapon_group.setLayout(weapon_layout)
        weapon_group.setFixedHeight(weapon_layout.sizeHint().height() + 20)  # 높이 조정
        right_layout.addWidget(weapon_group)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        checkbox_button_layout = QHBoxLayout()

        # 방어반경 표시 체크박스
        self.radius_checkbox = QCheckBox(self.tr("위협반경 표시"), self)
        self.radius_checkbox.stateChanged.connect(self.toggle_threat_radius)
        checkbox_button_layout.addWidget(self.radius_checkbox)

        # 지도 출력 버튼
        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.setFixedSize(230, 50)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        checkbox_button_layout.addWidget(self.print_button, alignment=Qt.AlignRight)

        # 수평 레이아웃을 right_layout에 추가
        right_layout.addLayout(checkbox_button_layout)
        # 위젯들을 QSplitter에 추가
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        # QSplitter를 메인 레이아웃에 추가
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)
        # 초기 분할 비율 설정 (1:3)
        splitter.setSizes([100, 300])

        # 지도 뷰
        self.map_view = QWebEngineView()
        right_layout.addWidget(self.map_view)

        self.load_enemy_bases()

    def toggle_threat_radius(self, state):
        self.show_threat_radius = state == Qt.Checked
        self.update_map()

    def load_enemy_bases(self):
        search_text = self.search_filter.text()
        query = f"""
                SELECT id, base_name, area, coordinate, mgrs, weapon_system 
                FROM enemy_bases_{self.parent.selected_language}
                WHERE 1=1
                """
        params = []

        if search_text:
            query += """ AND (
                base_name LIKE ? OR
                area LIKE ? OR
                coordinate LIKE ? OR
                weapon_system LIKE ?
            )"""
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param, search_param, search_param])

        query += " LIMIT ? OFFSET ?"
        rows_per_page = int(self.display_count_combo.currentText())
        offset = (self.current_page - 1) * rows_per_page
        params.extend([rows_per_page, offset])

        cursor = self.parent.cursor
        cursor.execute(query, params)
        enemy_bases = cursor.fetchall()

        self.enemy_base_table.setRowCount(len(enemy_bases))
        for row_idx, enemy_base in enumerate(enemy_bases):
            checkbox_widget = CenteredCheckBox()
            self.enemy_base_table.setCellWidget(row_idx, 0, checkbox_widget)
            checkbox_widget.checkbox.stateChanged.connect(self.update_map)

            for col_idx, item in enumerate(enemy_base[1:], start=1):  # id 열 제외
                table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.enemy_base_table.setItem(row_idx, col_idx, table_item)

            # id를 첫 번째 열의 UserRole에 저장
            self.enemy_base_table.item(row_idx, 1).setData(Qt.UserRole, enemy_base[0])

        self.enemy_base_table.setColumnHidden(4, True)

        self.update_map()
        self.update_pagination()

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
            self.load_enemy_bases()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_label()
            self.load_enemy_bases()

    def add_enemy_base(self):
        add_enemy_base_dialog = EnemyBaseInputDialog(self)
        add_enemy_base_dialog.exec_()

    def delete_enemy_base(self):
        rows_to_delete = []
        for row in range(self.enemy_base_table.rowCount()):
            checkbox_widget = self.enemy_base_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.isChecked():
                rows_to_delete.append(row)

        if not rows_to_delete:
            QMessageBox.warning(self, self.tr('경고'), self.tr('삭제할 기지가 선택되지 않았습니다.'))
            return

        reply = QMessageBox.question(self, self.tr('확인'), self.tr('선택한 기지들을 삭제하시겠습니까?'),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            cursor = self.parent.cursor
            conn = self.parent.conn
            for row in rows_to_delete:
                asset_id = self.enemy_base_table.item(row, 1).data(Qt.UserRole)
                cursor.execute("DELETE FROM enemy_bases_en WHERE id = ?", (asset_id,))
                cursor.execute("DELETE FROM enemy_bases_ko WHERE id = ?", (asset_id,))
            conn.commit()

            # 선택된 행들을 역순으로 삭제 (인덱스 변화 방지)
            for row in sorted(rows_to_delete, reverse=True):
                self.enemy_base_table.removeRow(row)

            QMessageBox.information(self, self.tr('알림'), self.tr('선택한 기지들이 삭제되었습니다.'))
            self.load_all_enemy_bases()  # 테이블 새로고침

    def correct_enemy_base(self):
        checked_rows = [row for row in range(self.enemy_base_table.rowCount())
                        if self.enemy_base_table.cellWidget(row, 0) and
                        self.enemy_base_table.cellWidget(row, 0).isChecked()]

        if len(checked_rows) != 1:
            QMessageBox.warning(self, self.tr("경고"), self.tr("수정을 위해 정확히 하나의 기지를 선택해주세요."))
            return

        row = checked_rows[0]
        asset_id = self.enemy_base_table.item(row, 1).data(Qt.UserRole)

        cursor = self.parent.cursor
        cursor.execute(f"SELECT * FROM enemy_bases_ko WHERE id = ?", (asset_id,))

        enemy_base_data = cursor.fetchone()

        edit_window = EnemyBaseInputDialog(self, edit_mode=True, enemy_data=enemy_base_data)
        if edit_window.exec_() == QDialog.Accepted:
            self.load_all_enemy_bases()

    def update_map(self):
        # 새로운 지도 객체를 생성하되, 현재의 중심 위치와 줌 레벨을 사용합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        selected_enemy_bases = self.get_selected_enemy_bases()
        selected_weapons = self.get_selected_weapons()
        print
        if selected_enemy_bases:
            EnemyBaseMapView(selected_enemy_bases, self.map)

        if selected_weapons:
            EnemyWeaponMapView(selected_weapons, self.show_threat_radius, self.map)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

    def get_selected_enemy_bases(self):
        selected_enemy_bases = []
        for row in range(self.enemy_base_table.rowCount()):
            checkbox_widget = self.enemy_base_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_base_table.item(row, 1).text()
                mgrs_coord = self.enemy_base_table.item(row, 4).text()
                weapon_system = self.enemy_base_table.item(row, 5).text()
                selected_enemy_bases.append((base_name, mgrs_coord, weapon_system))
        return selected_enemy_bases

    def get_selected_weapons(self):
        selected_enemy_weapons = []
        for row in range(self.enemy_base_table.rowCount()):
            checkbox_widget = self.enemy_base_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                base_name = self.enemy_base_table.item(row, 1).text()
                mgrs_coord = self.enemy_base_table.item(row, 4).text()
                weapon_system = self.enemy_base_table.item(row, 5).text()
                weapon_systems_list = weapon_system.split(", ")
                for weapon in weapon_systems_list:
                    for weapon_systems_check, checkbox in self.enemy_weapon_system_checkboxes.items():
                        if checkbox.isChecked() and weapon == weapon_systems_check:
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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Enemy Missile Bases")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Enemy Missile Bases")

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

class CoordinateEdit(UnderlineEdit):
    def __init__(self, coordinate_type, parent=None):
        super().__init__(parent)
        self.coordinate_type = coordinate_type
        self.setPlaceholderText(f"예: {'N39.99999' if coordinate_type == '위도' else 'E128.99999'}")
        self.other_edit = None

    def set_other_edit(self, other_edit):
        self.other_edit = other_edit

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.validate_input()

    def validate_input(self):
        if not self.text():
            return

        pattern = r'^[NS]?\d{1,2}\.\d{5}$' if self.coordinate_type == '위도' else r'^[EW]?\d{1,3}\.\d{5}$'
        if not re.match(pattern, self.text()):
            self.show_warning(f"{self.coordinate_type} 형식이 올바르지 않습니다.\n예시: {'N39.99999' if self.coordinate_type == '위도' else 'E128.99999'}")
        else:
            if self.other_edit and self.other_edit.text():
                other_pattern = r'^[EW]?\d{1,3}\.\d{5}$' if self.coordinate_type == '위도' else r'^[NS]?\d{1,2}\.\d{5}$'
                if not re.match(other_pattern, self.other_edit.text()):
                    self.other_edit.show_warning(f"{'경도' if self.coordinate_type == '위도' else '위도'} 형식이 올바르지 않습니다.\n예시: {'E128.99999' if self.coordinate_type == '위도' else 'N39.99999'}")

    def show_warning(self, message):
        dialog = WarningDialog(message, self)
        dialog.exec_()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

class WarningDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("경고")
        self.setWindowIcon(QIcon("warning_icon.png"))  # 경고 아이콘 추가 (아이콘 파일 필요)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("background-color: #FFF0F0;")

        layout = QVBoxLayout()

        warning_label = QLabel(message)
        warning_label.setStyleSheet("color: #D32F2F; font-size: 14px;")
        warning_label.setWordWrap(True)
        warning_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning_label)

        ok_button = QPushButton("확인")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
        """)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

class MainWindow(QtWidgets.QMainWindow, QObject):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CAL/DAL Management System")
        self.setWindowIcon(QIcon("logo.png"))
        self.setMinimumSize(800, 600)
        self.map_app = MapApp()
        self.selected_language = "ko"  # 기본 언어 설정
        try:
            self.conn = sqlite3.connect('assets_management.db')
            self.cursor = self.conn.cursor()
            self.setupDatabase()
        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"데이터베이스 연결 오류: {e}"))
            sys.exit(1)

        self.centralWidget = QStackedWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainPage()
        self.enemy_bases_page = EnemyBaseWindow(self)
        self.centralWidget.addWidget(self.enemy_bases_page)  # 이 줄을 추가

    def setupDatabase(self):
        try:
            self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS enemy_bases_ko (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                base_name TEXT,
                                area TEXT, 
                                coordinate TEXT,
                                mgrs TEXT,
                                weapon_system TEXT
                            )
                        ''')
            self.conn.commit()
            self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS enemy_bases_en (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                base_name TEXT,
                                area TEXT, 
                                coordinate TEXT,
                                mgrs TEXT,
                                weapon_system TEXT
                            )
                        ''')
            self.conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"테이블 생성 오류: {e}"))
            raise

    def show_main_page(self):
        self.centralWidget.setCurrentIndex(0)

    def mainPage(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(self.tr("적 미사일 기지 관리 시스템"))
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QtGui.QFont("Arial", 24))
        layout.addWidget(title)
        manage_assets_button = QPushButton(self.tr("적 기지 관리"))
        manage_assets_button.setFont(QtGui.QFont("Arial", 16))
        manage_assets_button.clicked.connect(self.show_enemy_bases_page)
        layout.addWidget(manage_assets_button)
        self.centralWidget.addWidget(page)

    def show_enemy_bases_page(self):
        self.centralWidget.setCurrentWidget(self.enemy_bases_page)
        self.enemy_bases_page.load_all_enemy_bases()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
