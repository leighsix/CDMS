from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator
from addasset import AddAssetWindow
import sys, json
import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from languageselection import Translator, LanguageSelectionWindow
from cal_map_view import CalMapView
from PyQt5.QtGui import QIcon, QFont, QTextDocument, QTextCursor, QTextTableFormat, QTextLength, QColor
from PyQt5.QtCore import QObject, QRect
from setting import SettingWindow, MapApp
import re  # 입력 검증에 사용
import hashlib  # 해시함수 사용
import hmac  # 메시지 인증코드 (MAC) 사용

class BmdPriorityWindow(QtWidgets.QDialog):
    def __init__(self, parent):
        super(BmdPriorityWindow, self).__init__(parent)
        self.parent = parent
        self.setMinimumSize(1024, 768)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 40, 30, 30)

        self.priority_table = QTableWidget()
        self.priority_table.setColumnCount(5)
        self.priority_table.setRowCount(5)
        self.priority_table.setHorizontalHeaderLabels([
            self.tr("구분"), self.tr("작계 0단계"), self.tr("작계 1단계"),
            self.tr("작계 2단계"), self.tr("작계 3단계")
        ])

        # 테이블 스타일 설정
        self.priority_table.setAlternatingRowColors(True)
        self.priority_table.verticalHeader().setVisible(False)  # 왼쪽 헤더열 숨기기
        self.priority_table.setStyleSheet(
            "QTableWidget {background-color: #f0f0f0; font: 바른공군체; font-size: 18px;}"
            "QTableWidget::item { padding: 0px; }"
            "QHeaderView::section { background-color: #4a86e8; color: white; font-weight: bold; font-size: 18px; }"
        )

        # 헤더 폰트 설정
        font = QFont("강한공군체", 18)  # 폰트 크기를 18로 변경
        font.setBold(True)
        self.priority_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.priority_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # 행 높이 설정
        self.priority_table.verticalHeader().setDefaultSectionSize(60)  # 행 높이를 60으로 설정

        priorities = [self.tr('1순위'), self.tr('2순위'), self.tr('3순위'), self.tr('4순위'), self.tr('5순위')]
        # 구분 열 고정값 설정 및 다른 셀 편집 가능하게 설정
        for row in range(5):
            item = QTableWidgetItem(priorities[row])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#e6f2ff"))
            self.priority_table.setItem(row, 0, item)

        # 모든 셀의 텍스트를 중앙 정렬로 설정
        for row in range(self.priority_table.rowCount()):
            for col in range(1, self.priority_table.columnCount()):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                self.priority_table.setItem(row, col, item)

        self.priority_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        layout.addWidget(self.priority_table)

        button_layout = QHBoxLayout()

        self.save_button = QPushButton(self.tr("저장"), self)
        self.save_button.clicked.connect(self.save_table_data)

        self.print_button = QPushButton(self.tr("출력"), self)
        self.print_button.clicked.connect(self.print_table)

        self.back_button = QPushButton(self.tr("메인화면"), self)
        self.back_button.clicked.connect(self.parent.show_main_page)

        for button in [self.save_button, self.print_button, self.back_button]:
            button.setFont(QFont("강한공군체", 15, QFont.Bold))
            button.setFixedSize(200, 50)
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
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.load_table_data()  # 초기 로드

    def save_table_data(self):
        ko_data = []
        en_data = []
        for row in range(self.priority_table.rowCount()):
            ko_row_data = []
            en_row_data = []
            for col in range(self.priority_table.columnCount()):
                item = self.priority_table.item(row, col)
                text = item.text() if item else ""
                if self.parent.selected_language == 'ko':
                    ko_row_data.append(text)
                    en_row_data.append(self.translate_to_english(text))
                else:
                    en_row_data.append(text)
                    ko_row_data.append(self.translate_to_korean(text))

            ko_data.append(ko_row_data)
            en_data.append(en_row_data)

        with open('bmd_priority_data_ko.json', 'w', encoding='utf-8') as f:
            json.dump(ko_data, f, ensure_ascii=False, indent=4)

        with open('bmd_priority_data_en.json', 'w', encoding='utf-8') as f:
            json.dump(en_data, f, ensure_ascii=False, indent=4)

        QMessageBox.information(self, self.tr("저장 완료"), self.tr("테이블 데이터가 한국어와 영어로 저장되었습니다."))

    def load_table_data(self):
        file_name = f'bmd_priority_data_{self.parent.selected_language}.json'
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.priority_table.setRowCount(len(data))
            for row, row_data in enumerate(data):
                for col, cell_data in enumerate(row_data):
                    if col == 0:  # 구분 열은 건드리지 않음
                        continue
                    item = QTableWidgetItem(cell_data)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.priority_table.setItem(row, col, item)
        except FileNotFoundError:
            pass  # 파일이 없으면 아무것도 하지 않음

    @staticmethod
    def translate_to_english(korean_text):
        bmd_priority_en = {
            "": "",
            "지휘통제시설": "C2",
            "비행단": "Fighter Group",
            "군수기지": "Logistics Base",
            "해군기지": "Naval Base",
            "주요레이다": "Radar Site"
        }
        return bmd_priority_en.get(korean_text, korean_text)

    @staticmethod
    def translate_to_korean(english_text):
        bmd_priority_ko = {
            "": "",
            "C2": "지휘통제시설",
            "Fighter Group": "비행단",
            "Logistics Base": "군수기지",
            "Naval Base": "해군기지",
            "Radar Site": "주요레이다"
        }
        return bmd_priority_ko.get(english_text, english_text)

    def print_table(self):
        document = QTextDocument()
        cursor = QTextCursor(document)
        document.setDefaultStyleSheet("""
            body { font-family: 'Arial', sans-serif; }
            h1 { color: black; }
            .info { padding: 10px; }
            table { border-collapse: collapse; width: 100%; }
            td, th { border: 1px solid black; padding: 4px; text-align: center; }
        """)

        font = QFont("Arial", 8)
        document.setDefaultFont(font)

        cursor.insertHtml("<h1 align='center'>" + self.tr("연합사령관 BMD 전력배치 우선순위") + "</h1>")
        cursor.insertBlock()

        table_format = QTextTableFormat()
        table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
        table_format.setCellPadding(5)
        table_format.setAlignment(Qt.AlignCenter)
        table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))

        table = cursor.insertTable(self.priority_table.rowCount() + 1, self.priority_table.columnCount(), table_format)

        for col in range(self.priority_table.columnCount()):
            cell = table.cellAt(0, col)
            cellCursor = cell.firstCursorPosition()
            cellCursor.insertText(self.priority_table.horizontalHeaderItem(col).text())

        for row in range(self.priority_table.rowCount()):
            for col in range(self.priority_table.columnCount()):
                item = self.priority_table.item(row, col)
                cell = table.cellAt(row + 1, col)
                cellCursor = cell.firstCursorPosition()
                cellCursor.insertText(item.text() if item else "")

        preview = QPrintPreviewDialog()
        preview.paintRequested.connect(lambda p: document.print_(p))
        preview.exec_()

