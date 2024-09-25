from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QMainWindow, QStackedWidget, QMessageBox,
                             QComboBox, QLineEdit, QFormLayout, QGroupBox,
                             QCheckBox, QHeaderView, QDialog, QApplication)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtCore import Qt, QRect, QCoreApplication, QTranslator
from addasset import AutoSpacingLineEdit, UnderlineEdit
from PyQt5.QtWidgets import *
import sqlite3
import sys, json
import re, mgrs
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from PyQt5.QtCore import QDateTime
from mapview import DefenseAssetMapView
from setting import MapApp


# AddDefenseAssetWindow 클래스
class AddDefenseAssetWindow(QDialog):
    def __init__(self, parent, edit_mode=False, asset_data=None):
        super(AddDefenseAssetWindow, self).__init__(parent)
        self.parent = parent
        self.edit_mode = edit_mode
        self.asset_data = asset_data
        self.asset_id = None
        self.asset_info_fields = {}  # 여기에 asset_info_fields 딕셔너리 초기화
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        asset_info_group = QGroupBox(self.tr("방어자산 정보"))
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
            (self.tr("방어자산명"), self.tr("(영문)")),
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

            # 메인 레이아웃에 수평 레이아웃 추가
            asset_info_layout_main.addLayout(hbox, row, 0, 1, 4)
            row += 1

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
        if self.edit_mode:
            self.setWindowTitle(self.tr("방어자산 정보 수정"))
            self.setWindowIcon(QIcon("logo.png"))
            if self.asset_data:  # asset_data가 존재할 때만 populate_fields 호출
                self.populate_fields()
        else:
            self.setWindowTitle(self.tr("방어자산 추가"))
            self.setWindowIcon(QIcon("logo.png"))

    def convert_to_mgrs(self):
        lat_widget, lon_widget = self.asset_info_fields[(self.tr("위도"), self.tr("경도"))]
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
            self.asset_info_fields[self.tr("군사좌표(MGRS)")].setText(mgrs_coord)
        except ValueError as e:
            print(f"좌표 변환 오류: {e}")

    def getting_unit(self, unit):
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
            lat_lon_key = (self.tr("위도"), self.tr("경도"))
            lat, lon = asset_data[lat_lon_key]
            lat_lon = f"{lat},{lon}"
            # 위협 방위 유효성 검사
            if not self.validate_threat_degree(asset_data[self.tr("위협방위")]):
                QMessageBox.warning(self, self.tr("경고"), self.tr("위협 방위는 0에서 359 사이의 정수여야 합니다."))
                return

            try:
                cursor = self.parent.parent.conn.cursor()
                if self.edit_mode:
                    cursor.execute(
                        "UPDATE dal_assets_ko SET unit=?, area=?, asset_name=?, coordinate=?, mgrs=?, weapon_system=?, ammo_count=?, threat_degree=? WHERE id=?",
                        (unit_tuple[0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], asset_data[(self.tr("방어자산명"), self.tr("(영문)"))][0], lat_lon,
                        asset_data[self.tr("군사좌표(MGRS)")],
                        weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")],
                        self.asset_id)
                    )

                    cursor.execute(
                        "UPDATE dal_assets_en SET unit=?, area=?, asset_name=?, coordinate=?, mgrs=?, weapon_system=?, ammo_count=?, threat_degree=? WHERE id=?",
                        (unit_tuple[1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1],
                         asset_data[(self.tr("방어자산명"), self.tr("(영문)"))][1], lat_lon,
                         asset_data[self.tr("군사좌표(MGRS)")],
                         weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")],
                         self.asset_id)
                    )
                else:
                    cursor.execute("SELECT MAX(id) FROM dal_assets_ko")
                    max_id = cursor.fetchone()[0]
                    new_id = 1 if max_id is None else max_id + 1
                    cursor.execute(
                        "INSERT INTO dal_assets_ko (id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                        new_id, unit_tuple[0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], asset_data[(self.tr("방어자산명"), self.tr("(영문)"))][0], lat_lon,
                        asset_data[self.tr("군사좌표(MGRS)")],
                        weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")])
                        )
                    cursor.execute("SELECT MAX(id) FROM dal_assets_en")
                    max_id = cursor.fetchone()[0]
                    new_id = 1 if max_id is None else max_id + 1
                    cursor.execute(
                        "INSERT INTO dal_assets_en (id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                        new_id, unit_tuple[1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1], asset_data[(self.tr("방어자산명"), self.tr("(영문)"))][1], lat_lon,
                        asset_data[self.tr("군사좌표(MGRS)")],
                        weapon_system, asset_data[self.tr("보유탄수")], asset_data[self.tr("위협방위")])
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
            cursor = self.parent.parent.cursor
            cursor.execute(f"SELECT * FROM dal_assets_en WHERE id = ?", (self.asset_id,))
            asset_data2 = cursor.fetchone()
            coord_str = self.asset_data[4]
            lat, lon = coord_str.split(',')
            for label, field in self.asset_info_fields.items():
                if isinstance(field, tuple):
                    if label == (self.tr("지역구분"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(self.asset_data[2])
                        f2.setText(str(asset_data2[2]))
                    elif label == (self.tr("방어자산명"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(str(self.asset_data[3]))
                        f2.setText(str(asset_data2[3]))
                    elif label == (self.tr("위도"), self.tr("경도")):
                        f1, f2 = field
                        f1.setText(lat)
                        f2.setText(lon)

                else:
                    self.unit_combo.setCurrentText(
                        self.asset_data[1] if self.parent.parent.selected_language == 'ko' else asset_data2[1])
                    self.asset_info_fields[self.tr("군사좌표(MGRS)")].setText(self.asset_data[5])
                    self.weapon_system_input.setCurrentText(self.asset_data[6])
                    self.asset_info_fields[self.tr("보유탄수")].setText(str(self.asset_data[7]))
                    self.asset_info_fields[self.tr("위협방위")].setText(str(self.asset_data[8]))

    def validate_threat_degree(self, value):
        try:
            degree = int(value)
            return 0 <= degree <= 359
        except ValueError:
            return False

# ViewDefenseAssetWindow 클래스
class ViewDefenseAssetWindow(QWidget):
    def __init__(self, parent):
        super(ViewDefenseAssetWindow, self).__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 40, 30, 30)

        # 필터 그룹박스 생성
        filter_group = QGroupBox(self.tr("필터"))
        filter_group.setStyleSheet("font: 바른공군체; font-size: 18px; font-weight: bold;")

        # 필터 레이아웃 생성
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(20)

        # 구성군 선택 필터
        unit_filter_label = QLabel(self.tr("구성군 선택"), self)
        unit_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
        self.unit_filter.setFixedSize(150, 30)
        self.unit_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        filter_layout.addWidget(unit_filter_label)
        filter_layout.addWidget(self.unit_filter)


        # 무기체계 선택 필터
        weapon_filter_label = QLabel(self.tr("무기체계 선택"), self)
        weapon_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.weapon_filter = QComboBox()
        # weapon_systems.json 파일에서 무기체계 데이터 읽기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_systems = json.load(file)

        # '전체' 항목을 포함한 무기체계 목록 생성
        weapon_system_list = ['전체'] + list(weapon_systems.keys())
        # 무기체계 이름들을 콤보박스에 추가
        self.weapon_filter.addItems(weapon_system_list)
        self.weapon_filter.setFixedSize(150, 30)
        self.weapon_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        filter_layout.addWidget(weapon_filter_label)
        filter_layout.addWidget(self.weapon_filter)

        self.weapon_system_input = QComboBox()


        # 검색 섹션
        search_label = QLabel(self.tr("검색"), self)
        search_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.asset_search_input = QLineEdit()
        self.asset_search_input.setPlaceholderText(self.tr("검색어를 입력하세요"))
        self.asset_search_input.setFixedSize(200, 30)
        self.asset_search_input.setStyleSheet("font: 바른공군체; font-size: 16px;")
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.asset_search_input)

        # 찾기 버튼
        self.find_button = QPushButton(self.tr("찾기"))
        self.find_button.setFixedSize(80, 30)
        self.find_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold;")
        self.find_button.clicked.connect(self.load_assets)
        filter_layout.addWidget(self.find_button)

        # 여백 추가
        filter_layout.addStretch()

        # 필터 그룹에 레이아웃 설정
        filter_group.setLayout(filter_layout)

        # 메인 레이아웃에 필터 그룹 추가
        layout.addWidget(filter_group)

        self.defense_asset_table = MyTableWidget()
        self.defense_asset_table.setColumnCount(9)  # 열 개수를 9로 변경
        self.defense_asset_table.setAlternatingRowColors(True)
        self.defense_asset_table.setStyleSheet(
            "QTableWidget {background-color: #ffffff; font: 바른공군체; font-size: 16px;}"
            "QTableWidget::item { padding: 8px; }")
        self.defense_asset_table.setHorizontalHeaderLabels([
            "", self.tr("구성군"), self.tr("지역구분"), self.tr("방어자산명"), self.tr("경위도"), self.tr("군사좌표(MGRS)"),
            self.tr("방어체계"), self.tr("보유탄수"), self.tr("위협방위")])  # 위협방위 열 추가

        # 행 번호 숨기기
        self.defense_asset_table.verticalHeader().setVisible(False)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.defense_asset_table.horizontalHeader().setFont(font)
        header = self.defense_asset_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 50)
        header.setMinimumSectionSize(120)  # 최소 열 너비 설정


        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.defense_asset_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블이 수평으로 확장되도록 설정
        self.defense_asset_table.horizontalHeader().setStretchLastSection(False)
        self.defense_asset_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.defense_asset_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(1, header.count()):
            self.defense_asset_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        # 헤더 높이 자동 조절
        self.defense_asset_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.defense_asset_table.verticalHeader().setDefaultSectionSize(60)

        layout.addWidget(self.defense_asset_table, stretch=3)

        self.add_defense_asset_button = QPushButton(self.tr("방어자산 입력"), self)
        self.view_map_button = QPushButton(self.tr("지도 보기"), self)
        self.correction_button = QPushButton(self.tr("수정"), self)
        self.delete_button =  QPushButton(self.tr("삭제"), self)
        self.print_button =  QPushButton(self.tr("출력"), self)
        self.back_button = QPushButton(self.tr("메인 화면으로 돌아가기"), self)
        self.add_defense_asset_button.clicked.connect(self.add_defense_asset)
        self.view_map_button.clicked.connect(self.defense_asset_view_map)
        self.correction_button.clicked.connect(self.correct_asset)
        self.delete_button.clicked.connect(self.delete_asset)
        self.print_button.clicked.connect(self.print_defense_asset_table)
        self.back_button.clicked.connect(self.parent.show_main_page)


        # 각 버튼에 폰트 적용
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 5, 0, 5)
        for button in [self.add_defense_asset_button, self.view_map_button, self.correction_button, self.delete_button, self.print_button, self.back_button]:
            button.setFont(QFont("강한공군체", 14, QFont.Bold))
            button.setFixedSize(230, 50)
            button.setStyleSheet("QPushButton { text-align: center; }")
        button_layout.addWidget(self.add_defense_asset_button)
        button_layout.addWidget(self.view_map_button)
        button_layout.addWidget(self.correction_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.back_button)

        layout.addLayout(button_layout)  # addWidget 대신 addLayout 사용

        self.setLayout(layout)

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.weapon_filter.setCurrentIndex(0)  # 무기체계 필터를 "전체"로 설정
        self.asset_search_input.clear()  # 검색 입력창 비우기
        # 테이블의 모든 체크박스 해제
        self.defense_asset_table.uncheckAllRows()
        self.load_all_assets()  # 테이블 데이터 새로고침

    def load_all_assets(self):
        query = f"SELECT id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree FROM dal_assets_{self.parent.selected_language}"
        cursor = self.parent.cursor
        cursor.execute(query, )
        assets = cursor.fetchall()

        self.defense_asset_table.setRowCount(len(assets))
        for row_idx, asset in enumerate(assets):
            checkbox_widget = CenteredCheckBox()
            self.defense_asset_table.setCellWidget(row_idx, 0, checkbox_widget)

            for col_idx, item in enumerate(asset[1:], start=1):  # id 열 제외
                if col_idx == 8:  # 위협방위 열
                    threat_degree = f"{int(item):03d}°"  # 3자리 숫자로 변환하고 도(°) 기호 추가
                    table_item = QTableWidgetItem(threat_degree)
                else:
                    table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.defense_asset_table.setItem(row_idx, col_idx, table_item)

            # id를 첫 번째 열의 UserRole에 저장
            self.defense_asset_table.item(row_idx, 1).setData(Qt.UserRole, asset[0])

    def load_assets(self):
        """현재 필터에 맞춰 자산 정보를 로드하여 표시하는 함수"""
        unit_filter = self.unit_filter.currentText()
        weapon_filter = self.weapon_filter.currentText()
        search_text = self.asset_search_input.text()

        query = f"""
            SELECT id, unit, area, asset_name, coordinate, mgrs, weapon_system, ammo_count, threat_degree 
            FROM dal_assets_{self.parent.selected_language}
            WHERE 1=1
        """
        params = []

        if unit_filter != self.tr("전체"):
            query += " AND unit = ?"
            params.append(unit_filter)

        if weapon_filter != self.tr("전체"):
            query += " AND weapon_system = ?"
            params.append(weapon_filter)

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

        self.defense_asset_table.uncheckAllRows()
        self.defense_asset_table.setRowCount(len(assets))
        for row_idx, asset in enumerate(assets):
            checkbox_widget = CenteredCheckBox()
            self.defense_asset_table.setCellWidget(row_idx, 0, checkbox_widget)

            for col_idx, item in enumerate(asset[1:], start=1):  # id 열 제외
                if col_idx == 7:  # 위협방위 열
                    threat_degree = f"{int(item):03d}°"  # 3자리 숫자로 변환하고 도(°) 기호 추가
                    table_item = QTableWidgetItem(threat_degree)
                else:
                    table_item = QTableWidgetItem(str(item))
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.defense_asset_table.setItem(row_idx, col_idx, table_item)

            # id를 첫 번째 열의 UserRole에 저장
            self.defense_asset_table.item(row_idx, 1).setData(Qt.UserRole, asset[0])

    def delete_asset(self):
        reply = QMessageBox.question(self, self.tr('확인'), self.tr('선택한 자산들을 삭제하시겠습니까?'),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            cursor = self.parent.cursor
            conn = self.parent.conn
            rows_to_delete = []
            for row in range(self.defense_asset_table.rowCount()):
                checkbox_widget = self.defense_asset_table.cellWidget(row, 0)
                if checkbox_widget and checkbox_widget.isChecked():
                    asset_id = self.defense_asset_table.item(row, 1).data(Qt.UserRole)
                    cursor.execute(f"DELETE FROM dal_assets_en WHERE id = ?", (asset_id,))
                    cursor.execute(f"DELETE FROM dal_assets_ko WHERE id = ?", (asset_id,))
                    rows_to_delete.append(row)
            conn.commit()

            # 선택된 행들을 역순으로 삭제 (인덱스 변화 방지)
            for row in sorted(rows_to_delete, reverse=True):
                self.defense_asset_table.removeRow(row)

            QMessageBox.information(self, self.tr('알림'), self.tr('선택한 자산들이 삭제되었습니다.'))
            self.load_all_assets()  # 테이블 새로고침

    def correct_asset(self):
        checked_rows = [row for row in range(self.defense_asset_table.rowCount())
                        if self.defense_asset_table.cellWidget(row, 0) and
                        self.defense_asset_table.cellWidget(row, 0).isChecked()]

        if len(checked_rows) != 1:
            QMessageBox.warning(self, self.tr("경고"), self.tr("수정을 위해 정확히 하나의 자산을 선택해주세요."))
            return

        row = checked_rows[0]
        asset_id = self.defense_asset_table.item(row, 1).data(Qt.UserRole)

        cursor = self.parent.cursor
        cursor.execute(f"SELECT * FROM dal_assets_ko WHERE id = ?", (asset_id,))

        asset_data = cursor.fetchone()

        edit_window = AddDefenseAssetWindow(self, edit_mode=True, asset_data=asset_data)
        if edit_window.exec_() == QDialog.Accepted:
            self.load_all_assets()

    def defense_asset_view_map(self):
        selected_assets = []
        for row in range(self.defense_asset_table.rowCount()):
            checkbox_widget = self.defense_asset_table.cellWidget(row, 0)
            if checkbox_widget.isChecked():
                asset_name = self.defense_asset_table.item(row, 3).text()
                coordinate = self.defense_asset_table.item(row, 4).text()
                mgrs = self.defense_asset_table.item(row, 5).text()
                weapon_system = self.defense_asset_table.item(row, 6).text()
                threat_degree = int(self.defense_asset_table.item(row, 8).text().replace("°", ""))  # 위협방위 정보 추가
                selected_assets.append((asset_name, coordinate, mgrs, weapon_system, threat_degree))

        if not selected_assets:
            QMessageBox.warning(self, self.tr("경고"), self.tr("선택된 자산이 없습니다."))
            return

        map_view = DefenseAssetMapView(selected_assets, self.parent.map_app.loadSettings())
        map_view.exec_()

    def add_defense_asset(self):
        add_defense_asset = AddDefenseAssetWindow(self)
        add_defense_asset.exec_()

    def print_defense_asset_table(self):
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

            rows = self.defense_asset_table.rowCount() + 1
            cols = self.defense_asset_table.columnCount()

            excluded_columns = [0]  # 체크박스 열 제외

            actual_cols = cols - len(excluded_columns)
            table = cursor.insertTable(rows, actual_cols, table_format)

            header_col = 0
            for col in range(cols):
                if col not in excluded_columns:
                    cell = table.cellAt(0, header_col)
                    cellCursor = cell.firstCursorPosition()
                    cellCursor.insertHtml(f"<th>{self.defense_asset_table.horizontalHeaderItem(col).text()}</th>")
                    header_col += 1

            for row in range(self.defense_asset_table.rowCount()):
                data_col = 0
                for col in range(cols):
                    if col not in excluded_columns:
                        item = self.defense_asset_table.item(row, col)
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

# MainWindow 클래스
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("DAL 관리"))
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
        self.defense_assets_page = ViewDefenseAssetWindow(self)
        self.centralWidget.addWidget(self.defense_assets_page)  # 이 줄을 추가

    def setupDatabase(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS dal_assets_ko (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit TEXT,
                    area TEXT,
                    asset_name TEXT,
                    coordinate TEXT,
                    mgrs TEXT,
                    weapon_system TEXT,
                    ammo_count INTEGER,
                    threat_degree INTEGER
                )
            ''')
            self.conn.commit()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS dal_assets_en (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit TEXT,
                    area TEXT,
                    asset_name TEXT,
                    coordinate TEXT,
                    mgrs TEXT,
                    weapon_system TEXT,
                    ammo_count INTEGER,
                    threat_degree INTEGER
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"테이블 생성 오류: {e}"))
            raise

    def mainPage(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(self.tr("DAL 관리 시스템"))
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QtGui.QFont("Arial", 24))
        layout.addWidget(title)
        manage_assets_button = QPushButton(self.tr("DAL 관리"))
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
