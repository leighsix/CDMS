from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator
from addasset import AddAssetWindow
import sys
import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QTextDocument, QTextCursor, QTextTableFormat, QTextFrameFormat, QTextLength, QTextCharFormat, QFont, QTextBlockFormat
from languageselection import Translator, LanguageSelectionWindow
from mapview import CalAssetMapView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, QRect

from setting import SettingWindow, MapApp


class ViewAssetsWindow(QtWidgets.QDialog, QObject):
    """저장된 자산을 보여주는 창"""

    def __init__(self, parent, language="Korean"):
        super(ViewAssetsWindow, self).__init__(parent)
        self.parent = parent
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

        self.assets_table = MyTableWidget()
        self.assets_table.setColumnCount(16)
        self.assets_table.setHorizontalHeaderLabels([
            "", self.tr("ID"), self.tr("구성군"), self.tr("자산번호"), self.tr("담당자"),
            self.tr("연락처"), self.tr("방어대상자산"), self.tr("지역구분"), self.tr("경위도"),
            self.tr("군사좌표(MGRS)"), self.tr("임무/기능 기술"),
            self.tr("중요도"), self.tr("취약성"), self.tr("위협"), self.tr("합산 점수"), self.tr("삭제")
        ])
        self.assets_table.verticalHeader().setVisible(False)

        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.setStyleSheet("QTableWidget {background-color: #ffffff; font: 바른공군체; font-size: 16px;}"
                                        "QTableWidget::item { padding: 8px; }")
        self.assets_table.setSelectionBehavior(QTableView.SelectRows)
        self.assets_table.cellClicked.connect(self.on_row_click)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)

        # 헤더 설정
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setMinimumSectionSize(120)  # 최소 열 너비 설정
        header.resizeSection(0, 100)
        header.resizeSection(-1, 100)

        # 헤더 텍스트 중앙 정렬 및 자동 줄바꿈
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 테이블 설정
        self.assets_table.horizontalHeader().setStretchLastSection(False)
        self.assets_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.assets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 각 열의 내용에 맞게 너비 설정
        for column in range(1, header.count() - 1):
            self.assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        # 헤더 높이 자동 조절
        self.assets_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.assets_table.verticalHeader().setDefaultSectionSize(60)


        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 10, 0, 10)

        self.view_map_button = QPushButton(self.tr("지도 보기"), self)
        self.view_map_button.clicked.connect(self.cal_asset_view_map)

        self.print_button = QPushButton(self.tr("출력"), self)
        self.print_button.clicked.connect(self.print_assets_table)

        self.back_button = QPushButton(self.tr("메인 화면으로 돌아가기"), self)
        self.back_button.clicked.connect(self.parent.show_main_page)


        # 각 버튼에 폰트 적용 및 크기 조정
        for button in [self.view_map_button, self.print_button, self.back_button]:
            button.setFont(QFont("강한공군체", 15, QFont.Bold))
            button.setFixedSize(300, 50)  # 버튼 크기 고정 (너비 300, 높이 50)
            button.setStyleSheet("QPushButton { text-align: center; }")  # 텍스트 가운데 정렬

        button_layout.addWidget(self.view_map_button)
        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.back_button)

        layout.addWidget(self.assets_table)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.load_assets()

    def refresh(self):
        """테이블을 초기 상태로 되돌리고 필터를 초기화하는 함수"""
        self.unit_filter.setCurrentIndex(0)  # 콤보박스를 "전체"로 설정
        self.asset_search_input.clear()  # 검색 입력창 비우기
        self.load_assets()  # 테이블 데이터 새로고침

    def on_row_click(self, row, column):
        """특정 행 클릭 시 자산 데이터 로드 및 수정 창으로 이동하는 메서드"""
        if column == 15:  # '삭제' 버튼 클릭 시
            self.delete_asset(row)
        else:
            asset_id = self.assets_table.item(row, 1).text()
            self.parent.add_asset_page.set_data(asset_id)
            self.parent.show_edit_asset_page()

    def load_assets(self):
        """데이터베이스에서 자산 정보를 로드하여 테이블에 표시하는 함수"""
        unit_filter = self.unit_filter.currentText()
        search_text = self.asset_search_input.text().strip()

        query = f'''
                    SELECT 
                        id, unit, asset_number, manager, contact,
                        target_asset, area, coordinate, mgrs, description,
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

        if unit_filter != self.tr("전체"):
            conditions.append("unit = ?")
            parameters.append(unit_filter)

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
            self.assets_table.setCellWidget(row_position, 0, checkbox_widget)
            for col_position, value in enumerate(asset):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.assets_table.setItem(row_position, col_position + 1, item)

            delete_button = QPushButton(self.tr("삭제"))
            delete_button.setFont(QFont("바른공군체", 13))
            delete_button.setMaximumWidth(100)
            delete_button.clicked.connect(lambda _, row=row_position: self.delete_asset(row))
            self.assets_table.setCellWidget(row_position, 15, delete_button)

        self.assets_table.setColumnHidden(1, True)
        self.assets_table.setColumnHidden(4, True)
        self.assets_table.setColumnHidden(5, True)
        self.assets_table.setColumnHidden(9, True)
        self.assets_table.setColumnHidden(10, True)

    def delete_asset(self, row):
        """선택된 자산을 삭제"""
        asset_id = self.assets_table.item(row, 1).text()
        print(asset_id)
        target_asset = self.assets_table.item(row, 6).text()
        print(target_asset)
        reply = QMessageBox.question(self, self.tr("확인"), self.tr("정말로 '{}' (ID: {}) 을(를) 삭제하시겠습니까?".format(target_asset, asset_id)),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.parent.cursor.execute("DELETE FROM cal_assets_ko WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            self.parent.cursor.execute("DELETE FROM cal_assets_en WHERE id = ?", (asset_id,))
            self.parent.conn.commit()
            self.load_assets()

    def cal_asset_view_map(self):
        selected_assets = []

        for row in range(self.assets_table.rowCount()):
            checkbox_widget = self.assets_table.cellWidget(row, 0)
            if checkbox_widget.isChecked():
                unit = self.assets_table.item(row, 2).text()
                asset_name = self.assets_table.item(row, 6).text()
                coordinate = self.assets_table.item(row,8).text()
                mgrs = self.assets_table.item(row, 9).text()
                selected_assets.append((unit, asset_name, coordinate, mgrs))

        if not selected_assets:
            QMessageBox.warning(self, self.tr("경고"), self.tr("선택된 자산이 없습니다."))
            return
        print(self.parent.map_app.loadSettings())
        map_view = CalAssetMapView(selected_assets, self.parent.map_app.loadSettings())
        map_view.exec_()

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

            cursor.insertHtml("<h1 align='center'>" + self.tr("CAL 목록") + "</h1>")
            cursor.insertBlock()


            table_format = QTextTableFormat()
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            table_format.setCellPadding(1)
            table_format.setAlignment(Qt.AlignCenter)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))

            rows = self.assets_table.rowCount() + 1
            cols = self.assets_table.columnCount() - 1

            excluded_columns = [0, 1, 4, 5, 9, 10]

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
                document.print_(printer)
                QMessageBox.information(self, self.tr("저장 완료"), self.tr("PDF가 저장되었습니다: {}").format(file_path))

            QCoreApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr("다음 오류가 발생했습니다: {}").format(str(e)))

    def show_message(self, message):
        """메시지 박스 출력 함수"""
        QMessageBox.information(self, self.tr("정보"), message)


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

        self.view_assets_page = ViewAssetsWindow(self, self.selected_language)
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