class EngagementEffectWindow(QtWidgets.QDialog):
    """저장된 자산을 보여주는 창"""

    def __init__(self, parent):
        super(EngagementEffectWindow, self).__init__(parent)
        self.parent = parent
        self.db_path = parent.db_path  # db_path 속성 추가
        self.setMinimumSize(1024, 768)
        self.initUI()

    def initUI(self):
        """UI 구성"""
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

        # 필터 변경 시 자동 갱신
        self.unit_filter.currentIndexChanged.connect(self.filter_assets)

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
        # 찾기 버튼 연결
        self.find_button.clicked.connect(self.filter_assets)
        filter_layout.addWidget(self.find_button)

        # 여백 추가
        filter_layout.addStretch()

        # 필터 그룹에 레이아웃 설정
        filter_group.setLayout(filter_layout)

        # 메인 레이아웃에 필터 그룹 추가
        layout.addWidget(filter_group)

        # 테이블 위젯 생성 및 설정
        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(3)
        self.assets_table.setHorizontalHeaderLabels([self.tr("구분"), self.tr("내용"), self.tr("주요자산목록")])
        self.assets_table.setRowCount(4)

        # 왼쪽 헤더열 숨기기
        self.assets_table.verticalHeader().setVisible(False)

        # 테이블 스타일 설정
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.setStyleSheet(
            "QTableWidget {background-color: #f0f0f0; font: 바른공군체; font-size: 18px;}"
            "QTableWidget::item { padding: 0px; }"
            "QHeaderView::section { background-color: #4a86e8; color: white; font-weight: bold; font-size: 18px; }"
        )

        # 헤더 폰트 설정
        font = QFont("강한공군체", 18)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # 1열 고정
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)  # 2열 고정
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절
        header.resizeSection(0, 150)
        header.resizeSection(1, 200)

        # 헤더 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.assets_table.verticalHeader().setDefaultSectionSize(70)

        # 헤더 텍스트 중앙 정렬 및 자동 줄바꿈
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블 설정
        self.assets_table.setWordWrap(True)  # 자동 줄바꿈 활성화
        self.assets_table.horizontalHeader().setStretchLastSection(False)
        self.assets_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.assets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 테이블 셀 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # 내용 열 채우기
        contents = [self.tr("1단계: 원격발사대"), self.tr("2단계: 단층방어"), self.tr("3단계: 중첩방어"), self.tr("4단계: 다층방어")]
        for row, content in enumerate(contents):
            for col in range(3):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                if col == 0:
                    item.setText(content.split(": ")[0])
                    item.setBackground(QColor("#e6f2ff"))
                elif col == 1:
                    item.setText(content.split(": ")[1])
                    item.setBackground(QColor("#e6f2ff"))
                self.assets_table.setItem(row, col, item)

        # 세 번째 열 자동 줄바꿈 설정
        self.assets_table.setWordWrap(True)
        layout.addWidget(self.assets_table)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 10, 0, 10)


        self.print_button = QPushButton(self.tr("출력"), self)
        self.print_button.clicked.connect(self.print_assets_table)

        self.back_button = QPushButton(self.tr("메인화면"), self)
        self.back_button.clicked.connect(self.parent.show_main_page)

        # 버튼 스타일 설정
        for button in [self.print_button, self.back_button]:
            button.setFont(QFont("강한공군체", 15, QFont.Bold))
            button.setFixedSize(200, 50)
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

        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.back_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.load_assets()

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.asset_search_input.clear()  # 검색 입력창 비우기
        self.load_assets()  # 테이블 데이터 새로고침

    def filter_assets(self):
        """필터와 검색어를 적용하여 자산 목록을 필터링하는 함수"""
        filter_text = self.unit_filter.currentText()
        search_text = self.asset_search_input.text().lower()

        try:
            conn = sqlite3.connect(self.parent.db_path)
            cursor = conn.cursor()

            table_name = f"cal_assets_{self.parent.selected_language}"

            # 각 행별로 필터링 적용
            for row in range(self.assets_table.rowCount()):
                show_row = True

                # 1,2열은 그대로 유지
                engagement_level = self.assets_table.item(row, 0).text()

                # 3열(자산목록)에 대해서만 필터링 적용
                if filter_text != self.tr("전체"):
                    # 선택된 unit에 해당하는 자산 검색
                    query = f"""
                    SELECT target_asset 
                    FROM {table_name}
                    WHERE engagement_effectiveness LIKE ? 
                    AND unit = ?
                    """
                    cursor.execute(query, (f'%{engagement_level}%', filter_text))
                else:
                    # 전체 자산 검색
                    query = f"""
                    SELECT target_asset
                    FROM {table_name}  
                    WHERE engagement_effectiveness LIKE ?
                    """
                    cursor.execute(query, (f'%{engagement_level}%',))

                results = cursor.fetchall()
                filtered_assets = ', '.join([r[0] for r in results])

                # 검색어 필터링 적용
                if search_text:
                    # 자산명/지역명 검색
                    query = f"""
                    SELECT target_asset
                    FROM {table_name}
                    WHERE engagement_effectiveness LIKE ?
                    AND (target_asset LIKE ? OR area LIKE ?)
                    """
                    cursor.execute(query,
                                   (f'%{engagement_level}%', f'%{search_text}%', f'%{search_text}%'))
                    search_results = cursor.fetchall()
                    filtered_assets = ', '.join([r[0] for r in search_results])

                    if not search_results:
                        show_row = False

                # 필터링된 결과를 3열에 표시
                asset_item = QTableWidgetItem(filtered_assets)
                asset_item.setTextAlignment(Qt.AlignCenter)
                self.assets_table.setItem(row, 2, asset_item)

                # 행 표시/숨김 처리
                self.assets_table.setRowHidden(row, not show_row)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "데이터베이스 오류", f"데이터베이스 오류가 발생했습니다: {e}")

        finally:
            if conn:
                conn.close()

    def load_assets(self):
        keywords = [
            self.tr("1단계: 원격발사대"),
            self.tr("2단계: 단층방어"),
            self.tr("3단계: 중첩방어"),
            self.tr("4단계: 다층방어")
        ]

        try:
            conn = sqlite3.connect(self.db_path)  # db_path 사용
            cursor = conn.cursor()

            table_name = f"cal_assets_{self.parent.selected_language}"

            for row, keyword in enumerate(keywords):
                query = f"""
                SELECT target_asset
                FROM {table_name}
                WHERE engagement_effectiveness LIKE ?
                """
                cursor.execute(query, ('%' + keyword + '%',))
                results = cursor.fetchall()

                target_assets = ', '.join([result[0] for result in results]) if results else ''

                self.assets_table.setItem(row, 2, QTableWidgetItem(target_assets))

            self.assets_table.resizeColumnsToContents()
            self.assets_table.resizeRowsToContents()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "데이터베이스 오류", f"데이터베이스 오류가 발생했습니다: {e}")
        finally:
            if conn:
                conn.close()

    def print_assets_table(self):
        try:
            document = QTextDocument()
            cursor = QTextCursor(document)

            document.setDefaultStyleSheet("""
                body { font-family: 'Arial', sans-serif; }
                h1 { color: black; }
                .info { padding: 10px; }
                table { border-collapse: collapse; width: 100%; }
                td, th { border: 1px solid black; padding: 4px; text-align: center; }
            """)

            font = QFont("Arial", 8)
            document.setDefaultFont(font)

            cursor.insertHtml("<h1 align='center'>" + self.tr("교전효과 수준") + "</h1>")
            cursor.insertBlock()


            table_format = QTextTableFormat()
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            table_format.setCellPadding(1)
            table_format.setAlignment(Qt.AlignCenter)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))

            rows = 0
            for row in range(self.assets_table.rowCount()):
                if not self.assets_table.isRowHidden(row):
                    rows += 1

            table = cursor.insertTable(rows + 1, self.assets_table.columnCount(), table_format)

            # 헤더 추가
            for col in range(self.assets_table.columnCount()):
                cell = table.cellAt(0, col)
                cellCursor = cell.firstCursorPosition()
                cellCursor.insertHtml(f"<th>{self.assets_table.horizontalHeaderItem(col).text()}</th>")

            # 데이터 추가
            table_row = 1
            for row in range(self.assets_table.rowCount()):
                if not self.assets_table.isRowHidden(row):
                    for col in range(self.assets_table.columnCount()):
                        item = self.assets_table.item(row, col)
                        if item:
                            cell = table.cellAt(table_row, col)
                            cellCursor = cell.firstCursorPosition()
                            cellCursor.insertText(item.text())
                    table_row += 1

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

