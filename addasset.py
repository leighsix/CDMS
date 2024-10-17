from PyQt5 import QtWidgets  # PyQt5 위젯 관련 모듈 가져오기
from PyQt5.QtWidgets import *  # 모든 PyQt5 위젯을 사용하기 위해
from PyQt5.QtCore import Qt, QTranslator  # Qt 및 QTranslator 사용
import sqlite3  # SQLite 데이터베이스와의 연결을 위한 모듈
import sys  # 시스템 관련 기능을 위한 모듈
from PyQt5 import QtGui  # PyQt5 GUI 기능 사용
from PyQt5.QtGui import QTextDocument, QTextCursor, QIcon, QPageLayout, QTextTableFormat, QTextTable, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from PyQt5.QtCore import QObject
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtWidgets import (QMessageBox, QFileDialog, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor, QTextTableFormat
from PyQt5.QtCore import Qt
import mgrs, re,json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt


class AddAssetWindow(QDialog, QObject):
    """자산 추가 및 수정 다이얼로그 클래스"""

    def __init__(self, parent, main_window=None, asset_id=None):
        super(AddAssetWindow, self).__init__(parent)  # 부모 클래스 초기화
        self.parent = parent  # 부모 위젯 참조
        self.edit_mode = False
        self.setWindowTitle(self.tr("CAL/DAL Management System"))  # 창 제목 설정
        self.setWindowIcon(QIcon("logo.png"))
        self.setMinimumSize(800, 600)  # 최소 크기 설정
        self.main_window = main_window  # 메인 윈도우 참조
        self.asset_id = asset_id  # 자산 ID (수정 시 사용)
        self.asset_info_fields = {}  # 자산 정보 필드를 저장할 딕셔너리
        self.checkboxes = {}  # 체크박스를 저장할 딕셔너리
        self.sections = []  # 체크박스 섹션 저장
        self.language = self.parent.selected_language
        if self.asset_id:
            self.set_data(self.asset_id)  # 자산 ID가 있는 경우 데이터 로드
        self.initUI()  # UI 초기화

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.setWindowTitle(self.tr("CAL/DAL Management System"))
        self.setWindowIcon(QIcon("logo.png"))

        # 좌측 레이아웃 (CAL 정보, DAL 정보, 교전효과 수준)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        asset_info_group = QGroupBox(self.tr("CAL 정보"))
        asset_info_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        asset_info_layout = QVBoxLayout(asset_info_group)

        self.asset_info_scroll = QScrollArea()
        self.asset_info_scroll.setWidgetResizable(True)
        asset_info_container = QWidget()
        asset_info_layout_main = QGridLayout(asset_info_container)
        asset_info_layout_main.setVerticalSpacing(20)
        asset_info_layout_main.setColumnStretch(1, 1)

        # 레이블 목록 정의
        labels = [
            self.tr("구성군"), self.tr("자산번호"),
            (self.tr("담당자"), self.tr("(영문)")),
            self.tr("연락처"),
            (self.tr("방어대상자산"), self.tr("(영문)")),
            (self.tr("지역구분"), self.tr("(영문)")),
            (self.tr("위도"), self.tr("경도")),
            self.tr("군사좌표(MGRS)"),
            self.tr("임무/기능(국/영문)"),  # 수정된 부분: 임무/기능 라벨을 별도로 처리
        ]

        row = 0
        for label in labels:
            if label == self.tr("임무/기능(국/영문)"):  # 수정된 부분: 임무/기능 라벨 처리
                label_widget = QLabel(label)
                label_widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
                label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                label_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 왼쪽 정렬
                asset_info_layout_main.addWidget(label_widget, row, 0, 1, 4)

                input_widget = QTextEdit()
                input_widget.setMinimumHeight(100)
                input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                asset_info_layout_main.addWidget(input_widget, row + 1, 0, 1, 4)  # 다음 줄에 입력창 배치
                self.asset_info_fields[label] = input_widget
                row += 2  # 두 줄을 사용했으므로 row 값을 2 증가

            else:
                if isinstance(label, tuple):  # tuple 형태 라벨 처리
                    label_widget = QLabel(label[0])  # 첫 번째 요소를 메인 라벨로 사용
                    sub_label_widget = QLabel(label[1])  # 두 번째 요소를 서브 라벨로 사용
                    input_widgets = []  # 입력 위젯 리스트 생성

                    for i, sub_label in enumerate(label):
                        if label == (self.tr("위도"), self.tr("경도")):
                            input_widget = CoordinateEdit(sub_label)
                            input_widget.editingFinished.connect(self.check_coordinates)
                        else:
                            input_widget = UnderlineEdit()
                        input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                        input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                        input_widgets.append(input_widget)

                    # QHBoxLayout을 사용하여 라벨과 입력 필드를 가로로 배치
                    hbox = QHBoxLayout()
                    hbox.setSpacing(0)  # 라벨과 입력창 사이의 간격 제거
                    hbox.setContentsMargins(0, 0, 0, 0)  # hbox의 내부 여백 제거
                    hbox.addWidget(label_widget)
                    hbox.addWidget(input_widgets[0])  # 첫 번째 입력 위젯 추가
                    hbox.addWidget(sub_label_widget)  # 서브 라벨 추가
                    hbox.addWidget(input_widgets[1])  # 두 번째 입력 위젯 추가

                    if label == (self.tr("위도"), self.tr("경도")):
                        self.lat_widget = input_widgets[0]
                        self.lon_widget = input_widgets[1]

                    self.asset_info_fields[label] = tuple(input_widgets)  # 입력 위젯 튜플 저장

                    for widget in [label_widget, sub_label_widget]:  # 라벨 스타일 설정
                        widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
                        widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                        widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 왼쪽 정렬

                    # 레이아웃에 추가 (hbox를 추가해야 함)
                    asset_info_layout_main.addLayout(hbox, row, 0, 1, 4)
                    row += 1

                else:  # 단일 라벨 처리
                    label_widget = QLabel(label)
                    label_widget.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
                    label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 크기 정책 설정
                    label_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 왼쪽 정렬

                    # 입력 필드 생성
                    if label == self.tr("구성군"):
                        # 콤보박스 생성
                        self.unit_combo = QComboBox()
                        self.unit_combo.addItems([self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
                        self.unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                        self.unit_combo.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                        input_widget = self.unit_combo
                    elif label == self.tr("군사좌표(MGRS)"):
                        input_widget = AutoSpacingLineEdit()
                        input_widget.setPlaceholderText("99A AA 99999 99999")
                    else:
                        input_widget = UnderlineEdit()

                    input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    input_widget.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    self.asset_info_fields[label] = input_widget

                    # QHBoxLayout을 사용하여 라벨과 입력 필드를 가로로 배치
                    hbox = QHBoxLayout()
                    hbox.setSpacing(0)  # 라벨과 입력창 사이의 간격 제거
                    hbox.setContentsMargins(0, 0, 0, 0)  # hbox의 내부 여백 제거
                    hbox.addWidget(label_widget)
                    hbox.addWidget(input_widget)

                    # 레이아웃에 추가 (hbox를 추가해야 함)
                    asset_info_layout_main.addLayout(hbox, row, 0, 1, 4)
                    row += 1

            asset_info_layout_main.setColumnStretch(0, 0)
            asset_info_layout_main.setColumnStretch(1, 1)
            asset_info_layout_main.setRowStretch(row - 1, 1)  # row 값 조정

            self.asset_info_scroll.setWidget(asset_info_container)
            asset_info_layout.addWidget(self.asset_info_scroll)

        # 방어자산(DAL) 정보 그룹
        dal_group = QGroupBox(self.tr("방어자산(DAL) 정보"))
        dal_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        dal_layout = QGridLayout(dal_group)

        self.dal_checkbox = QCheckBox(self.tr("방어자산(DAL)"))
        self.dal_checkbox.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight:bold;")
        self.dal_checkbox.stateChanged.connect(self.toggle_dal_fields)
        dal_layout.addWidget(self.dal_checkbox)

        # 무기체계 그룹 생성
        weapon_group = QGroupBox(self.tr("무기체계"))
        weapon_group.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
        weapon_layout = QGridLayout(weapon_group)

        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_systems = json.load(file)

        self.weapon_checkboxes = {}
        self.ammo_inputs = {}
        row = 0
        col = 0
        for weapon in weapon_systems:
            checkbox = QCheckBox(weapon)
            checkbox.setStyleSheet("font: 바른공군체; font-size: 14px;")
            ammo_input = QLineEdit()
            ammo_input.setPlaceholderText(self.tr("탄수"))
            ammo_input.setStyleSheet("font: 바른공군체; font-size: 14px;")
            ammo_input.setFixedWidth(50)
            ammo_input.setEnabled(False)

            checkbox.stateChanged.connect(lambda state, input=ammo_input: input.setEnabled(state == Qt.Checked))

            self.weapon_checkboxes[weapon] = checkbox
            self.ammo_inputs[weapon] = ammo_input

            hbox = QHBoxLayout()
            hbox.addWidget(checkbox)
            hbox.addWidget(ammo_input)
            hbox.addStretch()

            weapon_layout.addLayout(hbox, row, col)

            col += 1
            if col >= 2:
                col = 0
                row += 1

        dal_layout.addWidget(weapon_group)

        # 위협방위 입력 필드
        threat_degree_label = QLabel(self.tr("위협방위"))
        threat_degree_label.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight: bold;")
        self.threat_degree_edit = QLineEdit()
        self.threat_degree_edit.setStyleSheet("font: 바른공군체; font-size: 14px;")

        threat_hbox = QHBoxLayout()
        threat_hbox.addWidget(threat_degree_label)
        threat_hbox.addWidget(self.threat_degree_edit)
        threat_hbox.setAlignment(Qt.AlignLeft)

        # 새로운 QWidget을 생성하고 QHBoxLayout을 설정
        threat_widget = QWidget()
        threat_widget.setLayout(threat_hbox)

        # QWidget을 dal_layout에 추가
        dal_layout.addWidget(threat_widget)

        # 교전효과 수준 그룹
        engagement_group = QGroupBox(self.tr("교전효과 수준"))
        engagement_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")  # 그룹 박스 글꼴 설정
        engagement_layout = QVBoxLayout(engagement_group)

        self.engagement_combo = QComboBox()
        self.engagement_combo.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight:bold;")  # 콤보 박스 글꼴 설정
        self.engagement_combo.addItems([
            "",
            self.tr("1단계: 원격발사대"),
            self.tr("2단계: 단층방어"),
            self.tr("3단계: 중첩방어"),
            self.tr("4단계: 다층방어")
        ])
        engagement_layout.addWidget(self.engagement_combo)

        # 교전효과 수준 그룹
        bmd_priority_group = QGroupBox(self.tr("우선순위 고려사항"))
        bmd_priority_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")  # 그룹 박스 글꼴 설정
        bmd_priority_layout = QVBoxLayout(bmd_priority_group)

        self.bmd_priority_combo = QComboBox()
        self.bmd_priority_combo.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight:bold;")  # 콤보 박스 글꼴 설정
        self.bmd_priority_combo.addItems([
            "",
            self.tr("지휘통제시설"),
            self.tr("비행단"),
            self.tr("군수기지"),
            self.tr("해군기지"),
            self.tr("주요레이다")
        ])
        bmd_priority_layout.addWidget(self.bmd_priority_combo)


        # 왼쪽 레이아웃에 그룹 박스 추가
        left_layout.addWidget(asset_info_group)
        left_layout.addWidget(dal_group)
        left_layout.addWidget(engagement_group)
        left_layout.addWidget(bmd_priority_group)



        score_group = QGroupBox(self.tr("CVT 점수 평가"))
        score_group.setStyleSheet("background-color: white; font: 강한공군체; font-size: 20px; font-weight: bold;")
        score_layout = QVBoxLayout(score_group)
        score_group_main = QGroupBox(self.tr("CVT 점수 평가"))  # 내부 그룹 생성
        score_group_main.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        score_layout_main = QVBoxLayout(score_group_main)  # 그룹 레이아웃 생성


        # 점수 섹션 설정
        self.sections = [
            (self.tr("중요도"), [
                (self.tr("작전계획 실행 중단 초래"), 10.0),
                (self.tr("작전계획 실행 위험 초래"), 8.0),
                (self.tr("작전계획 중요 변경 초래"), 6.0),
                (self.tr("차기 작전계획 단계 실행 지연"), 4.0),
                (self.tr("임무전환/자산 위치 조정하기"), 2.0),
                (self.tr("중요도 가점(중심)"), [
                    (self.tr("작계 1,2,3단계의 중심"), 0.5)]),
                (self.tr("중요도 가점(기능)"), [
                    (self.tr("비전투원 후송작전 통제소, 양륙공항, 양륙항만"), 0.5)])
            ]),
            (self.tr("취약성"), [
                (self.tr("피해민감도"), [
                    (self.tr("방호강도"), [
                        (self.tr("시설의 29%미만으로 방호 가능"), 3.0),
                        (self.tr("시설의 30~74%로 방호 가능"), 2.0),
                        (self.tr("시설의 75%이상 방호 가능"), 1.0)
                    ]),
                    (self.tr("분산배치"), [
                        (self.tr("시설의 29%미만으로 분산 배치"), 3.0),
                        (self.tr("시설의 30~74%로 분산 배치"), 2.0),
                        (self.tr("시설의 75%이상 분산 배치"), 1.0)
                    ])
                ]),
                (self.tr("복구가능성"), [
                    (self.tr("복구시간"), [
                        (self.tr("7일 이상 또는 영구적 폐쇄"), 2.0),
                        (self.tr("1~7일 임시 폐쇄"), 1.5),
                        (self.tr("1일 이상 75~100% 임무제한"), 1.0),
                        (self.tr("1일 이상 25~74% 임무제한"), 0.5)
                    ]),
                    (self.tr("복구능력"), [
                        (self.tr("부대 25% 복원 능력"), 2.0),
                        (self.tr("부대 26~75% 복원 능력"), 1.5),
                        (self.tr("부대 100% 복원 능력"), 0.5)
                    ])
                ])
            ]),
            (self.tr("위협"), [
                (self.tr("공격가능성"), [
                    (self.tr("공격가능성 높음"), 5.0),
                    (self.tr("공격가능성 중간"), 3.0),
                    (self.tr("공격가능성 낮음"), 1.0)
                ]),
                (self.tr("탐지가능성"), [
                    (self.tr("탐지가능성 높음"), 5.0),
                    (self.tr("탐지 가능성 중간"), 3.0),
                    (self.tr("탐지 가능성 낮음"), 1.0)
                ])
            ])
        ]

        self.checkboxes = {}

        # 체크박스 추가 함수
        def add_checkboxes(layout, section, items):
            for item in items:
                if isinstance(item, tuple) and isinstance(item[1], (int, float)):
                    desc, score = item
                    checkbox = QCheckBox(f"{desc} ({score})")
                    checkbox.setStyleSheet("background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
                    checkbox.score = score
                    checkbox.section = section
                    checkbox.toggled.connect(lambda checked, cb=checkbox: self.checkbox_clicked(checked, cb))
                    layout.addWidget(checkbox, alignment=Qt.AlignLeft)
                    self.checkboxes[f"{section}_{desc}"] = checkbox
                elif isinstance(item, tuple) and isinstance(item[1], list):
                    sub_group_box = QGroupBox(item[0])
                    sub_group_box.setStyleSheet(
                        "background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
                    sub_group_layout = QVBoxLayout()
                    add_checkboxes(sub_group_layout, f"{section}_{item[0]}", item[1])
                    sub_group_box.setLayout(sub_group_layout)
                    layout.addWidget(sub_group_box)

        # 점수 평가 섹션에 대한 체크박스 추가
        for section, items in self.sections:
            group_box = QGroupBox(section)
            group_box.setStyleSheet("background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
            group_layout = QVBoxLayout()
            add_checkboxes(group_layout, section, items)
            group_box.setLayout(group_layout)
            score_layout.addWidget(group_box)

        score_group.setLayout(score_layout)  # 점수 그룹에 레이아웃 추가

        # 점수 레이아웃을 위한 스크롤 영역
        self.score_scroll = QScrollArea(self.parent)  # 부모를 score_group으로 변경
        self.score_scroll.setWidgetResizable(True)
        score_container = QWidget()
        score_container.setLayout(score_layout)
        self.score_scroll.setWidget(score_container)
        score_layout_main.addWidget(self.score_scroll)  # 점수 레이아웃에 스크롤 추가

        # # QSplitter를 사용하여 좌우 너비 조절 가능하게 설정
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(score_group_main)  # 스크롤 영역을 splitter에 추가
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        # 총합 점수 레이블 (높이 조절 및 스타일 변경)
        self.total_score_label = QLabel(self.tr("총합 점수: 0"))
        self.total_score_label.setFixedHeight(30)  # 높이 고정
        self.total_score_label.setStyleSheet(
            "font: '맑은 고딕'; font-size: 18px; font-weight: bold; color: #333; background-color: #f0f0f0; padding: 5px; border-radius: 5px;")  # 현대적인 스타일 적용

        # 메인 레이아웃에 위젯 추가
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.total_score_label)

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()  # 버튼 레이아웃 생성
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 10, 0, 10)

        self.save_button = QPushButton(self.tr("저장"), self)  # 저장 버튼
        self.save_button.setStyleSheet("font: 강한공군체; font-size: 18px; min-width: 150px;")
        self.save_button.clicked.connect(self.save_data)  # 클릭 시 데이터 저장

        # 기존 버튼 추가부분
        self.print_button = QPushButton(self.tr("출력"), self)  # 인쇄 버튼
        self.print_button.setStyleSheet("font: 강한공군체; font-size: 18px; min-width: 150px;")
        self.print_button.clicked.connect(self.print_data)  # 인쇄 버튼 클릭 시 인쇄 기능 실행

        self.back_button = QPushButton(self.tr("메인화면"), self)  # 메인 화면으로 돌아가기 버튼
        self.back_button.setStyleSheet("font: 강한공군체; font-size: 18px; min-width: 150px;")
        self.back_button.clicked.connect(self.parent.show_main_page)  # 클릭 시 메인 페이지로 돌아가기

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.print_button)  # 인쇄 버튼 추가
        button_layout.addWidget(self.back_button)

        for button in [self.save_button, self.print_button, self.back_button]:
            button.setStyleSheet("font: 강한공군체; font-size: 18px; min-width: 150px;")
            button.setFont(QFont("강한공군체", 15, QFont.Bold))
            button.setFixedSize(300, 50)
            button.setStyleSheet("QPushButton { text-align: center; }")


        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    # toggle_dal_fields 메서드 수정
    def toggle_dal_fields(self, state):
        is_enabled = state == Qt.Checked
        for checkbox in self.weapon_checkboxes.values():
            checkbox.setEnabled(is_enabled)
        self.threat_degree_edit.setEnabled(is_enabled)

    def convert_to_mgrs(self):
        lat_widget, lon_widget = self.asset_info_fields[(self.tr("위도"), self.tr("경도"))]
        lat_input = lat_widget.text()
        lon_input = lon_widget.text()

        # 입력 형식 검증
        lat_pattern = r'^[NS]\d{2}\.\d{5}'
        lon_pattern = r'^[EW]\d{3}\.\d{5}'

        if not re.match(lat_pattern, lat_input) or not re.match(lon_pattern, lon_input):
            QMessageBox.warning(self, "입력 오류",
                                "위도와 경도 형식이 올바르지 않습니다.\n올바른 형식: N##.######° 또는 S##.######°, E###.######° 또는 W###.######°")
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

    def refresh(self):
        self.reset_data()  # 기존의 reset_data 메서드 호출

    def checkbox_clicked(self, checked, clicked_checkbox):
        # 체크박스 클릭 시, 같은 섹션 내의 다른 체크박스를 해제
        if checked:
            for checkbox in self.checkboxes.values():
                if (
                        checkbox is not clicked_checkbox
                        and checkbox.section == clicked_checkbox.section
                        and checkbox.isChecked()
                ):
                    checkbox.setChecked(False)  # 다른 체크박스 해제
        self.calculate_total_score()  # 총 점수 계산

    def calculate_total_score(self):
        total_score = sum(checkbox.score for checkbox in self.checkboxes.values() if checkbox.isChecked())  # 총합 점수 계산
        self.total_score_label.setText(self.tr(f"총합 점수: {total_score}"))  # 총합 점수 레이블 업데이트

    def save_data(self):
        try:
            # 자산 정보 입력 필드에서 공백 체크
            for label, field in self.asset_info_fields.items():
                if isinstance(field, QTextEdit):
                    value = field.toPlainText().strip()
                elif isinstance(field, QLineEdit):
                    value = field.text().strip()
                else:
                    continue

                if not value and label != self.tr("임무/기능(국/영문)"):
                    QMessageBox.warning(self, self.tr("입력 오류"), self.tr(f"{label} 값을 입력하세요."))
                    return

            # 구성군 데이터 저장
            unit = self.unit_combo.currentText().strip()
            unit_tuple = self.getting_unit(unit)

            asset_data = {}
            for label, field in self.asset_info_fields.items():
                if isinstance(field, QTextEdit):
                    asset_data[label] = field.toPlainText().strip()
                elif isinstance(field, QLineEdit):
                    asset_data[label] = field.text().strip()
                elif isinstance(field, tuple):
                    asset_data[label] = tuple(
                        f.text().strip() if isinstance(f, QLineEdit) else f.toPlainText().strip() for f in field)
            # 경위도 검증
            lat_lon_key = (self.tr("위도"), self.tr("경도"))
            lat, lon = asset_data[lat_lon_key]
            if not self.validate_latitude(lat) or not self.validate_longitude(lon):
                QMessageBox.warning(self, self.tr("경고"), self.tr(
                    "올바른 경위도 형식을 입력해주세요.\n위도: N##.##### 또는 S##.#####\n경도: E###.##### 또는 W###.#####"))
                return

            lat_lon = f"{lat},{lon}"

            # DAL 관련 데이터 저장
            dal_select = self.dal_checkbox.isChecked()

            # 무기체계 및 탄약 수 처리
            weapon_system = []
            total_ammo = 0
            if dal_select:
                for weapon, checkbox in self.weapon_checkboxes.items():
                    if checkbox.isChecked():
                        ammo = self.ammo_inputs[weapon].text()
                        if ammo:
                            weapon_system.append(f"{weapon}({ammo})")
                            total_ammo += int(ammo)
            weapon_system_str = ", ".join(weapon_system) if weapon_system else None
            print(weapon_system_str)

            threat_degree = int(self.threat_degree_edit.text()) if dal_select and self.threat_degree_edit.text() else None
            print(threat_degree)

            # 교전효과 수준과 BMD 우선순위의 영문 버전 매핑
            engagement_effectiveness_ko = {
                "": "",
                "Level 1: Remote Launcher" : "1단계: 원격발사대",
                "Level 2: Single-layered Defense" : "2단계: 단층방어" ,
                "Level 3: Overlapping layered Defense" : "3단계: 중첩방어",
                "Level 4: Multi-layered Defense" : "4단계: 다층방어"
            }

            bmd_priority_ko = {
                "": "",
                "C2" : "지휘통제시설",
                "Fighter Group" : "비행단",
                "Logistics Base" : "군수기지",
                "Naval Base" : "해군기지",
                "Radar Site" : "주요레이다"
            }

            # 교전효과 수준과 BMD 우선순위의 영문 버전 매핑
            engagement_effectiveness_en = {
                "": "",
                "1단계: 원격발사대": "Level 1: Remote Launcher",
                "2단계: 단층방어": "Level 2: Single-layered Defense",
                "3단계: 중첩방어": "Level 3: Overlapping layered Defense",
                "4단계: 다층방어": "Level 4: Multi-layered Defense"
            }

            bmd_priority_en = {
                "": "",
                "지휘통제시설": "C2",
                "비행단": "Fighter Group",
                "군수기지": "Logistics Base",
                "해군기지": "Naval Base",
                "주요레이다": "Radar Site"
            }

            # engagement_effectiveness와 bmd_priority 처리 부분 수정
            if self.parent.selected_language == "ko" :
                engagement_effectiveness_ko = self.engagement_combo.currentText().strip()
                engagement_effectiveness_en = engagement_effectiveness_en.get(engagement_effectiveness_ko, '')
                print(engagement_effectiveness_en)
                if engagement_effectiveness_ko == '':
                    engagement_effectiveness_ko = None
                    engagement_effectiveness_en = None

                bmd_priority_ko = self.bmd_priority_combo.currentText().strip()
                bmd_priority_en = bmd_priority_en.get(bmd_priority_ko, '')
                if bmd_priority_ko == '':
                    bmd_priority_ko = None
                    bmd_priority_en = None

            else:
                engagement_effectiveness_en = self.engagement_combo.currentText().strip()
                engagement_effectiveness_ko = engagement_effectiveness_ko.get(engagement_effectiveness_en, '')
                if engagement_effectiveness_en == '':
                    engagement_effectiveness_ko = None
                    engagement_effectiveness_en = None

                bmd_priority_en = self.bmd_priority_combo.currentText().strip()
                bmd_priority_ko = bmd_priority_ko.get(bmd_priority_en, '')
                if bmd_priority_en == '':
                    bmd_priority_ko = None
                    bmd_priority_en = None

            scores_data = {}
            for section, items in self.sections:
                for item in items:
                    if isinstance(item, tuple) and isinstance(item[1], (int, float)):
                        checkbox = self.checkboxes.get(section + "_" + item[0])
                        if checkbox is not None:
                            if checkbox.isChecked():
                                scores_data[section] = scores_data.get(section, 0) + item[1]
                    elif isinstance(item[1], list):
                        for item_section, ite in [item]:
                            for it in ite:
                                if isinstance(it, tuple) and isinstance(it[1], (int, float)):
                                    checkbox = self.checkboxes.get(section + "_" + item_section + "_" + it[0])
                                    if checkbox is not None:
                                        if checkbox.isChecked():
                                            scores_data[section + "_" + item_section] = scores_data.get(
                                                section + "_" + item_section, 0) + it[1]

                                elif isinstance(it[1], list):
                                    for ite_section, i in [it]:
                                        for j in i:
                                            if isinstance(j, tuple) and isinstance(j[1], (int, float)):
                                                checkbox = self.checkboxes.get(
                                                    section + "_" + item_section + "_" + ite_section + "_" + j[0])
                                                if checkbox is not None:
                                                    if checkbox.isChecked():
                                                        scores_data[
                                                            section + "_" + item_section + "_" + ite_section] = \
                                                            scores_data.get(
                                                                section + "_" + item_section + "_" + ite_section,
                                                                0) + j[1]

            # 데이터베이스에 저장 시 None을 0으로 채움
            for score_key in scores_data:
                if scores_data[score_key] is None:  # 만약 값이 None이라면
                    scores_data[score_key] = 0  # 0으로 설정

            # asset_id로 기존 자산 확인
            self.parent.cursor.execute(f"SELECT id FROM cal_assets_{self.parent.selected_language} WHERE id=?",
                                       (self.asset_id,))
            existing_asset = self.parent.cursor.fetchone()

            if self.edit_mode and existing_asset:
                # UPDATE 쿼리 (한국어 테이블)
                self.parent.cursor.execute(f'''
                    UPDATE cal_assets_ko SET
                        unit=?, asset_number=?, manager=?, contact=?, target_asset=?,
                        area=?, coordinate=?, mgrs=?, description=?,
                        dal_select=?, weapon_system=?, ammo_count=?, threat_degree=?, engagement_effectiveness=?, bmd_priority=?,
                        criticality=?, criticality_bonus_center=?, criticality_bonus_function=?, 
                        vulnerability_damage_protection=?, vulnerability_damage_dispersion=?, 
                        vulnerability_recovery_time=?, vulnerability_recovery_ability=?, 
                        threat_attack=?, threat_detection=?
                    WHERE id=?
                ''', (
                    unit_tuple[0], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][0],
                    asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], lat_lon,
                    asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    dal_select, weapon_system_str, total_ammo, threat_degree, engagement_effectiveness_ko, bmd_priority_ko,
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                    self.asset_id
                ))

                # UPDATE 쿼리 (영어 테이블)
                self.parent.cursor.execute(f'''
                    UPDATE cal_assets_en SET
                        unit=?, asset_number=?, manager=?, contact=?, target_asset=?,
                        area=?, coordinate=?, mgrs=?, description=?,
                        dal_select=?, weapon_system=?, ammo_count=?, threat_degree=?, engagement_effectiveness=?, bmd_priority=?,
                        criticality=?, criticality_bonus_center=?, criticality_bonus_function=?, 
                        vulnerability_damage_protection=?, vulnerability_damage_dispersion=?, 
                        vulnerability_recovery_time=?, vulnerability_recovery_ability=?, 
                        threat_attack=?, threat_detection=?
                    WHERE id=?
                ''', (
                    unit_tuple[1], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][1],
                    asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1], lat_lon,
                    asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    dal_select, weapon_system_str, total_ammo, threat_degree, engagement_effectiveness_en, bmd_priority_en,
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                    self.asset_id
                ))

                QMessageBox.information(self, self.tr("성공"), self.tr("자산 정보가 수정되었습니다!"))
            else:  # 해당 자산이 없으면 새로 추가
                # INSERT 쿼리
                # 기존 자산이 없을 경우, 새로운 id 생성
                self.parent.cursor.execute("SELECT MAX(id) FROM cal_assets_ko")
                self.parent.cursor.execute("SELECT MAX(id) FROM cal_assets_en")
                max_id = self.parent.cursor.fetchone()[0]
                new_id = 1 if max_id is None else max_id + 1

                # INSERT 쿼리 수정
                self.parent.cursor.execute(f'''
                    INSERT INTO cal_assets_ko(
                        id, unit, asset_number, manager, contact, target_asset,
                        area, coordinate, mgrs, description,
                        dal_select, weapon_system, ammo_count, threat_degree, engagement_effectiveness, bmd_priority,
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_id, unit_tuple[0], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][0], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    dal_select, weapon_system_str, total_ammo, threat_degree, engagement_effectiveness_ko, bmd_priority_ko,
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                ))
                # INSERT 쿼리 수정
                self.parent.cursor.execute(f'''
                    INSERT INTO cal_assets_en(
                        id, unit, asset_number, manager, contact, target_asset,
                        area, coordinate, mgrs, description,
                        dal_select, weapon_system, ammo_count, threat_degree, engagement_effectiveness, bmd_priority,
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_id, unit_tuple[1], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][1], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    dal_select, weapon_system_str, total_ammo, threat_degree, engagement_effectiveness_en, bmd_priority_en,
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                ))
                QMessageBox.information(self, self.tr("성공"), self.tr("자산 및 CVT 점수 저장 성공!"))  # 성공 메시지
            self.parent.conn.commit()  # 변경사항 커밋
            self.parent.show_cal_view_page()

        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"오류 발생: {e}"))  # 데이터베이스 오류 처리
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"예기치 않은 오류 발생: {str(e)}"))

    def set_data(self, asset_id):
        self.asset_id = asset_id
        self.parent.cursor.execute(f"SELECT * FROM cal_assets_{self.parent.selected_language} WHERE id=?", (asset_id,))
        asset_data = self.parent.cursor.fetchone()
        if asset_data:
            self.reset_data()  # 먼저 모든 필드를 초기화

            # 구성군(콤보박스 특성)
            self.unit_combo.setCurrentText(asset_data[1])

            for label, field in self.asset_info_fields.items():
                if isinstance(field, tuple):
                    if label == (self.tr("담당자"), self.tr("(영문)")):
                        field[0].setText(asset_data[3])
                        field[1].setText(asset_data[3])  # 영문 테이블에서 가져와야 함
                    elif label == (self.tr("방어대상자산"), self.tr("(영문)")):
                        field[0].setText(asset_data[5])
                        field[1].setText(asset_data[5])  # 영문 테이블에서 가져와야 함
                    elif label == (self.tr("지역구분"), self.tr("(영문)")):
                        field[0].setText(asset_data[6])
                        field[1].setText(asset_data[6])  # 영문 테이블에서 가져와야 함
                    elif label == (self.tr("위도"), self.tr("경도")):
                        lat, lon = asset_data[7].split(',')
                        field[0].setText(lat.strip())
                        field[1].setText(lon.strip())
                else:
                    if label == self.tr("자산번호"):
                        field.setText(str(asset_data[2]))
                    elif label == self.tr("연락처"):
                        field.setText(asset_data[4])
                    elif label == self.tr("군사좌표(MGRS)"):
                        field.setText(asset_data[8])
                    elif label == self.tr("임무/기능(국/영문)"):
                        field.setPlainText(asset_data[9])

            # DAL 정보 설정
            self.dal_checkbox.setChecked(asset_data[10])
            if asset_data[11]:  # weapon_system
                weapons = asset_data[11].split(', ')
                for weapon in weapons:
                    weapon_name, ammo = weapon.split('(')
                    ammo = ammo.rstrip(')')
                    if weapon_name in self.weapon_checkboxes:
                        self.weapon_checkboxes[weapon_name].setChecked(True)
                        self.ammo_inputs[weapon_name].setText(ammo)
            self.threat_degree_edit.setText(str(asset_data[13]) if asset_data[13] is not None else "")

            # 지휘관 지침 관련 설정
            self.engagement_combo.setCurrentText(asset_data[14] if asset_data[14] is not None else "")
            self.bmd_priority_combo.setCurrentText(asset_data[15] if asset_data[15] is not None else "")

            # 체크박스 상태 설정
            self.set_checkbox_state(self.tr("중요도"), asset_data[16])
            self.set_checkbox_state(self.tr("중요도_중요도 가점(중심)"), asset_data[17])
            self.set_checkbox_state(self.tr("중요도_중요도 가점(기능)"), asset_data[18])
            self.set_checkbox_state(self.tr("취약성_피해민감도_방호강도"), asset_data[19])
            self.set_checkbox_state(self.tr("취약성_피해민감도_분산배치"), asset_data[20])
            self.set_checkbox_state(self.tr("취약성_복구가능성_복구시간"), asset_data[21])
            self.set_checkbox_state(self.tr("취약성_복구가능성_복구능력"), asset_data[22])
            self.set_checkbox_state(self.tr("위협_공격가능성"), asset_data[23])
            self.set_checkbox_state(self.tr("위협_탐지가능성"), asset_data[24])

    def set_edit_mode(self, edit_mode):
        self.edit_mode = edit_mode
        # 편집 모드에 따라 UI 조정 (예: 버튼 텍스트 변경)
        if edit_mode:
            self.save_button.setText(self.tr("수정"))
        else:
            self.save_button.setText(self.tr("저장"))

    def reset_data(self):
        """모든 입력 필드와 체크박스를 초기화합니다."""
        # 자산 ID 초기화
        self.asset_id = None
        # 구성군 콤보박스 초기화
        self.unit_combo.setCurrentIndex(0)

        # 모든 입력 필드 초기화
        for label, field in self.asset_info_fields.items():
            if isinstance(field, tuple):
                for f in field:
                    if isinstance(f, QLineEdit):
                        f.clear()
                    elif isinstance(f, QTextEdit):
                        f.clear()
            else:
                if isinstance(field, QTextEdit):
                    field.clear()
                elif isinstance(field, QLineEdit):
                    field.clear()
                elif isinstance(field, QComboBox):
                    field.setCurrentIndex(0)

        # 모든 체크박스 초기화
        self.reset_checkboxes()

        # DAL 관련 필드 초기화
        for ammo_input in self.ammo_inputs.values():
            ammo_input.clear()
        self.threat_degree_edit.clear()
        self.engagement_combo.setCurrentIndex(0)
        self.bmd_priority_combo.setCurrentIndex(0)

    def reset_checkboxes(self):
        """모든 체크박스를 초기화(체크 해제)합니다."""
        self.dal_checkbox.setChecked(False)
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)  # 모든 체크박스를 체크 해제
        for checkbox in self.weapon_checkboxes.values():
            checkbox.setChecked(False)

    def set_checkbox_state(self, section_key, score):
        for section, items in self.sections:
            for item in items:
                if isinstance(item, tuple) and isinstance(item[1], (int, float)):
                    checkbox = self.checkboxes.get(section_key + "_" + item[0])
                    if checkbox:
                        if score == item[1]:
                            checkbox.setChecked(True)  # 체크
                elif isinstance(item[1], list):
                    for item_section, ite in [item]:
                        for it in ite:
                            if isinstance(it, tuple) and isinstance(it[1], (int, float)):
                                checkbox = self.checkboxes.get(section_key + "_" + it[0])
                                if checkbox:
                                    if score == it[1]:
                                        checkbox.setChecked(True)  # 체크
                            elif isinstance(it[1], list):
                                for ite_section, i in [it]:
                                    for j in i:
                                        if isinstance(j, tuple) and isinstance(j[1], (int, float)):
                                            checkbox = self.checkboxes.get(section_key + "_" + j[0])
                                            if checkbox:
                                                if score == j[1]:
                                                    checkbox.setChecked(True)  # 체크

    def print_data(self):
        try:
            document = QTextDocument()
            cursor = QTextCursor(document)

            # 전체 문서 스타일 설정
            document.setDefaultStyleSheet("""
                body { font-family: Arial, sans-serif; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid black; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
                h1, h2 { text-align: center; }
                .section { font-size: 14pt; font-weight: bold; padding-top: 20px; }
                .subsection { font-size: 12pt; font-weight: bold; padding-top: 10px; }
                .checkbox { font-family: 'Arial Unicode MS', sans-serif; }
                .item { width: 70%; }
                .score { width: 15%; text-align: center; }
                .check { width: 15%; text-align: center; }
            """)

            # 공통 스타일
            table_style = "style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'"
            th_style = "style='border: 1px solid black; padding: 8px; background-color: #f2f2f2;'"
            td_style = "style='border: 1px solid black; padding: 8px;'"
            evaluation_data = self.tr('자산 CVT 평가자료')
            # 제목 추가 (중앙 정렬)
            cursor.insertHtml(f"<h1>{evaluation_data}</h1>")
            # 제목과 자산정보 사이에 공간 추가
            cursor.insertHtml("<br><br>")

            # 자산 정보 섹션
            assets_info = self.tr('자산정보')
            coordinate = self.tr("경위도")
            lang = 0 if self.parent.selected_language == 'ko' else 1
            cursor.insertHtml(f"<h2>{assets_info}</h2>")
            cursor.insertHtml(f"<table {table_style}>")
            # 구성군 정보 추가
            cursor.insertHtml(f"<tr><th {th_style} width='30%'>{self.tr('구성군')}</th>"
                              f"<td {td_style} width='70%'>{self.unit_combo.currentText().strip()}</td></tr>")
            for label, field in self.asset_info_fields.items():
                if isinstance(label, tuple):
                    if label == (self.tr("위도"), self.tr("경도")):
                        lat, lon = field
                        value = f"{lat.text().strip()}, {lon.text().strip()}"
                        cursor.insertHtml(f"<tr><th {th_style} width='30%'>{coordinate}</th>"
                                      f"<td {td_style} width='70%'>{value.strip()}</td></tr>")
                    else:
                        selected_field = field[0] if self.parent.selected_language == 'ko' else field[1]
                        if isinstance(selected_field, QLineEdit):
                            value = selected_field.text().strip()
                        else:
                            value = selected_field.toPlainText().strip()
                        cursor.insertHtml(f"<tr><th {th_style} width='30%'>{self.tr(label[lang])}</th>"
                                      f"<td {td_style} width='70%'>{value.strip()}</td></tr>")
                else:
                    if isinstance(field, QLineEdit):
                        value = field.text()
                    elif isinstance(field, QTextEdit):
                        value = field.toPlainText()
                    else:
                        value = str(field)  # 다른 타입의 필드 처리
                    cursor.insertHtml(f"<tr><th {th_style} width='30%'>{self.tr(label)}</th>"
                                      f"<td {td_style} width='70%'>{value.strip()}</td></tr>")

            cursor.insertHtml("</table>")
            cursor.insertHtml("<br><br>")

            # CVT 점수 평가 섹션
            score_evaluation = self.tr('CVT 점수평가')
            total_score_table = self.tr('총계')
            importance_table = self.tr('중요도')
            vulnerability_table = self.tr('취약성')
            threat_table = self.tr('위협')
            table_items = self.tr('항목')
            table_scores = self.tr('점수')
            cursor.insertHtml(f"<h2>{score_evaluation}</h2>")
            total_score, importance_score, vulnerability_score, threat_score = self.summarize_score()

            # 점수 요약 표 생성
            cursor.insertHtml("<table>")
            cursor.insertHtml(
                f"<tr><th width='20%'>{table_items}</th><th width='20%'>{total_score_table}</th><th width='20%'>{importance_table}</th><th width='20%'>{vulnerability_table}</th><th width='20%'>{threat_table}</th></tr>")
            cursor.insertHtml(
                f"<tr><td width='20%'>{table_scores}</td><td width='20%'>{total_score}</td><td width='20%'>{importance_score}</td><td width='20%'>{vulnerability_score}</td><td width='20%'>{threat_score}</td></tr>")
            cursor.insertHtml("</table>")
            cursor.insertHtml("<br><br>")

            # 중요도 섹션
            self.add_criticality_section(cursor)
            cursor.insertHtml("<br><br>")
            # 취약성 섹션
            self.add_vulnerability_section(cursor)
            cursor.insertHtml("<br><br>")

            # 위협 섹션
            self.add_threat_section(cursor)

            # 미리보기 및 저장 로직
            preview = QPrintPreviewDialog()
            preview.setWindowIcon(QIcon("image/logo.png"))
            preview.paintRequested.connect(lambda p: document.print_(p))
            preview.exec_()

            file_path, _ = QFileDialog.getSaveFileName(self, self.tr("PDF 저장"), "", "PDF Files (*.pdf)")
            if file_path:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                printer.setPageOrientation(QPageLayout.Landscape)
                document.print_(printer)
                QMessageBox.information(self, self.tr("저장 완료"), self.tr("자산 보고서가 {} 파일로 저장되었습니다.").format(file_path))

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr("보고서 생성 중 오류가 발생했습니다: {}").format(str(e)))

    def summarize_score(self):
        total_score = 0
        importance_score = 0
        vulnerability_score = 0
        threat_score = 0

        for checkbox_name, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                if checkbox_name.startswith("중요도"):
                    importance_score += checkbox.score
                elif checkbox_name.startswith("취약성"):
                    vulnerability_score += checkbox.score
                elif checkbox_name.startswith("위협"):
                    threat_score += checkbox.score

        total_score = importance_score + vulnerability_score + threat_score
        return total_score, importance_score, vulnerability_score, threat_score

    def add_criticality_section(self, cursor):
        cursor.insertHtml(f"<h3>{self.tr(self.sections[0][0])}</h3>")

        # 공통 스타일
        table_style = "style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'"
        th_style = "style='border: 1px solid black; padding: 8px; background-color: #f2f2f2;'"
        td_style = "style='border: 1px solid black; padding: 8px;'"

        # 메인 중요도 테이블
        table_items = self.tr('항목')
        table_scores = self.tr('점수')
        table_checks = self.tr('체크')
        cursor.insertHtml(f"<table {table_style}>")
        cursor.insertHtml(
            f"<tr><th {th_style} width='70%'align='center'>{table_items}</th><th {th_style} width='15%' align='center'>{table_scores}</th><th {th_style} width='15%' align='center'>{table_checks}</th></tr>")
        for item, score in self.sections[0][1]:
            if isinstance(score, (int, float)):
                checkbox = self.checkboxes.get(self.sections[0][0] + "_" + item)
                checkbox = "☑" if checkbox.isChecked() else "☐"
                cursor.insertHtml(
                    f"<tr><td {td_style} width='70%'>{self.tr(item)}</td><td {td_style} width='15%' align='center'>{score}</td><td {td_style} width='15%' align='center'>{checkbox}</td></tr>")
        cursor.insertHtml("</table>")
        cursor.insertHtml("<br><br>")

        # 중요도 가점 테이블들
        for subsection in self.sections[0][1]:
            if isinstance(subsection[1], list):
                cursor.insertHtml(f"<h4>{self.tr(subsection[0])}</h4>")
                cursor.insertHtml(f"<table {table_style}>")
                cursor.insertHtml(
                    f"<tr><th {th_style} width='70%'align='center'>{table_scores}</th><th {th_style} width='15%'align='center'>{table_scores}</th><th {th_style} width='15%'align='center'>{table_checks}</th></tr>")
                for item, score in subsection[1]:
                    checkbox = self.checkboxes.get(self.sections[0][0] + "_" + subsection[0] + "_" + item)
                    checkbox = "☑" if checkbox.isChecked() else "☐"
                    cursor.insertHtml(
                        f"<tr><td {td_style} width='70%'>{self.tr(item)}</td><td {td_style} width='15%' align='center'>{score}</td><td {td_style} width='15%' align='center'>{checkbox}</td></tr>")
                cursor.insertHtml("</table>")
                cursor.insertHtml("<br><br>")

    def add_vulnerability_section(self, cursor):
        cursor.insertHtml(f"<h3>{self.tr(self.sections[1][0])}</h3>")
        cursor.insertHtml("<br><br>")
        # 공통 스타일
        table_style = "style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'"
        th_style = "style='border: 1px solid black; padding: 8px; background-color: #f2f2f2;'"
        td_style = "style='border: 1px solid black; padding: 8px;'"
        table_items = self.tr('항목')
        table_scores = self.tr('점수')
        table_checks = self.tr('체크')

        for subsection in self.sections[1][1]:
            for item, scores in subsection[1]:
                cursor.insertHtml(f"<h4>{self.tr(self.sections[1][0] + '_' + subsection[0] + '_' + item)}</h4>")
                cursor.insertHtml(f"<table {table_style}>")
                cursor.insertHtml(
                    f"<tr><th {th_style} width='70%'align='center'>{table_items}</th><th {th_style} width='15%'align='center'>{table_scores}</th><th {th_style} width='15%'align='center'>{table_checks}</th></tr>")
                for ite, score in scores:
                    checkbox = self.checkboxes.get(self.sections[1][0] + "_" + subsection[0] + "_" + item + "_" + ite)
                    checkbox = "☑" if checkbox.isChecked() else "☐"
                    cursor.insertHtml(
                        f"<tr><td {td_style} width='70%'>{self.tr(ite)}</td><td {td_style} width='15%' align='center'>{score}</td><td {td_style} width='15%' align='center'>{checkbox}</td></tr>")
                cursor.insertHtml("</table>")
                cursor.insertHtml("<br><br>")

        # 테이블 간 간격 추가
        cursor.insertHtml("<br><br>")

    def add_threat_section(self, cursor):
        cursor.insertHtml(f"<h3>{self.tr(self.sections[2][0])}</h3>")
        cursor.insertHtml("<br><br>")
        # 공통 스타일
        table_style = "style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'"
        th_style = "style='border: 1px solid black; padding: 8px; background-color: #f2f2f2;'"
        td_style = "style='border: 1px solid black; padding: 8px;'"
        table_items = self.tr('항목')
        table_scores = self.tr('점수')
        table_checks = self.tr('체크')

        for subsection in self.sections[2][1]:
            cursor.insertHtml(f"<h4>{self.tr(self.sections[2][0] + '_' + subsection[0])}</h4>")
            cursor.insertHtml(f"<table {table_style}>")
            cursor.insertHtml(
                f"<tr><th {th_style} width='70%' align='center'>{table_items}</th><th {th_style} width='15%' align='center'>{table_scores}</th><th {th_style} width='15%' align='center'>{table_checks}</th></tr>")
            for item, score in subsection[1]:
                checkbox = self.checkboxes.get(self.sections[2][0] + "_" + subsection[0] + "_" + item)
                checkbox = "☑" if checkbox.isChecked() else "☐"
                cursor.insertHtml(
                    f"<tr><td {td_style} width='70%'>{self.tr(item)}</td><td {td_style} width='15%' align='center'>{score}</td><td {td_style} width='15%' align='center'>{checkbox}</td></tr>")
            cursor.insertHtml("</table>")
            cursor.insertHtml("<br><br>")

        # 테이블 간 간격 추가
        cursor.insertHtml("<br>")

    @staticmethod
    def validate_latitude(lat):
        pattern = r'^[NS]\d{2}\.\d{5}'
        return bool(re.match(pattern, lat))

    @staticmethod
    def validate_longitude(lon):
        pattern = r'^[EW]\d{3}\.\d{5}'
        return bool(re.match(pattern, lon))

    def check_coordinates(self):
        if hasattr(self, 'lat_widget') and hasattr(self, 'lon_widget'):
            if self.lat_widget.text() and self.lon_widget.text():
                self.convert_to_mgrs()

class UnderlineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 1px solid black;
                background-color: transparent;
                padding: 2px;
            }
        """)

class AutoSpacingLineEdit(UnderlineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.format_text)
        self.setMaxLength(19)  # 공백 포함 19자 (실제 문자는 15자)

    def format_text(self):
        cursor_pos = self.cursorPosition()
        text = self.text().replace(" ", "")[:15]  # 최대 15자로 제한
        formatted_text = ""
        space_count = 0
        for i, char in enumerate(text):
            if i in [3, 5, 10]:  # 공백 위치 조정
                formatted_text += " "
                space_count += 1
            formatted_text += char

        self.blockSignals(True)
        self.setText(formatted_text)
        self.blockSignals(False)

        # 커서 위치 조정
        if cursor_pos <= len(text):
            new_cursor_pos = cursor_pos + sum(1 for x in [3, 5, 10] if x < cursor_pos)
        else:
            new_cursor_pos = len(formatted_text)

        self.setCursorPosition(new_cursor_pos)

class MainWindow(QtWidgets.QMainWindow):
    """메인 창 클래스"""
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(self.tr("자산 관리"))  # 창 제목 설정
        self.setMinimumSize(1024, 768)  # 최소 크기 설정
        self.selected_language = "ko"
        self.db_path = 'assets_management.db'
        self.conn = sqlite3.connect(self.db_path)  # 데이터베이스 연결
        self.cursor = self.conn.cursor()  # 커서 생성

        self.sections = [  # 평가 항목 설정
            (self.tr("중요도"), [
                (self.tr("작전계획 실행 중단 초래"), 10.0),
                (self.tr("작전계획 실행 위험 초래"), 8.0),
                (self.tr("작전계획 중요 변경 초래"), 6.0),
                (self.tr("차기 작전계획 단계 실행 지연"), 4.0),
                (self.tr("임무전환/자산 위치 조정하기"), 2.0),
                (self.tr("중요도 가점(중심)"), [
                    (self.tr("작계 1,2,3단계의 중심"), 0.5)]),
                (self.tr("중요도 가점(기능)"), [
                    (self.tr("비전투원 후송작전 통제소, 양륙공항, 양륙항만"), 0.5)])
            ]),
            (self.tr("취약성"), [
                (self.tr("피해민감도"), [
                    (self.tr("방호강도"), [
                        (self.tr("시설의 29%미만으로 방호 가능"), 3),
                        (self.tr("시설의 30~74%로 방호 가능"), 2),
                        (self.tr("시설의 75%이상 방호 가능"), 1)
                    ]),
                    (self.tr("분산배치"), [
                        (self.tr("시설의 29%미만으로 분산 배치"), 3),
                        (self.tr("시설의 30~74%로 분산 배치"), 2),
                        (self.tr("시설의 75%이상 분산 배치"), 1)
                    ])
                ]),
                (self.tr("복구가능성"), [
                    (self.tr("복구 시간"), [
                        (self.tr("7일 이상 또는 영구적 폐쇄"), 2),
                        (self.tr("1~7일 임시 폐쇄"), 1.5),
                        (self.tr("1일 이상 75~100% 임무제한"), 1),
                        (self.tr("1일 이상 25~74% 임무제한"), 0.5)
                    ]),
                    (self.tr("복구 능력"), [
                        (self.tr("부대 25% 복원 능력"), 2),
                        (self.tr("부대 26~75% 복원 능력"), 1.5),
                        (self.tr("부대 100% 복원 능력"), 0.5)
                    ])
                ])
            ]),
            (self.tr("위협"), [
                (self.tr("공격가능성"), [
                    (self.tr("공격가능성 높음"), 5),
                    (self.tr("공격가능성 중간"), 3),
                    (self.tr("공격가능성 낮음"), 1)
                ]),
                (self.tr("탐지 가능성"), [
                    (self.tr("탐지가능성 높음"), 5),
                    (self.tr("탐지가능성 중간"), 3),
                    (self.tr("탐지가능성 낮음"), 1)
                ])
            ])
        ]

        self.initDB()  # 데이터베이스 초기화

        self.centralWidget = QtWidgets.QStackedWidget()  # 스택형 위젯 생성
        self.setCentralWidget(self.centralWidget)  # 중앙 위젯 설정

        self.mainPage()  # 메인 페이지 생성
        self.addAssetPage()  # 자산 추가 페이지 생성

    def initDB(self):
        # 데이터베이스 테이블 생성
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS cal_assets_ko (
        id INTEGER PRIMARY KEY,
        unit TEXT,
        asset_number INT,
        manager TEXT,
        contact TEXT,
        target_asset TEXT,
        area TEXT,
        coordinate TEXT,
        mgrs TEXT,
        description TEXT,
        dal_select BOOL,
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
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS cal_assets_en (
        id INTEGER PRIMARY KEY,
        unit TEXT,
        asset_number INT,
        manager TEXT,
        contact TEXT,
        target_asset TEXT,
        area TEXT,
        coordinate TEXT,
        mgrs TEXT,
        description TEXT,
        dal_select BOOL,
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
        self.conn.commit()  # 변경사항 커밋

    def mainPage(self):
        # 메인 페이지 구성
        page = QWidget()
        layout = QVBoxLayout()  # 수직 레이아웃 생성
        layout.setAlignment(Qt.AlignCenter)  # 중앙 정렬

        title = QLabel(self.tr("자산 관리 시스템"))  # 제목 레이블
        title.setStyleSheet("font-size: 30px; font-family: Arial;")  # 제목 스타일 설정
        layout.addWidget(title)  # 제목 추가

        add_asset_button = QPushButton(self.tr("자산 추가"))  # 자산 추가 버튼
        add_asset_button.setStyleSheet("padding: 20px; font-size: 20px;")  # 스타일 설정
        add_asset_button.clicked.connect(self.show_add_asset_page)  # 클릭 시 자산 추가 페이지로 이동
        layout.addWidget(add_asset_button)  # 버튼 추가

        page.setLayout(layout)  # 페이지 레이아웃 설정
        self.centralWidget.addWidget(page)  # 중앙 위젯에 페이지 추가

    def addAssetPage(self):
        # 자산 추가 페이지 설정
        self.add_asset_win = AddAssetWindow(self)  # AddAssetWindow 인스턴스 생성
        self.centralWidget.addWidget(self.add_asset_win)  # 중앙 위젯에 추가

    def show_add_asset_page(self):
        # 자산 추가 페이지 표시
        self.centralWidget.setCurrentWidget(self.add_asset_win)  # 자산 추가 페이지로 전환

    def show_main_page(self):
        # 메인 페이지 표시
        self.centralWidget.setCurrentIndex(0)  # 인덱스 0의 페이지로 전환

    def refresh_database(self):
        """데이터베이스 연결을 새로 고치기 위한 메서드"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def load_assets(self):
        self.centralWidget.setCurrentIndex(0)  # 인덱스 0의 페이지로 전환

    def show_view_assets_page(self):
        self.centralWidget.setCurrentIndex(0)  # 인덱스 0의 페이지로 전환

class CoordinateEdit(UnderlineEdit):
    def __init__(self, coordinate_type, parent=None):
        super().__init__(parent)
        self.coordinate_type = coordinate_type
        self.setPlaceholderText(f"예: {'N39.99999' if coordinate_type == '위도' else 'E128.99999'}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)  # QApplication 인스턴스 생성
    app.setFont(QtGui.QFont("강한공군체", 12, QtGui.QFont.Bold))
    win = MainWindow()  # 메인 윈도우 인스턴스 생성
    win.show()  # 윈도우 표시
    sys.exit(app.exec_())  # 애플리케이션 실행
