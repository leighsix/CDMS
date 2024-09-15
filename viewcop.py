import sys, os, io
import folium
import sqlite3
import pandas as pd
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir, QRect
from common_map_view import CommonMapView, DefenseAssetCommonMapView
from PyQt5.QtCore import QUrl, QTemporaryFile, QSize
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QUrl, QSize, QTimer, QTemporaryFile, QDir, QEventLoop, QDateTime


class ViewCopWindow(QDialog):
    def __init__(self, parent):
        super(ViewCopWindow, self).__init__(parent)
        self.parent = parent
        self.setWindowTitle(self.tr("공통상황도"))
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.load_dataframes()
        self.map = folium.Map(location=[37.5665, 126.9780], zoom_start=7)
        self.show_defense_radius = False
        self.initUI()
        self.create_map()
        self.update_map()  # 초기 지도 로드

    def load_dataframes(self):
        self.assets_df = pd.DataFrame()
        self.defense_assets_df = pd.DataFrame()

        try:
            conn = sqlite3.connect('assets.db')

            try:
                query = "SELECT * FROM assets_priority WHERE language = ?"
                self.assets_df = pd.read_sql_query(query, conn, params=(self.parent.selected_language,))
            except sqlite3.OperationalError:
                print("assets_priority 테이블이 존재하지 않습니다.")
                self.assets_df = pd.DataFrame(columns=["priority", "unit", "target_asset", "area", "mgrs", "language"])

            try:
                query = "SELECT * FROM defense_assets WHERE language = ?"
                self.defense_assets_df = pd.read_sql_query(query, conn, params=(self.parent.selected_language,))
            except sqlite3.OperationalError:
                print("defense_assets 테이블이 존재하지 않습니다.")
                self.defense_assets_df = pd.DataFrame(columns=["asset_name", "mgrs", "weapon_system", "language"])

        except sqlite3.Error as e:
            print(f"데이터베이스 연결 오류: {e}")

        finally:
            if conn:
                conn.close()

        if self.assets_df.empty and self.defense_assets_df.empty:
            print("경고: 데이터를 불러오지 못했습니다. 빈 DataFrame을 사용합니다.")

    def refresh(self):
        # 데이터프레임 다시 로드
        self.load_dataframes()

        # 필터 초기화
        self.unit_filter.setCurrentIndex(0)  # '전체'로 설정
        self.search_filter.clear()  # 검색창 초기화
        self.display_count_combo.setCurrentIndex(0)  # '전체'로 설정

        # 테이블의 모든 체크박스 해제
        self.assets_table.uncheckAllRows()
        for weapon_system, checkbox in self.defense_assets_checkboxes.items():
            if checkbox.isChecked():
                checkbox.setChecked(False)
        self.radius_checkbox.setChecked(False)

        # 테이블 데이터 다시 로드
        self.load_assets()

        # 지도 업데이트
        self.update_map()

    def create_map(self):
        if self.parent.selected_language == "Korean":
            # 한국 서울 중심
            self.map = folium.Map(location=[37.5665, 126.9780], zoom_start=7)
        else:
            # 아랍에미리트 두바이 중심
            self.map = folium.Map(location=[25.2048, 55.2708], zoom_start=7)

    def initUI(self):
        main_layout = QHBoxLayout()

        # 좌측 레이아웃 (필터 및 테이블)
        left_layout = QVBoxLayout()

        # 필터 추가
        self.filter_layout = QHBoxLayout()

        self.unit_filter = QComboBox()
        self.unit_filter.addItems([self.tr("전체"), self.tr("지상군"), self.tr("해군"), self.tr("공군")])
        self.unit_filter.currentTextChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.unit_filter)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText(self.tr("방어대상자산 또는 지역구분 검색"))
        self.search_filter.textChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.search_filter)

        self.display_count_combo = QComboBox()
        self.display_count_combo.addItems([self.tr("전체"), "30", "50", "100", "200", "300"])
        self.display_count_combo.currentTextChanged.connect(self.load_assets)
        self.filter_layout.addWidget(self.display_count_combo)
        left_layout.addLayout(self.filter_layout)

        # 테이블
        self.assets_table = MyTableWidget()
        self.assets_table.setColumnCount(5)
        self.assets_table.setHorizontalHeaderLabels(
            ["", self.tr("우선순위"), self.tr("구성군"), self.tr("방어대상자산"), self.tr("지역구분")])

        # 행 번호 숨기기
        self.assets_table.verticalHeader().setVisible(False)

        font = QFont("강한공군체", 13)
        font.setBold(True)
        self.assets_table.horizontalHeader().setFont(font)
        header = self.assets_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.resizeSection(0, 40)
        header.resizeSection(1, 80)

        # 헤더 텍스트 중앙 정렬
        for column in range(header.count()):
            item = self.assets_table.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

        # 나머지 열들이 남은 공간을 채우도록 설정
        for column in range(2, header.count()):
            self.assets_table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)

        left_layout.addWidget(self.assets_table)

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

        # 우측 레이아웃 (지도 및 체크박스)
        right_layout = QVBoxLayout()

        # 무기체계 체크박스 그룹
        weapon_group = QGroupBox(self.tr("무기체계"))
        weapon_layout = QHBoxLayout()
        weapon_layout.setContentsMargins(10, 5, 10, 5)  # 여백 조정
        weapon_layout.setSpacing(10)  # 체크박스 간 간격 조정
        self.defense_assets_checkboxes = {}
        defense_assets = self.get_defense_assets()
        for asset in defense_assets:
            checkbox = QCheckBox(asset)
            checkbox.stateChanged.connect(self.update_map)
            self.defense_assets_checkboxes[asset] = checkbox
            weapon_layout.addWidget(checkbox)
        weapon_group.setLayout(weapon_layout)
        weapon_group.setFixedHeight(weapon_layout.sizeHint().height() + 20)  # 높이 조정
        right_layout.addWidget(weapon_group)

        # 방어반경 표시 체크박스와 지도 출력 버튼을 위한 수평 레이아웃
        checkbox_button_layout = QHBoxLayout()

        # 방어반경 표시 체크박스
        self.radius_checkbox = QCheckBox(self.tr("방어반경 표시"), self)
        self.radius_checkbox.stateChanged.connect(self.toggle_defense_radius)
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

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)

        # 지도 뷰
        self.map_view = QWebEngineView()
        right_layout.addWidget(self.map_view)

        self.load_assets()

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.update_map()

    def load_assets(self):
        filtered_df = self.assets_df

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

        display_count = self.display_count_combo.currentText()
        if display_count != self.tr("전체"):
            limit = int(display_count)
            filtered_df = filtered_df.head(limit)
        self.assets_table.uncheckAllRows()
        self.assets_table.setRowCount(len(filtered_df))
        for row, (_, asset) in enumerate(filtered_df.iterrows()):
            checkbox = CenteredCheckBox()
            self.assets_table.setCellWidget(row, 0, checkbox)
            checkbox.checkbox.stateChanged.connect(self.update_map)
            for col, value in enumerate(asset[['priority', 'unit', 'target_asset', 'area']], start=1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.assets_table.setItem(row, col, item)
        self.update_map()

    def get_defense_assets(self):
        return self.defense_assets_df['weapon_system'].unique().tolist()

    def update_map(self):
        self.create_map()
        selected_assets = self.get_selected_assets()
        selected_defense_assets = self.get_selected_defense_assets()
        if selected_assets != []:
            CommonMapView(selected_assets, self.map)
        if selected_defense_assets != []:
            DefenseAssetCommonMapView(selected_defense_assets, self.show_defense_radius, self.map)
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html_content = data.getvalue().decode()
        self.map_view.setHtml(html_content)

    def get_selected_assets(self):
        selected_assets = []
        for row in range(self.assets_table.rowCount()):
            checkbox_widget = self.assets_table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.checkbox.isChecked():
                asset_name = self.assets_table.item(row, 3).text()
                priority = int(self.assets_table.item(row, 1).text())
                area = self.assets_table.item(row, 4).text()
                unit = self.assets_table.item(row, 2).text()

                asset_info = self.assets_df[
                    (self.assets_df['target_asset'] == asset_name) &
                    (self.assets_df['area'] == area) &
                    (self.assets_df['unit'] == unit)
                    ]

                if not asset_info.empty:
                    mgrs_coord = asset_info.iloc[0]['mgrs']
                    selected_assets.append((asset_name, mgrs_coord, priority))
        return selected_assets

    def get_selected_defense_assets(self):
        selected_defense_assets = []
        for weapon_system, checkbox in self.defense_assets_checkboxes.items():
            if checkbox.isChecked():
                assets = self.defense_assets_df[self.defense_assets_df['weapon_system'] == weapon_system]
                for _, asset in assets.iterrows():
                    selected_defense_assets.append((asset['asset_name'], asset['mgrs'], weapon_system, asset['threat_degree']))
        return selected_defense_assets

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")

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
        #self.header_checked = checked
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.checkbox.setChecked(checked)

    def uncheckAllRows(self):
        self.header_checked = False
        # 헤더 체크박스도 해제
        self.horizontalHeader().isOn = False
        self.horizontalHeader().updateSection(0)

class MainWindow(QtWidgets.QMainWindow, QObject):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CAL/DAL Management System")
        self.setWindowIcon(QIcon("logo.png"))
        self.setMinimumSize(800, 600)
        self.selected_language = "Korean"  # 기본 언어 설정
        self.central_widget = QtWidgets.QStackedWidget(self)
        self.setCentralWidget(self.central_widget)
        self.view_cop_window = ViewCopWindow(self)
        self.central_widget.addWidget(self.view_cop_window)


    def show_main_page(self):
        self.central_widget.setCurrentIndex(0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())