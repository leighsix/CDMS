from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator
from addasset import AddAssetWindow
import sys, logging
import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from PyQt5.QtGui import QPagedPaintDevice, QPainter, QImage, QPageSize, QPageLayout
from PyQt5.QtCore import QUrl, QTemporaryFile, QSize, QTimer, QMarginsF
from generate_dummy_data import engagement_effectiveness
from languageselection import Translator, LanguageSelectionWindow
from commander_guidance import BmdPriority, EngagementEffect
from common_map_view import CommonCalMapView
from cal_map_view import CalMapView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, QRect, QDateTime
from setting import SettingWindow, MapApp
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
import io
import re  # 입력 검증에 사용
import hashlib  # 해시함수 사용
import hmac  # 메시지 인증코드 (MAC) 사용

class CalViewWindow(QtWidgets.QDialog, QObject):
    """저장된 자산을 보여주는 창"""

    def __init__(self, parent):
        super(CalViewWindow, self).__init__(parent)
        self.parent = parent
        self.setMinimumSize(1024, 768)
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        self.initUI()
        self.load_assets()
        self.update_map()

    def initUI(self):
        """UI 구성"""
        main_layout = QHBoxLayout()

        # 좌우측 너비 조정 가능하도록 설정
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 왼쪽 레이아웃 구성
        left_layout.setSpacing(20)
        left_layout.setContentsMargins(30, 40, 30, 30)

        # 필터 그룹박스 생성
        filter_group = QGroupBox(self.tr("필터"))
        filter_group.setStyleSheet("font: 바른공군체; font-size: 18px; font-weight: bold;")

        # 필터 레이아웃 생성
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)
        filter_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 왼쪽 상단 정렬

        # 구성군 선택 필터
        unit_filter_label = QLabel(self.tr("구성군 선택"), self)
        unit_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군"), self.tr("기타")])
        self.unit_filter.setFixedSize(150, 30)
        self.unit_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.unit_filter.currentIndexChanged.connect(self.load_assets)  # 변경 시 load_assets 호출
        filter_layout.addWidget(unit_filter_label, 0, 0)
        filter_layout.addWidget(self.unit_filter, 0, 1)

        # DAL 선택 필터
        self.dal_checkbox = QCheckBox(self.tr("방어자산(DAL)"))
        self.dal_checkbox.setStyleSheet("font: 강한공군체; font-size: 16px; font-weight:bold;")
        filter_layout.addWidget(self.dal_checkbox, 0, 2, 1, 2)

        # BMD 우선순위 필터
        bmd_priority_filter_label = QLabel(self.tr("BMD 우선순위 목록"), self)
        bmd_priority_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.bmd_priority_filter = QComboBox()
        self.bmd_priority_filter.addItems(
            [self.tr("전체"), self.tr("지휘통제시설"), self.tr("비행단"), self.tr("군수기지"), self.tr("해군기지"), self.tr("주요레이다")])
        self.bmd_priority_filter.setFixedSize(150, 30)
        self.bmd_priority_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.bmd_priority_filter.currentIndexChanged.connect(self.load_assets)  # 변경 시 load_assets 호출
        filter_layout.addWidget(bmd_priority_filter_label, 1, 0)
        filter_layout.addWidget(self.bmd_priority_filter, 1, 1)

        # 교전효과 수준
        engagement_filter_label = QLabel(self.tr("교전효과 수준"), self)
        engagement_filter_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.engagement_filter = QComboBox()
        self.engagement_filter.addItems(
            [self.tr("전체"), self.tr("1단계: 원격발사대"), self.tr("2단계: 단층방어"), self.tr("3단계: 중첩방어"), self.tr("4단계: 다층방어")])
        self.engagement_filter.setFixedSize(250, 30)
        self.engagement_filter.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.engagement_filter.currentIndexChanged.connect(self.load_assets)  # 변경 시 load_assets 호출
        filter_layout.addWidget(engagement_filter_label, 1, 2)
        filter_layout.addWidget(self.engagement_filter, 1, 3)

        # 검색 섹션
        search_label = QLabel(self.tr("검색"), self)
        search_label.setStyleSheet("font: 바른공군체; font-size: 16px;")
        self.asset_search_input = QLineEdit()
        self.asset_search_input.setPlaceholderText(self.tr("검색어를 입력하세요"))
        self.asset_search_input.setFixedSize(200, 30)
        self.asset_search_input.setStyleSheet("font: 바른공군체; font-size: 16px;")
        filter_layout.addWidget(search_label, 2, 0)
        filter_layout.addWidget(self.asset_search_input, 2, 1, 1, 2)

        # 찾기 버튼
        self.find_button = QPushButton(self.tr("찾기"))
        self.find_button.setFixedSize(80, 30)
        self.find_button.setStyleSheet("font: 바른공군체; font-size: 16px; font-weight: bold;")
        self.find_button.clicked.connect(self.load_assets)
        filter_layout.addWidget(self.find_button, 2, 3)

        # 필터 그룹에 레이아웃 설정
        filter_group.setLayout(filter_layout)

        # 필터 그룹의 크기를 고정
        filter_group.setFixedHeight(filter_group.sizeHint().height())

        # DAL 체크박스를 위한 별도 그룹
        dal_group = QGroupBox()
        dal_layout = QHBoxLayout()
        dal_layout.addWidget(self.dal_checkbox)
        dal_group.setLayout(dal_layout)

        self.assets_table = MyTableWidget()
        self.assets_table.setColumnCount(22)
        self.assets_table.setHorizontalHeaderLabels([
            "", self.tr("ID"), self.tr("구성군"), self.tr("자산번호"), self.tr("담당자"),
            self.tr("연락처"), self.tr("방어대상자산"), self.tr("지역구분"), self.tr("경위도"),
            self.tr("군사좌표(MGRS)"), self.tr("임무/기능 기술"), self.tr("방어자산"), self.tr("무기체계"), self.tr("보유탄수"),
            self.tr("위협방위"), self.tr("교전효과 수준"), self.tr("BMD 우선순위"),
            self.tr("중요도"), self.tr("취약성"), self.tr("위협"), self.tr("합산 점수"), self.tr("삭제")
        ])
        # self.assets_table.verticalHeader().setVisible(False)

        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.setStyleSheet("QTableWidget {background-color: #ffffff; font: 바른공군체; font-size: 16px;}"
                                        "QTableWidget::item { padding: 5px; }")
        self.assets_table.setSelectionBehavior(QTableView.SelectRows)
        self.assets_table.itemChanged.connect(self.on_checkbox_changed)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 50)
        header.resizeSection(-1, 100)

        # 헤더 텍스트 중앙 정렬 및 자동 줄바꿈
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블 설정
        self.assets_table.horizontalHeader().setStretchLastSection(False)
        self.assets_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.assets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 각 열의 내용에 맞게 너비 설정
        for column in range(1, header.count() - 1):
            self.assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        # 헤더 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.assets_table.verticalHeader().setDefaultSectionSize(50)


        button_layout = QHBoxLayout()
        button_layout.setSpacing(1)
        button_layout.setContentsMargins(0, 1, 0, 1)

        self.edit_cal_assets_button = QPushButton(self.tr("수정"), self)
        self.edit_cal_assets_button.clicked.connect(self.edit_cal_assets)

        self.print_button = QPushButton(self.tr("출력"), self)
        self.print_button.clicked.connect(self.print_assets_table)

        self.back_button = QPushButton(self.tr("메인화면"), self)
        self.back_button.clicked.connect(self.parent.show_main_page)


        # 각 버튼에 폰트 적용 및 크기 조정
        for button in [self.edit_cal_assets_button, self.print_button, self.back_button]:
            button.setFont(QFont("강한공군체", 12, QFont.Bold))
            button.setFixedSize(150, 50)  # 버튼 크기 고정 (너비 300, 높이 50)
            button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬

        button_layout.addWidget(self.edit_cal_assets_button)
        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.back_button)

        # 왼쪽 레이아웃에 위젯 추가 (변경된 부분)
        left_layout.addWidget(filter_group)
        left_layout.addWidget(dal_group)
        left_layout.addWidget(self.assets_table, 1)  # stretch factor를 1로 설정하여 남은 공간을 채우도록 함
        left_layout.addLayout(button_layout)



        # 오른쪽 레이아웃 구성
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        map_print_button_layout = QVBoxLayout()

        # 지도 출력 버튼
        self.map_print_button = QPushButton(self.tr("지도 출력"), self)
        self.map_print_button.setFont(QFont("강한공군체", 12, QFont.Bold))
        self.map_print_button.setFixedSize(120, 30)
        self.map_print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.map_print_button.clicked.connect(self.print_map)
        map_print_button_layout.addWidget(self.map_print_button, alignment=Qt.AlignRight)

        right_layout.addLayout(map_print_button_layout)



        self.map_view = QWebEngineView()
        right_layout.addWidget(self.map_view)

        self.stacked_widget = QStackedWidget(self)
        self.bmd_priority_page = BmdPriority(self)
        self.engagement_effectiveness_page = EngagementEffect(self)
        self.stacked_widget.addWidget(self.bmd_priority_page)
        self.stacked_widget.addWidget(self.engagement_effectiveness_page)


        right_layout.addWidget(self.stacked_widget)


        right_splitter = QSplitter(Qt.Vertical)

        right_splitter.addWidget(self.map_view)
        right_splitter.addWidget(self.stacked_widget)
        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 1)

        # 오른쪽 레이아웃에 수직 스플리터 추가
        right_layout.addWidget(right_splitter)

        # 스플리터에 좌우 위젯 추가
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # 메인 레이아웃에 스플리터 추가
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        # 방어자산 체크박스 이벤트 연결
        self.dal_checkbox.stateChanged.connect(self.load_assets)

        self.load_assets()

        # 우측 하단에 버튼 추가
        right_bottom_layout = QHBoxLayout()
        self.bmd_priority_button = QPushButton(self.tr("BMD 우선순위"), self)
        self.engagement_effect_button = QPushButton(self.tr("교전효과 수준"), self)

        for button in [self.bmd_priority_button, self.engagement_effect_button]:
            button.setFont(QFont("강한공군체", 12, QFont.Bold))
            button.setFixedSize(150, 50)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #4a86e8;
                    color: white;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
            """)

        right_bottom_layout.addWidget(self.bmd_priority_button)
        right_bottom_layout.addWidget(self.engagement_effect_button)

        # 버튼 클릭 이벤트 연결
        self.bmd_priority_button.clicked.connect(self.show_bmd_priority)
        self.engagement_effect_button.clicked.connect(self.show_engagement_effect)

        # 우측 레이아웃에 버튼 추가
        right_layout.addLayout(right_bottom_layout)

    def on_checkbox_changed(self, item):
        if item.column() == 0:
            self.update_map()

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.engagement_filter.setCurrentIndex(0)
        self.bmd_priority_filter.setCurrentIndex(0)
        self.assets_table.uncheckAllRows()
        self.dal_checkbox.setChecked(False)
        self.asset_search_input.clear()  # 검색 입력창 비우기
        self.load_assets()  # 테이블 데이터 새로고침
        self.update_map()

    def update_map(self):
        self.map = folium.Map(
            location=[self.parent.map_app.loadSettings()['latitude'], self.parent.map_app.loadSettings()['longitude']],
            zoom_start=self.parent.map_app.loadSettings()['zoom'],
            tiles=self.parent.map_app.loadSettings()['style'])
        selected_assets = self.get_selected_assets()
        if selected_assets:
            CalMapView(selected_assets, self.map)
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

    def get_selected_assets(self):
        selected_assets = []
        for row in range(self.assets_table.rowCount()):
            checkbox_widget = self.assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.isChecked():
                unit = self.assets_table.item(row, 2).text()
                asset_name = self.assets_table.item(row, 6).text()
                area = self.assets_table.item(row, 7).text()
                coordinate = self.assets_table.item(row, 8).text()
                engagement_effectiveness = self.assets_table.item(row, 15).text()
                bmd_priority = self.assets_table.item(row, 16).text()
                selected_assets.append((unit, asset_name, area, coordinate, engagement_effectiveness, bmd_priority))
        return selected_assets

    def load_assets(self):
        """데이터베이스에서 자산 정보를 로드하여 테이블에 표시하는 함수"""
        unit_filter = self.unit_filter.currentText()
        engagement_filter = self.engagement_filter.currentText()
        bmd_priority_filter = self.bmd_priority_filter.currentText()
        search_text = self.asset_search_input.text().strip()

        query = f'''
                    SELECT 
                        id, unit, asset_number, manager, contact,
                        target_asset, area, coordinate, mgrs, description,
                        dal_select, weapon_system, ammo_count, threat_degree, engagement_effectiveness, bmd_priority,
                        COALESCE(criticality, 0) + COALESCE(criticality_bonus_center, 0) + COALESCE(criticality_bonus_function, 0),
                        COALESCE(vulnerability_damage_protection, 0) + COALESCE(vulnerability_damage_dispersion, 0) + COALESCE(vulnerability_recovery_time, 0) + COALESCE(vulnerability_recovery_ability, 0),
                        COALESCE(threat_attack, 0) + COALESCE(threat_detection, 0),
                        (COALESCE(criticality, 0) + COALESCE(criticality_bonus_center, 0) + COALESCE(criticality_bonus_function, 0)) +
                        (COALESCE(vulnerability_damage_protection, 0) + COALESCE(vulnerability_damage_dispersion, 0) + COALESCE(vulnerability_recovery_time, 0) + COALESCE(vulnerability_recovery_ability, 0)) +
                        (COALESCE(threat_attack, 0) + COALESCE(threat_detection, 0)) AS total_score
                    FROM cal_assets_{self.parent.selected_language}
                    '''

        conditions = []
        parameters = []

        if self.dal_checkbox.isChecked():
            conditions.append("dal_select = ?")
            parameters.append(1)

        if unit_filter != self.tr("전체"):
            conditions.append("unit = ?")
            parameters.append(unit_filter)

        if engagement_filter != self.tr("전체"):
            conditions.append("engagement_effectiveness = ?")
            parameters.append(engagement_filter)

        if bmd_priority_filter != self.tr("전체"):
            conditions.append("bmd_priority = ?")
            parameters.append(bmd_priority_filter)

        if search_text:
            search_conditions = [
                "target_asset LIKE ?",
                "asset_number LIKE ?",
                "area LIKE ?",
                "coordinate LIKE ?",
                "mgrs LIKE ?"
            ]
            conditions.append(f"({' OR '.join(search_conditions)})")
            parameters.extend([f'%{search_text}%'] * 5)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += "ORDER BY total_score DESC"

        self.parent.cursor.execute(query, parameters)
        asset_data = self.parent.cursor.fetchall()

        self.assets_table.setRowCount(0)
        for row_position, asset in enumerate(asset_data):
            self.assets_table.insertRow(row_position)
            checkbox_widget = CenteredCheckBox()
            checkbox_widget.checkbox.stateChanged.connect(self.update_map)  # 체크박스 상태 변경 시 지도 업데이트
            self.assets_table.setCellWidget(row_position, 0, checkbox_widget)
            for col_position, value in enumerate(asset):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.assets_table.setItem(row_position, col_position + 1, item)

            delete_button = QPushButton(self.tr("삭제"))
            delete_button.setFont(QFont("바른공군체", 13))
            delete_button.setMaximumWidth(100)
            delete_button.clicked.connect(lambda _, row=row_position: self.delete_asset(row))
            self.assets_table.setCellWidget(row_position, 21, delete_button)

        self.assets_table.setColumnHidden(1, True)
        self.assets_table.setColumnHidden(3, True)
        self.assets_table.setColumnHidden(4, True)
        self.assets_table.setColumnHidden(5, True)
        self.assets_table.setColumnHidden(8, True)

        self.assets_table.setColumnHidden(9, True)
        self.assets_table.setColumnHidden(10, True)
        self.assets_table.setColumnHidden(11, True)
        self.assets_table.setColumnHidden(12, True)
        self.assets_table.setColumnHidden(13, True)
        self.assets_table.setColumnHidden(14, True)

    def edit_cal_assets(self):
        checked_rows = [row for row in range(self.assets_table.rowCount())
                        if self.assets_table.cellWidget(row, 0) and
                        self.assets_table.cellWidget(row, 0).isChecked()]

        if len(checked_rows) != 1:
            QMessageBox.warning(self, self.tr("경고"), self.tr("수정을 위해 정확히 하나의 자산을 선택해주세요."))
            return

        row = checked_rows[0]
        asset_id = int(self.assets_table.item(row, 1).text())
        self.parent.add_asset_page.set_edit_mode(True)  # 편집 모드로 설정
        self.parent.show_edit_asset_page()
        self.parent.add_asset_page.set_data(asset_id)

    def delete_asset(self, row):
        """선택된 자산을 삭제"""
        asset_id = self.assets_table.item(row, 1).text()
        target_asset = self.assets_table.item(row, 6).text()
        reply = QMessageBox.question(self, self.tr("확인"), self.tr("정말로 '{}' (ID: {}) 을(를) 삭제하시겠습니까?".format(target_asset, asset_id)),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent.cursor.execute("DELETE FROM cal_assets_ko WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            self.parent.cursor.execute("DELETE FROM cal_assets_en WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            self.load_assets()

    def show_bmd_priority(self):
        self.stacked_widget.setCurrentWidget(self.bmd_priority_page)
        self.bmd_priority_page.load_table_data()

    def show_engagement_effect(self):
        self.stacked_widget.setCurrentWidget(self.engagement_effectiveness_page)
        self.engagement_effectiveness_page.load_assets()

    def print_assets_table(self):
        try:
            document = QTextDocument()
            cursor = QTextCursor(document)

            # CSS 스타일 수정
            document.setDefaultStyleSheet("""
                @page { size: A4; margin: 20mm; }
                body { 
                    font-family: 'Arial', sans-serif;
                    width: 100%;
                    margin: 0 auto;
                }
                h1 { 
                    color: black; 
                    text-align: center;
                    margin-bottom: 20px;
                }
                .info { padding: 1px; }
                table { 
                    border-collapse: collapse; 
                    width: 90%;
                    margin: 0 auto;
                    text-align: center;
                }
                td, th { 
                    border: 1px solid black; 
                    padding: 5px; 
                    text-align: center;
                }
            """)

            font = QFont("Arial", 8)
            document.setDefaultFont(font)

            cursor.insertHtml("<h1 align='center'>" + self.tr("CAL 목록") + "</h1>")
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

            rows = self.assets_table.rowCount() + 1
            cols = self.assets_table.columnCount() - 1

            excluded_columns = [0, 1, 3, 4, 5, 9, 10, 11, 12, 13, 14, 16]

            actual_cols = cols - len(excluded_columns)
            table = cursor.insertTable(rows, actual_cols, table_format)

            header_col = 0
            for col in range(cols):
                if col not in excluded_columns:
                    cell = table.cellAt(0, header_col)
                    cellCursor = cell.firstCursorPosition()
                    cellCursor.insertHtml(f"<th>{self.assets_table.horizontalHeaderItem(col).text()}</th>")
                    header_col += 1

            for row in range(self.assets_table.rowCount()):
                data_col = 0
                for col in range(cols):
                    if col not in excluded_columns:
                        item = self.assets_table.item(row, col)
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
                printer.setPageSize(QPageSize(QPageSize.A4))
                printer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Millimeter)
                printer.setPageOrientation(QPageLayout.Landscape)
                document.print_(printer)
                QMessageBox.information(self, self.tr("저장 완료"), self.tr("PDF가 저장되었습니다: {}").format(file_path))

            QCoreApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr("다음 오류가 발생했습니다: {}").format(str(e)))

    def print_map(self, *args):  # *args를 추가하여 추가 인자를 무시합니다.
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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))

            full_map = self.map_view.grab()

            content_rect = page_rect.adjusted(0, title_rect.height() + 10, 0, -30)
            scaled_image = full_map.scaled(QSize(int(content_rect.width()), int(content_rect.height())),
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)

            x = int(content_rect.left() + (content_rect.width() - scaled_image.width()) / 2)
            y = int(content_rect.top() + (content_rect.height() - scaled_image.height()) / 2)
            painter.drawImage(x, y, scaled_image.toImage())

            info_font = QFont("Arial", 8)
            painter.setFont(info_font)
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            info_text = f"인쇄 일시: {current_time}"
            painter.drawText(page_rect.adjusted(10, -20, -10, -10), Qt.AlignBottom | Qt.AlignRight, info_text)

            painter.end()
        except Exception as e:
            logging.error(f"인쇄 중 오류 발생: {str(e)}")
            self.print_success = False
        else:
            self.print_success = True

    def print_finished(self):
        if self.print_success:
            QMessageBox.information(self, self.tr("인쇄 완료"), self.tr("지도가 성공적으로 출력되었습니다."))
        else:
            QMessageBox.warning(self, self.tr("인쇄 실패"), self.tr("지도 출력 중 오류가 발생했습니다."))


class MainWindow(QMainWindow, QObject):
    """메인 윈도우 클래스"""

    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect('assets_management.db')
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setWindowTitle(self.tr("CAL 자산 보기"))
        self.cursor = self.conn.cursor()
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)
        self.map_app = MapApp()
        self.selected_language = "ko"
        self.translator = Translator(QApplication.instance())

        self.view_assets_page = CalViewWindow(self)
        self.add_asset_page = AddAssetWindow(self)

        self.stacked_widget.addWidget(self.view_assets_page)
        self.stacked_widget.addWidget(self.add_asset_page)
        self.show_main_page()


    def show_main_page(self):
        self.stacked_widget.setCurrentIndex(0)

    def load_assets(self):
        self.view_assets_page.load_assets()

    def show_add_asset_page(self):
        """자산 추가 페이지 표시"""
        self.refresh_database()  # 데이터 갱신
        self.stacked_widget.setCurrentWidget(self.add_asset_page)

    def show_edit_asset_page(self):
        self.refresh_database()
        self.add_asset_page.reset_data()
        self.stacked_widget.setCurrentWidget(self.add_asset_page)

    def show_view_assets_page(self):
        """자산 추가 페이지 표시"""
        self.refresh_database()  # 데이터 갱신
        self.stacked_widget.setCurrentWidget(self.view_assets_page)

    def refresh_database(self):
        """데이터베이스 연결을 새로 고치기 위한 메서드"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        self.conn = sqlite3.connect('assets_management.db')
        self.cursor = self.conn.cursor()

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