class BmdPriority(QtWidgets.QDialog):
    def __init__(self, parent):
        super(BmdPriority, self).__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        self.priority_table = QTableWidget()
        self.priority_table.setColumnCount(5)
        self.priority_table.setRowCount(5)
        self.priority_table.setHorizontalHeaderLabels([
            self.tr("구분"), self.tr("작계 0단계"), self.tr("작계 1단계"),
            self.tr("작계 2단계"), self.tr("작계 3단계")
        ])

        # 테이블 스타일 설정
        self.priority_table.setAlternatingRowColors(True)
        self.priority_table.verticalHeader().setVisible(False)  # 왼쪽 헤더열 숨기기
        self.priority_table.setStyleSheet(
            "QTableWidget {background-color: #f0f0f0; font: 바른공군체; font-size: 16px;}"
            "QTableWidget::item { padding: 0px; }"
            "QHeaderView::section { background-color: #4a86e8; color: white; font-weight: bold; font-size: 18px; }"
        )

        # 헤더 폰트 설정
        font = QFont("강한공군체", 15)  # 폰트 크기를 18로 변경
        font.setBold(True)
        self.priority_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.priority_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # 1열 고정
        header.resizeSection(0, 130)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절

        # 헤더 높이 자동 조절
        self.priority_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.priority_table.verticalHeader().setDefaultSectionSize(40)  # 행 높이를 40으로 설정

        # 구분 열 고정값 설정 및 다른 셀 편집 가능하게 설정
        priorities = [self.tr('1순위'), self.tr('2순위'), self.tr('3순위'), self.tr('4순위'), self.tr('5순위')]
        # 구분 열 고정값 설정 및 다른 셀 편집 가능하게 설정
        for row in range(5):
            item = QTableWidgetItem(priorities[row])
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#e6f2ff"))
            self.priority_table.setItem(row, 0, item)

        # 모든 셀의 텍스트를 중앙 정렬로 설정
        for row in range(self.priority_table.rowCount()):
            for col in range(1, self.priority_table.columnCount()):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                self.priority_table.setItem(row, col, item)


        layout.addWidget(self.priority_table)

        self.setLayout(layout)

        self.load_table_data()  # 초기 로드

    def load_table_data(self):
        file_name = f'bmd_priority_data_{self.parent.parent.selected_language}.json'
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.priority_table.setRowCount(len(data))
            for row, row_data in enumerate(data):
                for col, cell_data in enumerate(row_data):
                    if col == 0:  # 구분 열은 건드리지 않음
                        continue
                    item = QTableWidgetItem(cell_data)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.priority_table.setItem(row, col, item)
        except FileNotFoundError:
            pass  # 파일이 없으면 아무것도 하지 않음


