from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QMainWindow, QStackedWidget, QMessageBox,
                             QComboBox, QLineEdit, QFormLayout, QGroupBox,
                             QCheckBox, QHeaderView, QDialog, QApplication)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtCore import Qt, QRect, QCoreApplication, QTranslator
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtCore import QUrl, QSize, QTimer, QTemporaryFile, QDir, QEventLoop, QDateTime
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from addasset import AutoSpacingLineEdit, UnderlineEdit
from PyQt5.QtWidgets import *
import sqlite3
import sys, json, folium, io
import re, mgrs
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from PyQt5.QtCore import QDateTime
from weapon_map_view import WeaponAssetMapView, WeaponMapView
from PyQt5.QtWebEngineWidgets import QWebEngineView
from setting import MapApp


# AddDefenseAssetWindow 클래스
class AddWeaponAssetWindow(QDialog):
    def __init__(self, parent, edit_mode=False, asset_data=None):
        super(AddWeaponAssetWindow, self).__init__(parent)
        self.setWindowIcon(QIcon("image/logo.png"))
        self.parent = parent
        self.edit_mode = edit_mode
        self.asset_data = asset_data
        self.asset_id = None
        self.asset_info_fields = {}  # 여기에 asset_info_fields 딕셔너리 초기화
        self.initUI()
        if self.edit_mode and self.asset_data:
            self.setWindowTitle(self.tr("미사일 방공포대 정보수정"))
            self.populate_fields()  # initUI 호출 후에 populate_fields 호출
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)


    def initUI(self):
        self.setWindowTitle(self.tr("미사일 방공포대 입력"))
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        asset_info_group = QGroupBox(self.tr("미사일 방공포대 정보"))
        asset_info_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        asset_info_layout = QVBoxLayout(asset_info_group)

        self.asset_info_scroll = QScrollArea()
        self.asset_info_scroll.setWidgetResizable(True)
        asset_info_container = QWidget()
        asset_info_layout_main = QGridLayout(asset_info_container)
        asset_info_layout_main.setVerticalSpacing(20)
        asset_info_layout_main.setColumnStretch(1, 1)

        labels = [
            self.tr("구성군"),
            (self.tr("지역구분"), self.tr("(영문)")),
            (self.tr("방공포대명"), self.tr("(영문)")),
            (self.tr("위도"), self.tr("경도")),
            self.tr("군사좌표(MGRS)"),
            self.tr("무기체계"),
            self.tr("보유탄수"),
            self.tr("위협방위")  # 새로운 라벨 추가
        ]


        row = 0  # 행 번호 초기화
        for label in labels:
            hbox = QHBoxLayout()  # 수평 레이아웃 생성

            if isinstance(label, tuple):  # 레이블이 튜플인 경우 (예: 담당자와 영문)
                label_widget = QLabel(label[0])
                sub_label_widget = QLabel(label[1])
                input_widgets = []

                for i, sub_label in enumerate(label):
                    if label == (self.tr("위도"), self.tr("경도")):
                        input_widget = CoordinateEdit(sub_label)
                        input_widget.editingFinished.connect(
                            self.check_coordinates)  # textChanged에서 editingFinished로 변경
                    else:
                        input_widget = UnderlineEdit()
                    input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    input_widgets.append(input_widget)

                hbox.addWidget(label_widget)
                hbox.addWidget(input_widgets[0])
                hbox.addWidget(sub_label_widget)
                hbox.addWidget(input_widgets[1])

                if label == (self.tr("위도"), self.tr("경도")):
                    self.lat_widget = input_widgets[0]
                    self.lon_widget = input_widgets[1]

                self.asset_info_fields[label] = tuple(input_widgets)

                # 레이블 위젯 스타일 설정 (메인 레이블과 서브 레이블 모두 동일한 스타일 적용)
                for widget in [label_widget, sub_label_widget]:
                    widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
                    widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                    widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    widget.setFixedWidth(75)  # 레이블 너비를 절반으로 줄임


            else:  # 레이블이 단일 문자열인 경우
                label_widget = QLabel(label)

                if label == self.tr("구성군"):
                    self.unit_combo = QComboBox()
                    self.unit_combo.addItems([self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
                    self.unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.unit_combo.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    input_widget = self.unit_combo

                elif label == self.tr("군사좌표(MGRS)"):
                    input_widget = AutoSpacingLineEdit()
                    input_widget.setPlaceholderText("99A AA 99999 99999")

                elif label == self.tr("무기체계"):
                    self.weapon_system_input = QComboBox()

                    # weapon_systems.json 파일에서 무기체계 데이터 읽기
                    with open('weapon_systems.json', 'r', encoding='utf-8') as file:
                        weapon_systems = json.load(file)

                    # 무기체계 이름들을 콤보박스에 추가
                    self.weapon_system_input.addItems(weapon_systems.keys())

                    self.weapon_system_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.weapon_system_input.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    input_widget = self.weapon_system_input

                elif label == self.tr("위협방위"):
                    input_widget = QLineEdit()
                    input_widget.setPlaceholderText("000 ~ 359")

                else:
                    input_widget = UnderlineEdit()

                input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")

                hbox.addWidget(label_widget)
                hbox.addWidget(input_widget)

                self.asset_info_fields[label] = input_widget

            # 레이블 위젯 스타일 설정
            label_widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
            label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label_widget.setFixedWidth(150)  # 모든 레이블의 너비를 고정

            asset_info_layout_main.addLayout(hbox, row, 0, 1, 4)
            row += 1

        # 모든 입력 필드를 추가한 후에 방어자산 포함여부 체크박스를 추가합니다.
        self.dal_select_checkbox = QCheckBox(self.tr("방어자산 포함여부"))
        self.dal_select_checkbox.setStyleSheet("font: 강한공군체; font-size: 12pt;")
        asset_info_layout_main.addWidget(self.dal_select_checkbox, row, 2, 1, 4)

        asset_info_layout_main.setColumnStretch(0, 0)
        asset_info_layout_main.setColumnStretch(1, 1)
        asset_info_layout_main.setRowStretch(len(labels) - 1, 1)

        self.asset_info_scroll.setWidget(asset_info_container)
        asset_info_layout.addWidget(self.asset_info_scroll)
        main_layout.addWidget(asset_info_group)

        self.save_button = QPushButton(self.tr("저장"))
        self.save_button.clicked.connect(self.save_asset)
        self.save_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold; padding: 10px;")
        self.save_button.setFixedSize(150, 50)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def convert_to_mgrs(self):
        lat_widget, lon_widget = self.asset_info_fields[(self.tr("위도"), self.tr("경도"))]
        lat_input = lat_widget.text()
        lon_input = lon_widget.text()

        # 입력 형식 검증
        lat_pattern = r'^[NS]\d{2}\.\d{5}'
        lon_pattern = r'^[EW]\d{3}\.\d{5}'

        if not re.match(lat_pattern, lat_input) or not re.match(lon_pattern, lon_input):
            QMessageBox.warning(self, "입력 오류",
                                "위도와 경도 형식이 올바르지 않습니다.\n올바른 형식: N##.##### 또는 S##.#####, E###.##### 또는 W###.#####")
            return

        try:
            lat = float(lat_input[1:])  # 'N' 또는 'S'와 '°' 제거
            lon = float(lon_input[1:])  # 'E' 또는 'W'와 '°' 제거

            if lat_input.startswith('S'):
                lat = -lat
            if lon_input.startswith('W'):
                lon = -lon

            m = mgrs.MGRS()
            mgrs_coord = m.toMGRS(lat, lon)
            self.asset_info_fields[self.tr("군사좌표(MGRS)")].setText(mgrs_coord)
        except ValueError as e:
            QMessageBox.warning(self, "변환 오류", f"좌표 변환 중 오류가 발생했습니다: {e}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"예기치 않은 오류가 발생했습니다: {e}")

    @staticmethod
    def getting_unit(unit):
        if unit == "지상군" or unit == "Ground Forces":
            return ("지상군", "Ground Forces")
        elif unit == "해군" or unit == "Navy":
            return ("해군", "Navy")
        elif unit == "공군" or unit == "Air Force":
            return ("공군", "Air Force")
        elif unit == "기타" or unit == "Other":
            return ("기타", "Other")
        return (unit, unit)  # 기본값

    def save_asset(self):
        try:
            # 구성군 데이터 저장
            unit = self.unit_combo.currentText().strip()
            unit_tuple = self.getting_unit(unit)
            weapon_system = self.weapon_system_input.currentText().strip()
            dal_select = self.dal_select_checkbox.isChecked()
            asset_data = {}
            for label, field in self.asset_info_fields.items():
                if isinstance(field, QTextEdit):
                    asset_data[label] = field.toPlainText().strip()
                elif isinstance(field, QLineEdit):
                    asset_data[label] = field.text().strip()
                elif isinstance(field, tuple):
                    asset_data[label] = tuple(
                        f.text().strip() if isinstance(f, QLineEdit) else f.toPlainText().strip() for f in field)
            # 새로운 형식으로 변경
            # 경위도 검증
            lat_lon_key = (self.tr("위도"), self.tr("경도"))
            lat, lon = asset_data[lat_lon_key]
            if not self.validate_latitude(lat) or not self.validate_longitude(lon):
                QMessageBox.warning(self, self.tr("경고"), self.tr(
                    "올바른 경위도 형식을 입력해주세요.\n위도: N##.##### 또는 S##.#####\n경도: E###.##### 또는 W###.#####"))
                return

            lat_lon = f"{lat},{lon}"

            # 위협 방위 유효성 검사
            if not self.validate_threat_degree(asset_data[self.tr("위협방위")]):
                QMessageBox.warning(self, self.tr("경고"), self.tr("위협 방위는 0에서 359 사이의 정수여야 합니다."))
                return

            try:
                cursor = self.parent.parent.conn.cursor()
                if self.edit_mode:
                    cursor.execute(
                        "UPDATE weapon_assets_ko SET unit=?, area=?, asset_name=?, coordinate=?, mgrs=?, weapon_system=?, ammo_count=?, threat_degree=?, dal_select=? WHERE id=?",
                        (unit_tuple[0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0],
                         asset_data[(self.tr("방공포대명"), self.tr("(영문)"))][0], lat_lon,
                         asset_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")], dal_select,
                         self.asset_id)
                    )

                    cursor.execute(
                        "UPDATE weapon_assets_en SET unit=?, area=?, asset_name=?, coordinate=?, mgrs=?, weapon_system=?, ammo_count=?, threat_degree=?, dal_select=? WHERE id=?",
                        (unit_tuple[1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1],
                         asset_data[(self.tr("방공포대명"), self.tr("(영문)"))][1], lat_lon,
                         asset_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")], dal_select,
                         self.asset_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO weapon_assets_ko (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (unit_tuple[0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0],
                         asset_data[(self.tr("방공포대명"), self.tr("(영문)"))][0], lat_lon,
                         asset_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")], dal_select)
                    )
                    cursor.execute(
                        "INSERT INTO weapon_assets_en (unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (unit_tuple[1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1],
                         asset_data[(self.tr("방공포대명"), self.tr("(영문)"))][1], lat_lon,
                         asset_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")], dal_select)
                    )
                self.parent.parent.conn.commit()
                self.accept()
                if self.edit_mode:
                    QMessageBox.information(self, self.tr("성공"), self.tr("자산이 성공적으로 수정되었습니다."))
                else:
                    QMessageBox.information(self, self.tr("성공"), self.tr("자산이 성공적으로 저장되었습니다."))
            except sqlite3.Error as e:
                QMessageBox.critical(self, self.tr("오류"), self.tr(f"데이터베이스 오류: {e}"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("오류"), self.tr(f"예기치 않은 오류 발생: {e}"))
        finally:
            self.parent.load_assets()

    def populate_fields(self):
        if self.asset_data:
            self.asset_id = self.asset_data[0]
            cursor = self.parent.parent.conn.cursor()
            cursor.execute(f"SELECT * FROM weapon_assets_ko WHERE id = ?", (self.asset_id,))
            asset_data1 = cursor.fetchone()
            cursor.execute(f"SELECT * FROM weapon_assets_en WHERE id = ?", (self.asset_id,))
            asset_data2 = cursor.fetchone()
            coord_str = asset_data1[4]
            lat, lon = coord_str.split(',')
            for label, field in self.asset_info_fields.items():
                if isinstance(field, tuple):
                    if label == (self.tr("지역구분"), self.tr("(영문)")):
                        f1, f2 = field
                        print(f1, f2)
                        f1.setText(str(asset_data1[2]))
                        f2.setText(str(asset_data2[2]))
                    elif label == (self.tr("방공포대명"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(str(asset_data1[3]))
                        f2.setText(str(asset_data2[3]))
                    elif label == (self.tr("위도"), self.tr("경도")):
                        f1, f2 = field
                        f1.setText(lat)
                        f2.setText(lon)
                else:
                    self.unit_combo.setCurrentText(self.asset_data[1])
                    self.asset_info_fields[self.tr("군사좌표(MGRS)")].setText(self.asset_data[5])
                    self.weapon_system_input.setCurrentText(self.asset_data[6])
                    self.asset_info_fields[self.tr("보유탄수")].setText(str(self.asset_data[7]))
                    self.asset_info_fields[self.tr("위협방위")].setText(str(self.asset_data[8]))

    @staticmethod
    def validate_latitude(lat):
        pattern = r'^[NS]\d{2}\.\d{5}'
        return bool(re.match(pattern, lat))

    @staticmethod
    def validate_longitude(lon):
        pattern = r'^[EW]\d{3}\.\d{5}'
        return bool(re.match(pattern, lon))

    @staticmethod
    def validate_threat_degree(value):
        try:
            degree = int(value)
            return 0 <= degree <= 359
        except ValueError:
            return False

    def check_coordinates(self):
        if hasattr(self, 'lat_widget') and hasattr(self, 'lon_widget'):
            if self.lat_widget.text() and self.lon_widget.text():
                self.convert_to_mgrs()

class WeaponAssetWindow(QDialog):
    def __init__(self, parent):
        super(WeaponAssetWindow, self).__init__(parent)
        self.parent = parent
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.initUI()
        self.weapon_assets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.load_all_assets()
        self.show_threat_radius = False
        self.update_map()

    def initUI(self):
        main_layout = QHBoxLayout()

        # QSplitter 생성
        splitter = QSplitter(Qt.Horizontal)

        # 좌측 레이아웃 (필터 및 테이블)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 필터 그룹박스 생성
        filter_group = QGroupBox(self.tr("필터"))
        filter_group.setStyleSheet("font: 바른공군체; font-size: 18px; font-weight: bold;")

        # 필터 레이아웃 생성
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(10)
        filter_layout.setAlignment(Qt.AlignLeft)

        # 첫 번째 줄: 콤보박스들
        combo_layout = QHBoxLayout()
        combo_layout.setAlignment(Qt.AlignLeft)

        # 구성군 선택 필터
        unit_filter_label = QLabel(self.tr("구성군 선택"), self)
        unit_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
        self.unit_filter.setFixedSize(150, 30)
        self.unit_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.unit_filter.currentIndexChanged.connect(self.load_assets)
        combo_layout.addWidget(unit_filter_label)
        combo_layout.addWidget(self.unit_filter)
        combo_layout.addStretch(1)

        # 무기체계 선택 필터
        weapon_filter_label = QLabel(self.tr("무기체계 선택"), self)
        weapon_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.weapon_filter = QComboBox()
        # weapon_systems.json 파일에서 무기체계 데이터 읽기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_systems = json.load(file)

        # '전체' 항목을 포함한 무기체계 목록 생성
        weapon_system_list = [self.tr('전체')] + list(weapon_systems.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.weapon_filter.addItems(weapon_system_list)
        self.weapon_filter.setFixedSize(150, 30)
        self.weapon_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.weapon_filter.currentIndexChanged.connect(self.load_assets)
        combo_layout.addWidget(weapon_filter_label)
        combo_layout.addWidget(self.weapon_filter)
        combo_layout.addStretch(1)

        filter_layout.addLayout(combo_layout)

        # 두 번째 줄: 검색 섹션
        search_layout = QHBoxLayout()
        search_layout.setAlignment(Qt.AlignLeft)

        search_label = QLabel(self.tr("검색"), self)
        search_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.asset_search_input = QLineEdit()
        self.asset_search_input.setPlaceholderText(self.tr("검색어를 입력하세요"))
        self.asset_search_input.setFixedSize(200, 30)
        self.asset_search_input.setStyleSheet("font: 바른공군체; font-size: 16px;")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.asset_search_input)

        self.find_button = QPushButton(self.tr("찾기"))
        self.find_button.setFixedSize(80, 30)
        self.find_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold;")
        self.find_button.clicked.connect(self.load_assets)
        search_layout.addWidget(self.find_button)
        search_layout.addStretch(1)

        filter_layout.addLayout(search_layout)

        # 방어자산 포함여부 필터 추가
        self.dal_select_filter = QCheckBox(self.tr("방어자산만 표시"))
        self.dal_select_filter.stateChanged.connect(self.load_assets)
        filter_layout.addWidget(self.dal_select_filter)

        # 필터 그룹에 레이아웃 설정
        filter_group.setLayout(filter_layout)

        # 메인 레이아웃에 필터 그룹 추가
        left_layout.addWidget(filter_group)

        # 테이블
        self.weapon_assets_table = MyTableWidget()
        self.weapon_assets_table.setColumnCount(10)  # 삭제 버튼 열 추가
        self.weapon_assets_table.setAlternatingRowColors(True)
        self.weapon_assets_table.setHorizontalHeaderLabels([
            "", self.tr("구성군"), self.tr("지역구분"), self.tr("방공포대명"), self.tr("경위도"), self.tr("군사좌표(MGRS)"),
            self.tr("무기체계"), self.tr("보유탄수"), self.tr("위협방위"), self.tr("삭제")])

        # 행 번호 숨기기
        # self.weapon_assets_table.verticalHeader().setVisible(False)
        self.weapon_assets_table.setStyleSheet("QTableWidget {background-color: #ffffff; font: 바른공군체; font-size: 16px;}"
                                        "QTableWidget::item { padding: 1px; }")
        self.weapon_assets_table.setSelectionBehavior(QTableView.SelectRows)


        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.weapon_assets_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.weapon_assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 50)
        header.resizeSection(-1, 100)

        # 헤더 텍스트 중앙 정렬 및 자동 줄바꿈
        for column in range(header.count()):
            item = self.weapon_assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블 설정
        self.weapon_assets_table.horizontalHeader().setStretchLastSection(False)
        self.weapon_assets_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.weapon_assets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 각 열의 내용에 맞게 너비 설정
        for column in range(1, header.count() - 1):
            self.weapon_assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        # 헤더 높이 자동 조절
        self.weapon_assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.weapon_assets_table.verticalHeader().setDefaultSectionSize(50)

        left_layout.addWidget(self.weapon_assets_table)

        # 버튼
        button_layout = QHBoxLayout()
        self.add_weapon_asset_button = QPushButton(self.tr("입력"), self)
        self.correction_button = QPushButton(self.tr("수정"), self)
        self.return_button = QPushButton(self.tr("메인화면"), self)
        self.add_weapon_asset_button.clicked.connect(self.add_weapon_asset)
        self.correction_button.clicked.connect(self.correct_asset)
        self.return_button.clicked.connect(self.parent.show_main_page)

        for button in [self.add_weapon_asset_button, self.correction_button, self.return_button]:
            button.setFont(QFont("강한공군체", 13, QFont.Bold))
            button.setFixedSize(130, 40)
            button_layout.addWidget(button)

        left_layout.addLayout(button_layout)

        # 우측 레이아웃 (지도 및 체크박스)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 무기체계 체크박스 그룹
        weapon_group = QGroupBox(self.tr("무기체계"))
        weapon_layout = QHBoxLayout()
        weapon_layout.setContentsMargins(10, 5, 10, 5)  # 여백 조정
        weapon_layout.setSpacing(10)  # 체크박스 간 간격 조정
        self.weapon_system_checkboxes = {}
        # weapon_systems.json 파일에서 무기체계 목록 가져오기
        with open('weapon_systems.json', 'r', encoding='utf-8') as f:
            weapon_systems = json.load(f)
        for weapon in weapon_systems:
            checkbox = QCheckBox(weapon)
            checkbox.stateChanged.connect(self.update_map)
            self.weapon_system_checkboxes[weapon] = checkbox
            weapon_layout.addWidget(checkbox)
        weapon_group.setLayout(weapon_layout)
        weapon_group.setFixedHeight(weapon_layout.sizeHint().height() + 20)  # 높이 조정
        right_layout.addWidget(weapon_group)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        checkbox_button_layout = QHBoxLayout()

        # 위협반경 표시 체크박스
        self.radius_checkbox = QCheckBox(self.tr("방어반경 표시"), self)
        self.radius_checkbox.stateChanged.connect(self.toggle_threat_radius)
        checkbox_button_layout.addWidget(self.radius_checkbox)

        # 지도 출력 버튼
        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 12, QFont.Bold))
        self.print_button.setFixedSize(150, 40)
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

        self.load_assets()

    def toggle_threat_radius(self, state):
        self.show_threat_radius = state == Qt.Checked
        self.update_map()

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.load_all_assets()
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.weapon_filter.setCurrentIndex(0)  # 무기체계 필터를 "전체"로 설정
        self.asset_search_input.clear()  # 검색 입력창 비우기
        # 테이블의 모든 체크박스 해제
        self.weapon_assets_table.uncheckAllRows()
        for weapon_system, checkbox in self.weapon_system_checkboxes.items():
            if checkbox.isChecked():
                checkbox.setChecked(False)
        self.load_assets()  # 테이블 데이터 새로고침
        # 지도 업데이트
        self.update_map()

    def load_all_assets(self):
        query = f"SELECT id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select FROM weapon_assets_{self.parent.selected_language}"
        cursor = self.parent.cursor
        cursor.execute(query, )
        assets = cursor.fetchall()

        self.weapon_assets_table.setRowCount(len(assets))
        for row_idx, asset in enumerate(assets):
            checkbox = CenteredCheckBox()
            self.weapon_assets_table.setCellWidget(row_idx, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col_idx, item in enumerate(asset[1:], start=1):  # id 열 제외
                if col_idx == 8 :  # 위협방위 열
                    threat_degree = f"{int(item):03d}°"  # 3자리 숫자로 변환하고 도(°) 기호 추가
                    table_item = QTableWidgetItem(threat_degree)
                else:
                    table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.weapon_assets_table.setItem(row_idx, col_idx, table_item)

            # id를 첫 번째 열의 UserRole에 저장
            self.weapon_assets_table.item(row_idx, 1).setData(Qt.UserRole, asset[0])
        self.weapon_assets_table.setColumnHidden(4, True)
        self.weapon_assets_table.setColumnHidden(5, True)
        self.weapon_assets_table.setColumnHidden(10, True)


    def load_assets(self):
        """현재 필터에 맞춰 자산 정보를 로드하여 표시하는 함수"""
        unit_filter = self.unit_filter.currentText()
        weapon_filter = self.weapon_filter.currentText()
        dal_filter = self.dal_select_filter.isChecked()
        search_text = self.asset_search_input.text()

        query = f"""
            SELECT id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree, dal_select 
            FROM weapon_assets_{self.parent.selected_language}
            WHERE 1=1
        """
        params = []

        if unit_filter != self.tr("전체"):
            query += " AND unit = ?"
            params.append(unit_filter)

        if weapon_filter != self.tr("전체"):
            query += " AND weapon_system = ?"
            params.append(weapon_filter)

        if dal_filter == 1:
            query += " AND dal_select = 1"

        if search_text:
            query += """ AND (
                asset_name LIKE ? OR
                area LIKE ? OR
                mgrs LIKE ?
            )"""
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param, search_param])

        cursor = self.parent.cursor
        cursor.execute(query, params)
        assets = cursor.fetchall()

        self.weapon_assets_table.uncheckAllRows()
        self.weapon_assets_table.setRowCount(len(assets))
        for row_idx, asset in enumerate(assets):
            checkbox = CenteredCheckBox()
            self.weapon_assets_table.setCellWidget(row_idx, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)

            for col_idx, item in enumerate(asset[1:], start=1):  # id 열 제외
                if col_idx == 7:  # 위협방위 열
                    threat_degree = f"{int(item):03d}°"  # 3자리 숫자로 변환하고 도(°) 기호 추가
                    table_item = QTableWidgetItem(threat_degree)
                else:
                    table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.weapon_assets_table.setItem(row_idx, col_idx, table_item)
                delete_button = QPushButton("삭제")
                delete_button.clicked.connect(lambda _, r=row_idx: self.delete_asset(r))
                self.weapon_assets_table.setCellWidget(row_idx, 9, delete_button)

            # id를 첫 번째 열의 UserRole에 저장
            self.update_map()
            self.weapon_assets_table.item(row_idx, 1).setData(Qt.UserRole, asset[0])

    def delete_asset(self, row):
        asset_id = self.weapon_assets_table.item(row, 1).data(Qt.UserRole)
        reply = QMessageBox.question(self, '확인', '이 자산을 삭제하시겠습니까?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            cursor = self.parent.cursor
            cursor.execute(f"DELETE FROM weapon_assets_ko WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            cursor.execute(f"DELETE FROM weapon_assets_en WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            self.weapon_assets_table.removeRow(row)
            QMessageBox.information(self, '알림', '자산이 삭제되었습니다.')
            self.load_all_assets()  # 테이블 새로고침

    def correct_asset(self):
        checked_rows = [row for row in range(self.weapon_assets_table.rowCount())
                        if self.weapon_assets_table.cellWidget(row, 0) and
                        self.weapon_assets_table.cellWidget(row, 0).isChecked()]

        if len(checked_rows) != 1:
            QMessageBox.warning(self, self.tr("경고"), self.tr("수정을 위해 정확히 하나의 자산을 선택해주세요."))
            return

        row = checked_rows[0]
        asset_id = self.weapon_assets_table.item(row, 1).data(Qt.UserRole)
        cursor = self.parent.cursor

        if self.parent.selected_language == 'ko':
            cursor.execute(f"SELECT * FROM weapon_assets_ko WHERE id = ?", (asset_id,))

        else:
            cursor.execute(f"SELECT * FROM weapon_assets_en WHERE id = ?", (asset_id,))

        asset_data = cursor.fetchone()

        edit_window = AddWeaponAssetWindow(self, edit_mode=True, asset_data=asset_data)
        if edit_window.exec_() == QDialog.Accepted:
            self.load__assets()

    def update_map(self):
        # 새로운 지도 객체를 생성하되, 현재의 중심 위치와 줌 레벨을 사용합니다.
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])

        selected_weapon_assets = self.get_selected_weapon_assets()
        selected_missile_weapons = self.get_selected_weapons()

        if selected_weapon_assets:
            WeaponAssetMapView(selected_weapon_assets, self.map)
        if selected_missile_weapons:
            WeaponMapView(selected_missile_weapons, self.map, self.show_threat_radius)

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

    def get_selected_weapon_assets(self):
        selected_weapon_assets = []
        for row in range(self.weapon_assets_table.rowCount()):
            checkbox_widget = self.weapon_assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                unit = self.weapon_assets_table.item(row, 1).text()
                area = self.weapon_assets_table.item(row, 2).text()
                asset_name = self.weapon_assets_table.item(row, 3).text()
                coordinate = self.weapon_assets_table.item(row, 4).text()
                weapon_system = self.weapon_assets_table.item(row, 6).text()
                ammo_count = self.weapon_assets_table.item(row,7).text()
                threat_degree = int(self.weapon_assets_table.item(row, 8).text().replace("°", ""))  # 위협방위 정보 추가
                selected_weapon_assets.append((unit, area, asset_name, coordinate, weapon_system, ammo_count, threat_degree))
        return selected_weapon_assets

    def get_selected_weapons(self):
        selected_missile_weapons = []
        for row in range(self.weapon_assets_table.rowCount()):
            checkbox_widget = self.weapon_assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                unit = self.weapon_assets_table.item(row, 1).text()
                area = self.weapon_assets_table.item(row, 2).text()
                asset_name = self.weapon_assets_table.item(row, 3).text()
                coordinate = self.weapon_assets_table.item(row, 4).text()
                weapon_system = self.weapon_assets_table.item(row, 6).text()
                ammo_count = self.weapon_assets_table.item(row,7).text()
                threat_degree = int(self.weapon_assets_table.item(row, 8).text().replace("°", ""))  # 위협방위 정보 추가
                for weapon_systems_check, checkbox in self.weapon_system_checkboxes.items():
                    if checkbox.isChecked() and weapon_systems_check == weapon_system:
                        selected_missile_weapons.append((unit, area, asset_name, coordinate, weapon_system, ammo_count, threat_degree))
        return selected_missile_weapons

    def add_weapon_asset(self):
        add_defense_asset = AddWeaponAssetWindow(self)
        add_defense_asset.exec_()

    def print_weapon_assets_table(self):
        try:
            document = QTextDocument()
            cursor = QTextCursor(document)

            document.setDefaultStyleSheet("""
                body { font-family: '바른공군체', sans-serif; }
                h1 { color: black; }
                .info { padding: 10px; }
                table { border-collapse: collapse; width: 100%; }
                td, th { border: 1px solid black; padding: 4px; text-align: center; }
            """)

            font = QFont("바른공군체", 8)
            document.setDefaultFont(font)

            cursor.insertHtml("<h1 align='center'>" + self.tr("방어자산 보고서") + "</h1>")
            cursor.insertBlock()

            cursor.insertHtml("<div class='info' style='text-align: left; font-size: 0.9em;'>")
            cursor.insertHtml(self.tr("보고서 생성 일시: ") + QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"))
            cursor.insertHtml("</div>")
            cursor.insertBlock()

            table_format = QTextTableFormat()
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            table_format.setCellPadding(2)
            table_format.setAlignment(Qt.AlignCenter)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))

            rows = self.weapon_assets_table.rowCount() + 1
            cols = self.weapon_assets_table.columnCount()

            excluded_columns = [0]  # 체크박스 열 제외

            actual_cols = cols - len(excluded_columns)
            table = cursor.insertTable(rows, actual_cols, table_format)

            header_col = 0
            for col in range(cols):
                if col not in excluded_columns:
                    cell = table.cellAt(0, header_col)
                    cellCursor = cell.firstCursorPosition()
                    cellCursor.insertHtml(f"<th>{self.weapon_assets_table.horizontalHeaderItem(col).text()}</th>")
                    header_col += 1

            for row in range(self.weapon_assets_table.rowCount()):
                data_col = 0
                for col in range(cols):
                    if col not in excluded_columns:
                        item = self.weapon_assets_table.item(row, col)
                        if item:
                            cell = table.cellAt(row + 1, data_col)
                            cellCursor = cell.firstCursorPosition()
                            cellCursor.insertText(item.text())
                        data_col += 1

            preview = QPrintPreviewDialog()
            preview.setWindowIcon(QIcon("image/logo.png"))
            preview.paintRequested.connect(lambda p: document.print_(p))
            preview.exec_()

            file_path, _ = QFileDialog.getSaveFileName(self, self.tr("PDF 저장"), "", "PDF Files (*.pdf)")
            if file_path:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                document.print_(printer)
                QMessageBox.information(self, self.tr("저장 완료"), self.tr("PDF가 저장되었습니다: {}").format(file_path))

            QCoreApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr("다음 오류가 발생했습니다: {}").format(str(e)))

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Missile Defense Systems Map")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Missile Defense Systems Map")

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

# MainWindow 클래스
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("미사일 방공포대 관리"))
        self.selected_language = "ko"
        self.map_app = MapApp()
        self.setGeometry(100, 100, 1024, 768)

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
        self.defense_assets_page = WeaponAssetWindow(self)
        self.centralWidget.addWidget(self.defense_assets_page)  # 이 줄을 추가

    def setupDatabase(self):
        try:
            self.cursor.execute('''
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
            self.conn.commit()
            self.cursor.execute('''
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
            self.conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"테이블 생성 오류: {e}"))
            raise

    def mainPage(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(self.tr("미사일 방공포대 관리 시스템"))
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QtGui.QFont("Arial", 24))
        layout.addWidget(title)
        manage_assets_button = QPushButton(self.tr("미사일 방공포대 관리"))
        manage_assets_button.setFont(QtGui.QFont("Arial", 16))
        manage_assets_button.clicked.connect(self.show_defense_assets_page)
        layout.addWidget(manage_assets_button)
        self.centralWidget.addWidget(page)

    def show_defense_assets_page(self):
        self.centralWidget.setCurrentWidget(self.defense_assets_page)
        self.defense_assets_page.load_all_assets()

    def show_main_page(self):
        self.centralWidget.setCurrentIndex(0)

    def closeEvent(self, event):
        self.conn.close()
        super().closeEvent(event)

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



if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
