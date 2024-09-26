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
import mgrs, re
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt


class AddAssetWindow(QDialog, QObject):
    """자산 추가 및 수정 다이얼로그 클래스"""

    def __init__(self, parent, main_window=None, asset_id=None):
        super(AddAssetWindow, self).__init__(parent)  # 부모 클래스 초기화
        self.parent = parent  # 부모 위젯 참조
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
            self.load_asset_data()  # 자산 ID가 있는 경우 데이터 로드
        self.initUI()  # UI 초기화

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.setWindowTitle(self.tr("CAL/DAL Management System"))
        self.setWindowIcon(QIcon("logo.png"))

        asset_info_group = QGroupBox(self.tr("자산 CVT 평가자료"))
        asset_info_group.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        asset_info_layout = QVBoxLayout(asset_info_group)

        self.asset_info_scroll = QScrollArea()
        self.asset_info_scroll.setWidgetResizable(True)
        asset_info_container = QWidget()
        asset_info_layout_main = QGridLayout(asset_info_container)
        asset_info_layout_main.setVerticalSpacing(20)  # 수직 간격 설정
        asset_info_layout_main.setColumnStretch(1, 1)  # 두 번째 열(입력 필드)에 더 많은 공간 할당

        # 레이블 목록 정의
        labels = [
            self.tr("구성군"), self.tr("자산번호"),
            (self.tr("담당자"), self.tr("(영문)")),
            self.tr("연락처"),
            (self.tr("방어대상자산"), self.tr("(영문)")),
            (self.tr("지역구분"), self.tr("(영문)")),
            (self.tr("위도"), self.tr("경도")),
            self.tr("군사좌표(MGRS)"),
            self.tr("임무/기능(국/영문)"),
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
                    # 콤보박스 생성
                    self.unit_combo = QComboBox()
                    self.unit_combo.addItems([self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
                    self.unit_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.unit_combo.setStyleSheet("background-color: white; font: 바른공군체; font-size: 13pt;")
                    input_widget = self.unit_combo

                elif label == self.tr("임무/기능(국/영문)"):
                    input_widget = QTextEdit()
                    input_widget.setMinimumHeight(100)

                elif label == self.tr("군사좌표(MGRS)"):
                    input_widget = AutoSpacingLineEdit()
                    input_widget.setPlaceholderText("99A AA 99999 99999")
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
        self.setLayout(main_layout)

        # CVT 점수 평가 레이아웃 (오른쪽)
        score_group = QGroupBox(self.tr("CVT 점수 평가"))  # 점수 평가 그룹
        score_group.setStyleSheet("background-color: white; font: 강한공군체; font-size: 20px; font-weight: bold;")  # 스타일 설정
        score_layout = QVBoxLayout(score_group)  # 점수 평가 레이아웃 생성
        score_group_main = QGroupBox(self.tr("CVT 점수 평가"))  # 내부 그룹 생성
        score_group_main.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")
        score_layout_main = QVBoxLayout(score_group_main)  # 그룹 레이아웃 생성

        # 점수 섹션 설정
        self.sections = [
            (self.tr("중요도"), [  # 중요도 섹션
                (self.tr("작전계획 실행 중단 초래"), 10.0),
                (self.tr("작전계획 실행 위험 초래"), 8.0),
                (self.tr("작전계획 중요 변경 초래"), 6.0),
                (self.tr("차기 작전계획 단계 실행 지연"), 4.0),
                (self.tr("임무전환/자산 위치 조정하기"), 2.0),
                (self.tr("중요도 가점(중심)"), [  # 하위 항목
                    (self.tr("작계 1,2,3단계의 중심"), 0.5)]),
                (self.tr("중요도 가점(기능)"), [
                    (self.tr("비전투원 후송작전 통제소, 양륙공항, 양륙항만"), 0.5)])
            ]),
            (self.tr("취약성"), [  # 취약성 섹션
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
            (self.tr("위협"), [  # 위협 섹션
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

        self.checkboxes = {}  # 체크박스를 저장할 딕셔너리

        # 체크박스 추가 함수
        def add_checkboxes(layout, section, items):
            for item in items:
                if isinstance(item, tuple) and isinstance(item[1], (int, float)):  # 점수를 가진 항목
                    desc, score = item
                    checkbox = QCheckBox(f"{desc} ({score})")  # 체크박스 생성
                    checkbox.setStyleSheet(
                        "background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
                    checkbox.score = score
                    checkbox.section = section
                    checkbox.toggled.connect(
                        lambda checked, cb=checkbox: self.checkbox_clicked(checked, cb))  # 체크박스 클릭 시 응답
                    layout.addWidget(checkbox, alignment=Qt.AlignLeft)  # 체크박스 추가
                    self.checkboxes[f"{section}_{desc}"] = checkbox  # 체크박스 저장
                elif isinstance(item, tuple) and isinstance(item[1], list):  # 하위 항목
                    sub_group_box = QGroupBox(item[0])  # 서브 그룹박스 생성
                    sub_group_box.setStyleSheet("background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
                    sub_group_layout = QVBoxLayout()
                    add_checkboxes(sub_group_layout, f"{section}_{item[0]}", item[1])  # 재귀 호출
                    sub_group_box.setLayout(sub_group_layout)
                    layout.addWidget(sub_group_box)

        # 점수 평가 섹션에 대한 체크박스 추가
        for section, items in self.sections:
            group_box = QGroupBox(section)  # 그룹박스 생성
            group_box.setStyleSheet("background-color: white; font: 바른공군체; font-size: 16px; font-weight: bold;")
            group_layout = QVBoxLayout()
            add_checkboxes(group_layout, section, items)  # 체크박스 추가하는 함수 호출
            group_box.setLayout(group_layout)
            score_layout.addWidget(group_box)  # 점수 레이아웃에 그룹박스 추가

        score_group.setLayout(score_layout)  # 점수 그룹에 레이아웃 추가

        # 점수 레이아웃을 위한 스크롤 영역
        self.score_scroll = QScrollArea(self.parent)
        self.score_scroll.setWidgetResizable(True)
        score_container = QWidget()  # 점수 컨테이너 생성
        score_container.setLayout(score_layout)
        self.score_scroll.setWidget(score_container)
        score_layout_main.addWidget(self.score_scroll)  # 점수 레이아웃에 스크롤 추가

        horizontal_layout = QHBoxLayout()  # 수평 레이아웃
        horizontal_layout.addWidget(asset_info_group, 4)  # 자산 정보 그룹 추가
        horizontal_layout.addWidget(score_group_main, 6)  # 점수 평가 그룹 추가

        main_layout.addLayout(horizontal_layout)  # 수평 레이아웃을 메인 레이아웃에 추가

        # 총합 점수 레이블 초기화
        self.total_score_label = QLabel(self.tr("총합 점수: 0"))  # 총합 점수 레이블
        self.total_score_label.setStyleSheet("font: 강한공군체; font-size: 20px; font-weight: bold;")  # 스타일 설정
        main_layout.addWidget(self.total_score_label)  # 메인 레이아웃에 추가

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

        self.back_button = QPushButton(self.tr("메인 화면으로 돌아가기"), self)  # 메인 화면으로 돌아가기 버튼
        self.back_button.setStyleSheet("font: 강한공군체; font-size: 18px; min-width: 150px;")
        self.back_button.clicked.connect(self.parent.show_main_page)  # 클릭 시 메인 페이지로 돌아가기

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.print_button)  # 인쇄 버튼 추가
        button_layout.addWidget(self.back_button)


        for button in [self.save_button, self.back_button, self.print_button]:
            button.setFont(QFont("강한공군체", 15, QFont.Bold))
            button.setFixedSize(300, 50)  # 버튼 크기 고정 (너비 200, 높이 50)
            button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬


        main_layout.addLayout(button_layout)  # 메인 레이아웃에 버튼 레이아웃 추가
        self.setLayout(main_layout)  # 전체 레이아웃 설정

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

            # 자산 번호로 데이터베이스에서 자산 정보 확인
            target_asset = asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][0]
            self.parent.cursor.execute(f"SELECT id FROM cal_assets_{self.parent.selected_language} WHERE target_asset=?", (target_asset,))
            existing_asset = self.parent.cursor.fetchone()
            if existing_asset:  # 이미 존재하는 자산이면 수정
                # UPDATE 쿼리
                self.parent.cursor.execute(f'''
                    UPDATE cal_assets_ko SET
                        unit=?, asset_number=?, manager=?, contact=?, area=?, coordinate=?, mgrs=?, description=?,
                        criticality=?, criticality_bonus_center=?, criticality_bonus_function=?, 
                        vulnerability_damage_protection=?, vulnerability_damage_dispersion=?, 
                        vulnerability_recovery_time=?, vulnerability_recovery_ability=?, 
                        threat_attack=?, threat_detection=?
                    WHERE target_asset=?
                ''', (
                    unit_tuple[0], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][0], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                    target_asset  # 변경할 자산 번호
                ))
                # UPDATE 쿼리
                self.parent.cursor.execute(f'''
                    UPDATE cal_assets_en SET
                        unit=?, asset_number=?, manager=?, contact=?, area=?, coordinate=?, mgrs=?, description=?,
                        criticality=?, criticality_bonus_center=?, criticality_bonus_function=?, 
                        vulnerability_damage_protection=?, vulnerability_damage_dispersion=?, 
                        vulnerability_recovery_time=?, vulnerability_recovery_ability=?, 
                        threat_attack=?, threat_detection=?
                    WHERE target_asset=?
                ''', (
                    unit_tuple[1], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][1], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
                    scores_data.get(self.tr("중요도"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(중심)"), 0),
                    scores_data.get(self.tr("중요도_중요도 가점(기능)"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_방호강도"), 0),
                    scores_data.get(self.tr("취약성_피해민감도_분산배치"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구시간"), 0),
                    scores_data.get(self.tr("취약성_복구가능성_복구능력"), 0),
                    scores_data.get(self.tr("위협_공격가능성"), 0),
                    scores_data.get(self.tr("위협_탐지가능성"), 0),
                    target_asset  # 변경할 자산 번호
                ))


                QMessageBox.information(self, self.tr("성공"), self.tr("자산 정보가 수정되었습니다!"))  # 성공 메시지
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
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_id, unit_tuple[0], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][0], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][0], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][0], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
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
                        criticality, criticality_bonus_center, criticality_bonus_function, 
                        vulnerability_damage_protection, vulnerability_damage_dispersion, 
                        vulnerability_recovery_time, vulnerability_recovery_ability, 
                        threat_attack, threat_detection
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_id, unit_tuple[1], asset_data[self.tr("자산번호")], asset_data[(self.tr("담당자"), self.tr("(영문)"))][1], asset_data[self.tr("연락처")],
                    asset_data[(self.tr("방어대상자산"), self.tr("(영문)"))][1], asset_data[(self.tr("지역구분"), self.tr("(영문)"))][1], lat_lon, asset_data[self.tr("군사좌표(MGRS)")],
                    asset_data[self.tr("임무/기능(국/영문)")],
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
            self.parent.refresh_database()  # 데이터 저장 후 데이터베이스 갱신 호출
            self.parent.load_assets()  # 데이터 변경 후 저장된 자산 로드
            self.parent.show_view_assets_page()

        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"오류 발생: {e}"))  # 데이터베이스 오류 처리
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"예기치 않은 오류 발생: {str(e)}"))  # 일반 오류 처리

    def set_data(self, asset_id):
        self.asset_id = asset_id  # 선택한 자산의 ID
        self.parent.cursor.execute(f"SELECT * FROM cal_assets_ko WHERE id=?", (asset_id,))  # 자산 정보 조회
        asset_data1 = self.parent.cursor.fetchone()  # 결과 가져오기
        self.parent.cursor.execute(f"SELECT * FROM cal_assets_en WHERE id=?", (asset_id,))  # 자산 정보 조회
        asset_data2 = self.parent.cursor.fetchone()  # 결과 가져오기
        if asset_data1 and asset_data2:
            # Reset all checkboxes to unchecked
            self.reset_checkboxes()
            # UI 필드에 데이터 설정
            coord_str = asset_data1[7]
            lat, lon = coord_str.split(',')
            for label, field in self.asset_info_fields.items():
                if isinstance(field, tuple):
                    if label == (self.tr("담당자"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(asset_data1[3])
                        f2.setText(asset_data2[3])

                    elif label == (self.tr("방어대상자산"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(asset_data1[5])
                        f2.setText(asset_data2[5])

                    elif label == (self.tr("지역구분"), self.tr("(영문)")):
                        f1, f2 = field
                        f1.setText(asset_data1[6])
                        f2.setText(asset_data2[6])

                    elif label == (self.tr("위도"), self.tr("경도")):
                        f1, f2 = field
                        f1.setText(lat)
                        f2.setText(lon)
                else:
                    # 구성군(콤보박스 특성)
                    self.unit_combo.setCurrentText(asset_data1[1] if self.parent.selected_language == 'ko' else asset_data2[1])
                    self.asset_info_fields[self.tr("자산번호")].setText(str(asset_data1[2]))  # 자산번호
                    self.asset_info_fields[self.tr("연락처")].setText(asset_data1[4])  # 연락처
                    self.asset_info_fields[self.tr("군사좌표(MGRS)")].setText(asset_data1[8])  # 군사좌표(MGRS)
                    self.asset_info_fields[self.tr("임무/기능(국/영문)")].setPlainText(asset_data1[9])  # 임무 및 기능 기술
            # 체크박스 상태 설정
            self.set_checkbox_state(self.tr("중요도"), asset_data1[10] if asset_data1[10] is not None else 0)  # NULL 체크
            self.set_checkbox_state(self.tr("중요도_중요도 가점(중심)"), asset_data1[11] if asset_data1[11] is not None else 0)
            self.set_checkbox_state(self.tr("중요도_중요도 가점(기능)"), asset_data1[12] if asset_data1[12] is not None else 0)
            self.set_checkbox_state(self.tr("취약성_피해민감도_방호강도"), asset_data1[13] if asset_data1[13] is not None else 0)
            self.set_checkbox_state(self.tr("취약성_피해민감도_분산배치"), asset_data1[14] if asset_data1[14] is not None else 0)
            self.set_checkbox_state(self.tr("취약성_복구가능성_복구시간"), asset_data1[15] if asset_data1[15] is not None else 0)
            self.set_checkbox_state(self.tr("취약성_복구가능성_복구능력"), asset_data1[16] if asset_data1[16] is not None else 0)
            self.set_checkbox_state(self.tr("위협_공격가능성"), asset_data1[17] if asset_data1[17] is not None else 0)
            self.set_checkbox_state(self.tr("위협_탐지가능성"), asset_data1[18] if asset_data1[18] is not None else 0)

    def reset_data(self):
        """모든 입력 필드와 체크박스를 초기화합니다."""
        # 자산 ID 초기화
        self.asset_id = None

        # 구성군 콤보박스 초기화

        # 모든 입력 필드 초기화
        for label, field in self.asset_info_fields.items():
            if label == self.tr('구성군'):
                self.unit_combo.setCurrentIndex(0)
            elif isinstance(label, tuple):
                if label == (self.tr("지역구분"), self.tr("(영문)")):
                    f1, f2 = field
                    f1.setText("")
                    f2.setText("")
                elif label == (self.tr("방어자산명"), self.tr("(영문)")):
                    f1, f2 = field
                    f1.setText("")
                    f2.setText("")
                elif label == (self.tr("위도"), self.tr("경도")):
                    f1, f2 = field
                    f1.setText("")
                    f2.setText("")
            else:
                if isinstance(field, QTextEdit):
                    field.setPlainText("")
                else:
                    field.setText("")
        # 모든 체크박스 초기화
        self.reset_checkboxes()

    def reset_checkboxes(self):
        """모든 체크박스를 초기화(체크 해제)합니다."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)  # 모든 체크박스를 체크 해제

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

    def validate_latitude(self, lat):
        pattern = r'^[NS]\d{2}\.\d{5}'
        return bool(re.match(pattern, lat))

    def validate_longitude(self, lon):
        pattern = r'^[EW]\d{3}\.\d{5}'
        return bool(re.match(pattern, lon))

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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                asset_number TEXT,
                manager TEXT,
                contact TEXT,
                target_asset TEXT,
                area TEXT,
                coordinate TEXT,
                mgrs TEXT,   
                description TEXT,
                criticality FLOAT, 
                criticality_bonus_center FLOAT,
                criticality_bonus_function FLOAT,
                vulnerability_damage_protection FLOAT, 
                vulnerability_damage_dispersion FLOAT,
                vulnerability_recovery_time FLOAT, 
                vulnerability_recovery_ability FLOAT, 
                threat_attack FLOAT, 
                threat_detection FLOAT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cal_assets_en (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit TEXT,
                asset_number TEXT,
                manager TEXT,
                contact TEXT,
                target_asset TEXT,
                area TEXT,
                coordinate TEXT,
                mgrs TEXT,   
                description TEXT,
                criticality FLOAT, 
                criticality_bonus_center FLOAT,
                criticality_bonus_function FLOAT,
                vulnerability_damage_protection FLOAT, 
                vulnerability_damage_dispersion FLOAT,
                vulnerability_recovery_time FLOAT, 
                vulnerability_recovery_ability FLOAT, 
                threat_attack FLOAT, 
                threat_detection FLOAT
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