class EngagementEffect(QtWidgets.QDialog):
    def __init__(self, parent):
        super(EngagementEffect, self).__init__(parent)
        self.parent = parent
        self.db_path = parent.db_path  # db_path 속성 추가
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(3)
        self.assets_table.setRowCount(4)
        self.assets_table.setHorizontalHeaderLabels([
            self.tr("구분"), self.tr("내용"), self.tr("주요자산목록")
        ])

        # 테이블 스타일 설정
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.verticalHeader().setVisible(False)  # 왼쪽 헤더열 숨기기
        self.assets_table.setStyleSheet(
            "QTableWidget {background-color: #f0f0f0; font: 바른공군체; font-size: 16px;}"
            "QTableWidget::item { padding: 0px; }"
            "QHeaderView::section { background-color: #4a86e8; color: white; font-weight: bold; font-size: 18px; }"
        )

        # 헤더 폰트 설정
        font = QFont("강한공군체", 15)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # 1열 고정
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)  # 2열 고정
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # 3열 자동 조절
        header.resizeSection(0, 150)
        header.resizeSection(1, 200)

        # 헤더 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.assets_table.verticalHeader().setDefaultSectionSize(40)

        # 헤더 텍스트 중앙 정렬 및 자동 줄바꿈
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블 설정
        self.assets_table.setWordWrap(True)  # 자동 줄바꿈 활성화
        self.assets_table.horizontalHeader().setStretchLastSection(False)
        self.assets_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.assets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 테이블 셀 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)


        # 구분 열 고정값 설정 및 다른 셀 편집 가능하게 설정
        contents = [self.tr("1단계: 원격발사대"), self.tr("2단계: 단층방어"), self.tr("3단계: 중첩방어"), self.tr("4단계: 다층방어")]
        for row, content in enumerate(contents):
            item = QTableWidgetItem(content.split(": ")[0])
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#e6f2ff"))
            self.assets_table.setItem(row, 0, item)

            item = QTableWidgetItem(content.split(": ")[1])
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#e6f2ff"))
            self.assets_table.setItem(row, 1, item)

        layout.addWidget(self.assets_table)

        self.setLayout(layout)

        self.load_assets()

    def load_assets(self):
        keywords = [
            self.tr("1단계: 원격발사대"),
            self.tr("2단계: 단층방어"),
            self.tr("3단계: 중첩방어"),
            self.tr("4단계: 다층방어")
        ]

        try:
            conn = sqlite3.connect(self.db_path)  # db_path 사용
            cursor = conn.cursor()

            table_name = f"cal_assets_{self.parent.parent.selected_language}"

            for row, keyword in enumerate(keywords):
                query = f"""
                SELECT target_asset
                FROM {table_name}
                WHERE engagement_effectiveness LIKE ?
                """
                cursor.execute(query, ('%' + keyword + '%',))
                results = cursor.fetchall()

                target_assets = ', '.join([result[0] for result in results]) if results else ''

                self.assets_table.setItem(row, 2, QTableWidgetItem(target_assets))

            self.assets_table.resizeColumnsToContents()
            self.assets_table.resizeRowsToContents()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "데이터베이스 오류", f"데이터베이스 오류가 발생했습니다: {e}")
        finally:
            if conn:
                conn.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setWindowTitle(self.tr("BMD 우선순위"))
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)
        self.selected_language = 'ko'
        self.bmd_priority_page = BmdPriorityWindow(self)
        self.engagement_effectiveness_page = EngagementEffectWindow(self)
        self.stacked_widget.addWidget(self.bmd_priority_page)
        self.stacked_widget.addWidget(self.engagement_effectiveness_page)

        self.show_main_page()

    def show_main_page(self):
        self.stacked_widget.setCurrentWidget(self.engagement_effectiveness_page)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())



