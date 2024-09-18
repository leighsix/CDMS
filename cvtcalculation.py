import sys
import sqlite3
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject
from PyQt5.QtGui import QIcon
from languageselection import Translator
from mapview import PriorityMapView
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QLabel, QTableWidget, QHeaderView, \
    QTableWidgetItem, QPushButton, QMessageBox, QCheckBox, QAbstractItemView
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QTimer
import pandas as pd
import traceback


class MainWindow(QtWidgets.QMainWindow, QObject):
    """메인 창 클래스"""
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CAL/DAL Management System")
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(800, 600)
        self.conn = sqlite3.connect('assets_management.db')
        self.selected_language = "ko"  # 기본 언어 설정
        self.cursor = self.conn.cursor()

        self.initDB()
        self.central_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(self.central_widget)

        self.cvt_calculation_window = CVTCalculationWindow(self)
        self.central_widget.addWidget(self.cvt_calculation_window)

        # 초기 자산 불러오기
        self.cvt_calculation_window.load_all_assets()

    def show_main_page(self):
        """메인 페이지를 표시하는 메서드"""
        self.central_widget.setCurrentIndex(0)

    def initDB(self):
        """데이터베이스 테이블 초기화 메서드"""
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
        self.conn.commit()
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


class CVTCalculationWindow(QDialog):
    """CVT 계산을 위한 다이얼로그 창"""
    def __init__(self, parent):
        super(CVTCalculationWindow, self).__init__(parent)
        self.parent = parent
        self.setMinimumSize(800, 600)
        self.initUI()
        self.assets_data_ko = pd.DataFrame()
        self.assets_data_en = pd.DataFrame()
        self.deleted_ids = []

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
        self.find_button.clicked.connect(self.recalculate_cvt)
        filter_layout.addWidget(self.find_button)

        # 여백 추가
        filter_layout.addStretch()

        # 필터 그룹에 레이아웃 설정
        filter_group.setLayout(filter_layout)

        # 메인 레이아웃에 필터 그룹 추가
        layout.addWidget(filter_group)

        # 가중치 입력 레이아웃
        self.weight_layout = QHBoxLayout()
        self.weight_layout.setAlignment(Qt.AlignLeft)
        self.weight_checkbox = QCheckBox(self.tr("가중치 적용"))
        self.weight_checkbox.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.weight_checkbox.toggled.connect(self.toggle_weight_inputs)
        self.weight_layout.addWidget(self.weight_checkbox)


        self.criticality_weight_input = QLineEdit()
        self.criticality_weight_input.setFixedSize(120, 30)
        self.criticality_weight_input.setStyleSheet("font: 바른공군체; font-size: 16px;")

        self.criticality_weight_input.setPlaceholderText(self.tr("중요도 가중치"))
        self.vulnerability_weight_input = QLineEdit()
        self.vulnerability_weight_input.setFixedSize(150, 30)
        self.vulnerability_weight_input.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.vulnerability_weight_input.setPlaceholderText(self.tr("취약성 가중치"))
        self.threat_weight_input = QLineEdit()
        self.threat_weight_input.setFixedSize(150, 30)
        self.threat_weight_input.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.threat_weight_input.setPlaceholderText(self.tr("위협 가중치"))

        self.weight_layout.addWidget(self.criticality_weight_input)
        self.weight_layout.addWidget(self.vulnerability_weight_input)
        self.weight_layout.addWidget(self.threat_weight_input)

        self.bonus_checkbox = QCheckBox(self.tr("가점 적용"))
        self.bonus_checkbox.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.bonus_checkbox.toggled.connect(self.toggle_bonus_column)
        self.weight_layout.addWidget(self.bonus_checkbox)

        self.calculate_button = QPushButton(self.tr("CVT 산출"), self)
        self.calculate_button.setFixedSize(120, 30)
        self.calculate_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold;")
        self.calculate_button.clicked.connect(self.recalculate_cvt)
        self.weight_layout.addWidget(self.calculate_button)

        self.weight_layout.addStretch(1)

        # 결과 테이블 초기화
        self.results_table = MyTableWidget(self)
        headers = ["", self.tr("우선순위"), self.tr("구성군"), self.tr("방어대상자산"), self.tr("지역구분"), self.tr("경위도"),
                   self.tr("군사좌표(MGRS)"), self.tr("중요도"), self.tr("취약성"), self.tr("위협 점수"), self.tr("가점"),
                   self.tr("합계"), self.tr("삭제"), self.tr("ID")]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setColumnHidden(10, True)  # 가점 열을 기본적으로 숨김
        self.results_table.setColumnHidden(13, True)  # 가점 열을 기본적으로 숨김


        # 행 번호 숨기기
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet(
            "QTableWidget {background-color: #ffffff; font: 바른공군체; font-size: 16px;}"
            "QTableWidget::item { padding: 8px; }")
        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.results_table.horizontalHeader().setFont(font)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 60)  # 체크박스 열의 너비를 60으로 설정
        header.resizeSection(1, 100)  # 우선순위 열의 너비를 100으로 설정
        header.resizeSection(12, 100)

        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.results_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블이 수평으로 확장되도록 설정
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()-2):
            self.results_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        # 헤더 높이 자동 조절
        self.results_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.results_table.verticalHeader().setDefaultSectionSize(60)

        self.print_button = QPushButton(self.tr("출력"), self)
        self.print_button.clicked.connect(self.print_data)

        self.map_view_button = QPushButton(self.tr("지도 보기"), self)
        self.map_view_button.clicked.connect(self.show_map_view)

        self.decision_priority_button = QPushButton(self.tr("우선순위 결정"), self)
        self.decision_priority_button.clicked.connect(self.decision_priority)

        self.initialize_priority_button = QPushButton(self.tr("우선순위 초기화"), self)
        self.initialize_priority_button.clicked.connect(self.initialize_priority)

        self.return_button = QPushButton(self.tr("메인화면으로 돌아가기"), self)
        self.return_button.clicked.connect(self.parent.show_main_page)


        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 5, 0, 5)

        # 각 버튼에 폰트 적용
        for button in [self.print_button, self.map_view_button, self.decision_priority_button, self.initialize_priority_button, self.return_button]:
            button.setFont(QFont("강한공군체", 14, QFont.Bold))
            button.setFixedSize(230, 50)  # 버튼 크기 고정 (너비 200, 높이 50)
            button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬

        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.map_view_button)
        button_layout.addWidget(self.decision_priority_button)
        button_layout.addWidget(self.initialize_priority_button)
        button_layout.addWidget(self.return_button)

        # 레이아웃에 추가
        layout.addLayout(self.weight_layout)
        layout.addWidget(self.results_table)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.asset_search_input.clear()  # 검색 입력창 비우기
        self.weight_checkbox.setChecked(False)  # 가중치 적용 체크박스 해제
        self.toggle_weight_inputs()  # 가중치 입력 필드 비활성화
        self.bonus_checkbox.setChecked(False)  # 가점 적용 체크박스 해제
        self.toggle_bonus_column(False)  # 가점 열 숨기기
        self.load_all_assets()  # 테이블 데이터 새로고침
        self.update_results_table(self.assets_data_ko if self.parent.selected_language == 'ko' else self.assets_data_en)  # 테이블 업데이트
        self.results_table.uncheckAllRows()

    def toggle_weight_inputs(self):
        """가중치 입력 필드 활성화/비활성화 기능"""
        is_checked = self.weight_checkbox.isChecked()
        self.criticality_weight_input.setEnabled(is_checked)
        self.vulnerability_weight_input.setEnabled(is_checked)
        self.threat_weight_input.setEnabled(is_checked)

        if not is_checked:
            self.criticality_weight_input.clear()
            self.vulnerability_weight_input.clear()
            self.threat_weight_input.clear()

    def toggle_bonus_column(self, checked):
        self.results_table.setColumnHidden(10, not checked)  # 가점 열 표시/숨김

        self.results_table.blockSignals(True)  # 신호 일시 차단

        for row in range(self.results_table.rowCount()):
            asset_id = self.results_table.item(row, 13).text()
            if checked:
                bonus_value = self.assets_data_ko.loc[self.assets_data_ko['id'] == int(asset_id), 'bonus'].values[0]
                item = QTableWidgetItem(f"{bonus_value:.2f}")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.results_table.setItem(row, 10, item)
            else:
                self.assets_data_ko.loc[self.assets_data_ko['id'] == int(asset_id), 'bonus'] = 0.0
                self.assets_data_en.loc[self.assets_data_en['id'] == int(asset_id), 'bonus'] = 0.0
                if self.results_table.item(row, 10):
                    self.results_table.item(row, 10).setText("0.00")

        self.results_table.blockSignals(False)  # 신호 재개

        # 열 표시 상태가 변경된 후 update_bonus 연결
        if checked:
            self.results_table.cellChanged.connect(self.update_bonus)

    def update_bonus(self, row, column):
        try:
            if column == 10:  # 가점 열
                bonus_item = self.results_table.item(row, column)
                if bonus_item is None:
                    return
                bonus_value = bonus_item.text()
                try:
                    bonus_value = float(bonus_value)
                    asset_id_item = self.results_table.item(row, 13)
                    if asset_id_item is None:
                        QMessageBox.warning(self, "경고", "자산 ID를 찾을 수 없습니다.")
                        return
                    asset_id = asset_id_item.text()

                    # 데이터프레임 업데이트
                    self.assets_data_ko.loc[self.assets_data_ko['id'] == int(asset_id), 'bonus'] = bonus_value
                    self.assets_data_en.loc[self.assets_data_en['id'] == int(asset_id), 'bonus'] = bonus_value

                    # 테이블 업데이트
                    formatted_bonus = f"{bonus_value:.2f}"
                    self.results_table.blockSignals(True)  # 신호 차단
                    self.results_table.item(row, column).setText(formatted_bonus)
                    self.results_table.blockSignals(False)  # 신호 재개

                except ValueError:
                    QMessageBox.warning(self, "경고", "올바른 숫자를 입력해주세요.")
                    self.results_table.blockSignals(True)
                    self.results_table.item(row, column).setText("0.00")
                    self.results_table.blockSignals(False)

                    # 에러 시 데이터프레임 업데이트
                    asset_id_item = self.results_table.item(row, 13)
                    if asset_id_item:
                        asset_id = asset_id_item.text()
                        self.assets_data_ko.loc[self.assets_data_ko['id'] == int(asset_id), 'bonus'] = 0.0
                        self.assets_data_en.loc[self.assets_data_en['id'] == int(asset_id), 'bonus'] = 0.0
                    else:
                        QMessageBox.warning(self, "경고", "자산 ID를 찾을 수 없어 업데이트할 수 없습니다.")
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "오류", error_msg)
            print(error_msg)  # 콘솔에도 오류 출력

    def load_all_assets(self):
        """자산 정보를 데이터베이스에서 선택된 언어에 해당하는 데이터만 로드하여 표시하는 함수"""
        query = f'''
            SELECT id, unit, target_asset, area, coordinate, mgrs,
                   criticality + criticality_bonus_center + criticality_bonus_function AS total_criticality,
                   vulnerability_damage_protection +
                   vulnerability_damage_dispersion +
                   vulnerability_recovery_time +
                   vulnerability_recovery_ability AS total_vulnerability,
                   threat_attack + threat_detection AS total_threat
            FROM cal_assets_ko
        '''

        self.parent.cursor.execute(query,)
        assets_data_ko = self.parent.cursor.fetchall()

        # DataFrame으로 변환하여 삭제된 자산 제외
        self.assets_data_ko = pd.DataFrame(assets_data_ko, columns=['id', 'unit', 'target_asset', 'area', 'coordinate', 'mgrs', 'total_criticality',
                                                             'total_vulnerability', 'total_threat'
                                                             ])

        # 'bonus' 열 추가 및 초기화
        self.assets_data_ko['bonus'] = 0.0


        query = f'''
            SELECT id, unit, target_asset, area, coordinate, mgrs,
                   criticality + criticality_bonus_center + criticality_bonus_function AS total_criticality,
                   vulnerability_damage_protection +
                   vulnerability_damage_dispersion +
                   vulnerability_recovery_time +
                   vulnerability_recovery_ability AS total_vulnerability,
                   threat_attack + threat_detection AS total_threat
            FROM cal_assets_en
        '''
        self.parent.cursor.execute(query,)
        assets_data_en = self.parent.cursor.fetchall()

        # DataFrame으로 변환하여 삭제된 자산 제외
        self.assets_data_en = pd.DataFrame(assets_data_en, columns=['id', 'unit', 'target_asset', 'area', 'coordinate', 'mgrs', 'total_criticality',
                                                             'total_vulnerability', 'total_threat'
                                                             ])
        # 'bonus' 열 추가 및 초기화
        self.assets_data_en['bonus'] = 0.0

        # 테이블에 데이터 표시
        if self.parent.selected_language == 'ko':
            self.calculate_cvt(self.assets_data_ko)
        else:
            self.calculate_cvt(self.assets_data_en)

    def update_results_table(self, data):
        """테이블에 데이터 표시"""
        self.results_table.setRowCount(0)
        for index, row in data.iterrows():
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)

            # 체크박스 위젯 생성 및 설정
            checkbox_widget = CenteredCheckBox()
            self.results_table.setCellWidget(row_position, 0, checkbox_widget)

            def create_centered_item(text):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)  # 가운데 정렬
                return item
            self.results_table.setItem(row_position, 13, create_centered_item(row['id']))
            self.results_table.setItem(row_position, 1, create_centered_item(row['rank']))
            self.results_table.setItem(row_position, 2, create_centered_item(row['unit']))
            self.results_table.setItem(row_position, 3, create_centered_item(row['target_asset']))
            self.results_table.setItem(row_position, 4, create_centered_item(row['area']))
            self.results_table.setItem(row_position, 5, create_centered_item(row['coordinate']))
            self.results_table.setItem(row_position, 6, create_centered_item(row['mgrs']))
            self.results_table.setItem(row_position, 7, create_centered_item(f"{row['criticality']:.2f}"))
            self.results_table.setItem(row_position, 8, create_centered_item(f"{row['vulnerability']:.2f}"))
            self.results_table.setItem(row_position, 9, create_centered_item(f"{row['threat']:.2f}"))
            self.results_table.setItem(row_position, 10, create_centered_item(f"{row['bonus']:.2f}"))
            self.results_table.setItem(row_position, 11, create_centered_item(f"{row['total_score']:.2f}"))
            # 삭제 버튼 위치 변경
            delete_button = QPushButton(self.tr("삭제"))
            delete_button.setFont(QFont("바른공군체", 13))
            delete_button.setMaximumWidth(100)
            delete_button.clicked.connect(lambda checked, id=row['id']: self.delete_row(id))
            self.results_table.setCellWidget(row_position, 12, delete_button)

    def delete_row(self, asset_id):
        """자산을 삭제하는 함수 (DataFrame에서만)"""
        self.deleted_ids.append(asset_id)
        self.assets_data_ko = self.assets_data_ko[self.assets_data_ko['id'] != asset_id]
        self.assets_data_en = self.assets_data_en[self.assets_data_en['id'] != asset_id]

        # 테이블 갱신
        self.recalculate_cvt()

    def calculate_cvt(self, data):
        """CVT 계산 메서드"""
        try:
            if data.empty:
                QMessageBox.warning(self, self.tr("경고"), self.tr("자산 데이터가 없습니다."))
                return

            # 가중치 초기화 가져오기
            criticality_weight = float(self.criticality_weight_input.text() or 1.0)
            vulnerability_weight = float(self.vulnerability_weight_input.text() or 1.0)
            threat_weight = float(self.threat_weight_input.text() or 1.0)

            # 가중치 적용
            data['criticality'] = data['total_criticality'].astype(float) * criticality_weight
            data['vulnerability'] = data['total_vulnerability'].astype(float) * vulnerability_weight
            data['threat'] = data['total_threat'].astype(float) * threat_weight

            # 합산
            data['total_score'] = data['criticality'] + data['vulnerability'] + data['threat'] + data['bonus']
            data.sort_values('total_score', ascending=False, inplace=True)

            # 순위 매기기
            data['rank'] = data['total_score'].rank(method='min', ascending=False).astype(int)

            # 테이블 업데이트
            self.update_results_table(data)

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), str(e))

    def recalculate_cvt(self):
        """CVT 계산 메서드"""
        try:
            if self.assets_data_ko.empty and self.assets_data_en.empty:
                QMessageBox.warning(self, self.tr("경고"), self.tr("자산 데이터가 없습니다."))
                return
            unit_filter = self.unit_filter.currentText()
            search_text = self.asset_search_input.text()

            # 데이터프레임 필터링
            if self.parent.selected_language == 'ko':
                filtered_data = self.assets_data_ko.copy()
            else:
                filtered_data = self.assets_data_en.copy()

            self.results_table.uncheckAllRows()
            if unit_filter != self.tr("전체"):
                filtered_data = filtered_data[filtered_data['unit'] == unit_filter]

            if search_text:
                filtered_data = filtered_data[
                    filtered_data['target_asset'].str.contains(search_text, case=False, na=False) |
                    filtered_data['area'].str.contains(search_text, case=False, na=False) |
                    filtered_data['coordinate'].str.contains(search_text, case=False, na=False) |
                    filtered_data['mgrs'].str.contains(search_text, case=False, na=False)
                    ]

            # 가중치 가져오기
            criticality_weight = float(self.criticality_weight_input.text() or 1.0)
            vulnerability_weight = float(self.vulnerability_weight_input.text() or 1.0)
            threat_weight = float(self.threat_weight_input.text() or 1.0)

            # 가중치 적용
            filtered_data['criticality'] = filtered_data['total_criticality'].astype(float) * criticality_weight
            filtered_data['vulnerability'] = filtered_data['total_vulnerability'].astype(float) * vulnerability_weight
            filtered_data['threat'] = filtered_data['total_threat'].astype(float) * threat_weight

            # 합산
            filtered_data['total_score'] = filtered_data['criticality'] + filtered_data['vulnerability'] + filtered_data[
                'threat'] + filtered_data['bonus']
            filtered_data.sort_values('total_score', ascending=False, inplace=True)

            # 순위 매기기
            filtered_data['rank'] = filtered_data['total_score'].rank(method='min', ascending=False).astype(int)

            # 테이블 업데이트
            self.update_results_table(filtered_data)

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), str(e))

    def initialize_priority(self):
        try:
            # 기존 데이터 삭제
            if hasattr(self, 'parent') and hasattr(self.parent, 'cursor') and hasattr(self.parent, 'conn'):
                self.parent.cursor.execute('DELETE FROM cal_assets_priority_ko')
                self.parent.cursor.execute('DELETE FROM cal_assets_priority_en')
                self.parent.conn.commit()
            else:
                raise AttributeError("데이터베이스 연결이 설정되지 않았습니다.")

            # 가중치 초기화
            if hasattr(self, 'weight_checkbox') and hasattr(self, 'toggle_weight_inputs'):
                self.weight_checkbox.setChecked(False)
                self.toggle_weight_inputs()

            # 가점 초기화
            if hasattr(self, 'bonus_checkbox') and hasattr(self, 'toggle_bonus_column'):
                self.bonus_checkbox.setChecked(False)
                self.toggle_bonus_column(False)

            # 구성군 필터 초기화 ('전체'로 설정)
            if hasattr(self, 'unit_filter'):
                self.unit_filter.setCurrentText("전체")

            # 검색 필터 초기화 (빈 문자열로 설정)
            if hasattr(self, 'asset_search_input'):
                self.asset_search_input.setText("")

            # 데이터베이스에서 원래 데이터 다시 불러오기
            if hasattr(self, 'load_all_assets'):
                self.load_all_assets()
            else:
                raise AttributeError("load_all_assets 메서드가 정의되지 않았습니다.")

            # CVT 재계산
            if hasattr(self, 'recalculate_cvt'):
                self.recalculate_cvt()
            else:
                raise AttributeError("recalculate_cvt 메서드가 정의되지 않았습니다.")

            QMessageBox.information(self, self.tr("성공"), self.tr("우선순위 정보가 성공적으로 초기화되었습니다."))

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), f"{self.tr('우선순위 정보 초기화 중 오류가 발생했습니다:')} {str(e)}")
            if hasattr(self, 'parent') and hasattr(self.parent, 'conn'):
                self.parent.conn.rollback()

        finally:
            # 테이블 새로고침
            if hasattr(self, 'parent') and hasattr(self.parent, 'selected_language'):
                if hasattr(self, 'update_results_table'):
                    if self.parent.selected_language == 'ko':
                        if hasattr(self, 'assets_data_ko'):
                            self.update_results_table(self.assets_data_ko)
                        else:
                            print("assets_data_ko가 정의되지 않았습니다.")
                    else:
                        if hasattr(self, 'assets_data_en'):
                            self.update_results_table(self.assets_data_en)
                        else:
                            print("assets_data_en이 정의되지 않았습니다.")
                else:
                    print("update_results_table 메서드가 정의되지 않았습니다.")
            else:
                print("parent 또는 selected_language가 정의되지 않았습니다.")

    def show_map_view(self):
        """체크된 자산을 지도에 표시하는 함수"""
        selected_assets = []
        for row in range(self.results_table.rowCount()):
            check_box = self.results_table.cellWidget(row, 0)
            if isinstance(check_box, CenteredCheckBox) and check_box.isChecked():
                unit = self.results_table.item(row,2).text() # 구성군 열
                asset_name = self.results_table.item(row, 3).text()  # 방어대상자산 열
                coordinate = self.results_table.item(row, 5).text()  # 방어대상자산 열
                mgrs_coord = self.results_table.item(row, 6).text()  # 군사좌표 열
                priority = int(self.results_table.item(row, 1).text())  # 우선순위 열
                selected_assets.append((unit, asset_name, coordinate, mgrs_coord, priority))

        if not selected_assets:
            QMessageBox.warning(self, self.tr("경고"), self.tr("선택된 자산이 없습니다."))
            return

        map_view = PriorityMapView(selected_assets)
        map_view.exec_()

    def decision_priority(self):
        try:
            # assets_priority 테이블 생성 (이미 존재하지 않는 경우)
            self.parent.cursor.execute('''
                CREATE TABLE IF NOT EXISTS cal_assets_priority_ko (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    priority INTEGER,
                    unit TEXT,
                    target_asset TEXT,
                    area TEXT,
                    coordinate TEXT,
                    mgrs TEXT,
                    criticality REAL,
                    vulnerability REAL,
                    threat REAL,
                    bonus REAL,
                    total_score REAL
                )
            ''')
            self.parent.conn.commit()
            # assets_priority 테이블 생성 (이미 존재하지 않는 경우)
            self.parent.cursor.execute('''
                CREATE TABLE IF NOT EXISTS cal_assets_priority_en (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    priority INTEGER,
                    unit TEXT,
                    target_asset TEXT,
                    area TEXT,
                    coordinate TEXT,
                    mgrs TEXT,
                    criticality REAL,
                    vulnerability REAL,
                    threat REAL,
                    bonus REAL,
                    total_score REAL
                )
            ''')
            self.parent.conn.commit()
            # 기존 데이터 삭제
            self.parent.cursor.execute('DELETE FROM cal_assets_priority_ko')
            self.parent.cursor.execute('DELETE FROM cal_assets_priority_en')

            # 테이블에 표시된 모든 행의 데이터를 가져옵니다
            for row in range(self.results_table.rowCount()):
                priority = int(self.results_table.item(row, 1).text()) if self.results_table.item(row, 1) else 0
                unit = self.results_table.item(row, 2).text() if self.results_table.item(row, 2) else ''
                target_asset = self.results_table.item(row, 3).text() if self.results_table.item(row, 3) else ''
                area = self.results_table.item(row, 4).text() if self.results_table.item(row, 4) else ''
                coordinate = self.results_table.item(row, 5).text() if self.results_table.item(row, 5) else ''
                mgrs = self.results_table.item(row, 6).text() if self.results_table.item(row, 6) else ''
                criticality = float(self.results_table.item(row, 7).text()) if self.results_table.item(row, 7) else 0.0
                vulnerability = float(self.results_table.item(row, 8).text()) if self.results_table.item(row,
                                                                                                         8) else 0.0
                threat = float(self.results_table.item(row, 9).text()) if self.results_table.item(row, 9) else 0.0
                bonus = float(self.results_table.item(row, 10).text()) if self.results_table.item(row, 10) else 0.0
                total_score = float(self.results_table.item(row, 11).text()) if self.results_table.item(row, 11) else 0.0
                asset_id = int(self.results_table.item(row, 13).text()) if self.results_table.item(row, 13) else 0

                unit_en = self.assets_data_en.loc[self.assets_data_en['id'] == asset_id, 'unit'].values[0] if not \
                self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None
                unit_ko = self.assets_data_ko.loc[self.assets_data_en['id'] == asset_id, 'unit'].values[0] if not \
                self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None
                target_asset_en = self.assets_data_en.loc[self.assets_data_en['id'] == asset_id, 'target_asset'].values[0] if not \
                    self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None
                target_asset_ko = self.assets_data_ko.loc[self.assets_data_en['id'] == asset_id, 'target_asset'].values[0] if not \
                    self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None
                area_en = self.assets_data_en.loc[self.assets_data_en['id'] == asset_id, 'area'].values[0] if not \
                    self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None
                area_ko = self.assets_data_ko.loc[self.assets_data_en['id'] == asset_id, 'area'].values[0] if not \
                    self.assets_data_en[self.assets_data_en['id'] == asset_id].empty else None


                # 데이터를 assets_priority 테이블에 삽입
                self.parent.cursor.execute('''
                    INSERT INTO cal_assets_priority_ko 
                    (priority, unit, target_asset, area, coordinate, mgrs, criticality, vulnerability, threat, bonus, total_score, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (priority, unit_ko, target_asset_ko, area_ko, coordinate, mgrs, criticality, vulnerability, threat, bonus, total_score, asset_id))
                # 데이터를 assets_priority 테이블에 삽입

                self.parent.cursor.execute('''
                    INSERT INTO cal_assets_priority_en 
                    (priority, unit, target_asset, area, coordinate, mgrs, criticality, vulnerability, threat, bonus, total_score, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (priority, unit_en, target_asset_en, area_en, coordinate, mgrs, criticality, vulnerability, threat, bonus, total_score, asset_id))

            # 변경사항을 커밋
            self.parent.conn.commit()

            # GUI 스레드에서 메시지 박스를 표시하기 위해 QTimer 사용
            QTimer.singleShot(100,
                              lambda: QMessageBox.information(self, self.tr("성공"), self.tr("우선순위 정보가 성공적으로 저장되었습니다.")))

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), f"{self.tr('우선순위 정보 저장 중 오류가 발생했습니다:')} {str(e)}")
            self.parent.conn.rollback()

    def print_data(self):
        try:
            document = QTextDocument()
            cursor = QTextCursor(document)

            # 전체 문서 스타일 설정
            document.setDefaultStyleSheet("""
                body { font-family: 'Arial', sans-serif; }
                h1 { color: black; }
                .info { padding: 10px; }
                table { border-collapse: collapse; width: 100%; }
                td, th { border: 1px solid black; padding: 8px; text-align: center; }
            """)

            # 제목 추가
            cursor.insertHtml("<h1 align='center'>" + self.tr("중요자산 우선순위") + "</h1>")
            cursor.insertBlock()

            # 정보 섹션
            cursor.insertHtml("<div class='info' style='text-align: left; font-size: 0.9em;'>")
            cursor.insertHtml(f"<p><strong>{self.tr('구성군')}:</strong> {self.unit_filter.currentText()}</p>")
            cursor.insertHtml("<br><br>")
            if self.weight_checkbox.isChecked():
                cursor.insertHtml(f"<p><strong>{self.tr('가중치 적용')}:</strong> {self.tr('YES')}</p>")
                cursor.insertHtml(f"<p><strong>{self.tr('중요도 가중치')}:</strong> {self.criticality_weight_input.text()}</p>")
                cursor.insertHtml(f"<p><strong>{self.tr('취약성 가중치')}:</strong> {self.vulnerability_weight_input.text()}</p>")
                cursor.insertHtml(f"<p><strong>{self.tr('위협 가중치')}:</strong> {self.threat_weight_input.text()}</p>")
            else:
                cursor.insertHtml(f"<p><strong>{self.tr('가중치 적용')}:</strong> {self.tr('NO')}</p>")
            cursor.insertHtml("</div>")
            cursor.insertBlock()

            # 테이블 형식 설정
            table_format = QTextTableFormat()
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            table_format.setCellPadding(5)
            table_format.setAlignment(Qt.AlignCenter)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))

            # 테이블 생성
            rows = self.results_table.rowCount() + 1
            cols = self.results_table.columnCount() - 2
            table = cursor.insertTable(rows, cols, table_format)

            # 헤더 추가
            headers = [self.tr("우선순위"), self.tr("구성군"), self.tr("방어대상자산"), self.tr("지역구분"), self.tr("경위도"),
                       self.tr("MGRS"), self.tr("중요도"),
                       self.tr("취약성"), self.tr("위협 점수"), self.tr("가점"), self.tr("합계")]
            for col, header in enumerate(headers):
                cell = table.cellAt(0, col)
                cellCursor = cell.firstCursorPosition()
                cellCursor.insertHtml(f"<th>{header}</th>")

            # 데이터 추가
            for row in range(self.results_table.rowCount()):
                for col in range(cols+1):
                    item = self.results_table.item(row, col)
                    if item:
                        cell = table.cellAt(row + 1, col - 1)
                        cellCursor = cell.firstCursorPosition()
                        cellCursor.insertText(item.text())

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
                document.print_(printer)
                QMessageBox.information(self, self.tr("저장 완료"), f"{self.tr('자산 보고서가')} {file_path} {self.tr('파일로 저장되었습니다.')}")

            QCoreApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), f"{self.tr('보고서 생성 중 오류가 발생했습니다:')} {str(e)}")

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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Translator 인스턴스 생성
    translator = Translator(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
