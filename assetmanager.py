from PyQt5 import QtGui
import sys, os, datetime
import sqlite3
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from enemy_base import EnemyBaseWindow
from languageselection import LanguageSelectionWindow, Translator
from loginwindow import LoginWindow
from addasset import AddAssetWindow
from cvtcalculation import CVTCalculationWindow
from setting import SettingWindow, MapApp
from viewasset import ViewAssetsWindow
from defenseasset import ViewDefenseAssetWindow
from viewcop import ViewCopWindow
from weapon_system import WeaponSystemWindow
from enemy_spec import EnemySpecWindow
from database_merge import DatabaseIntegrationWindow
from PyQt5.QtCore import QObject, QPointF, center
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen, QPainterPath, QPixmap, QFontMetrics
from PyQt5.QtCore import Qt, QSize, QParallelAnimationGroup, QRect, QTimer, QDateTime
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime
from bcrypt import hashpw, gensalt, checkpw # bcrypt 추가
import secrets # secrets 모듈 추가
import re, string



class AssetManager(QtWidgets.QMainWindow, QObject):
    def __init__(self, db_path='assets_management.db'):
        super(AssetManager, self).__init__()
        self.translator = Translator(QApplication.instance())
        self.language_selection_window = LanguageSelectionWindow(self)
        self.db_path = db_path
        self.animation_group = None  # 애니메이션 그룹 초기화
        self.current_user = None
        self.login_time = None
        # 폰트 로딩 추가
        self.load_custom_font()
        self.map_app = MapApp()

        # stacked_widget 초기화 추가
        self.stacked_widget = QStackedWidget()
        self.start_application()

    def load_custom_font(self):
        # 실행 파일의 경로 확인
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        # 폰트 파일 경로
        font_path = os.path.join(application_path, 'font\바른공군체 Medium.ttf')

        # 폰트 로딩
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
            self.custom_font = QtGui.QFont(font_family, 12, QtGui.QFont.Bold)
        else:
            print("폰트 로딩 실패")
            self.custom_font = QtGui.QFont("Arial", 12, QtGui.QFont.Bold)

    def start_application(self):
        if self.language_selection_window.exec_() == QDialog.Accepted:
            self.selected_language = self.language_selection_window.language
            self.translator.load(self.selected_language)
            self.login_window = LoginWindow(self)
            if self.login_window.exec_() == QDialog.Accepted:
                self.current_user = self.login_window.username
                self.db_path = self.login_window.db_name
                self.login_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                self.create_database()
                self.refresh_database()
                self.initUI()
                self.show()  # 메인 창 표시
            else:
                sys.exit()
        else:
            sys.exit()

    def initUI(self):
        self.setWindowTitle(self.tr("CDMS"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1000, 600)

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 타이틀바 추가
        self.titleBar = FancyTitleBar(self)
        main_layout.addWidget(self.titleBar)

        # 스택 위젯 생성
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 메인 페이지 생성
        self.main_page = QWidget()
        main_page_layout = QHBoxLayout(self.main_page)  # QHBoxLayout으로 변경

        # 좌측 영역 (버튼 영역)
        button_widget = QWidget()
        button_widget.setMinimumWidth(330)  # 왼쪽 섹터 너비 증가
        button_layout = QVBoxLayout(button_widget)
        self.create_buttons(button_layout)
        main_page_layout.addWidget(button_widget)

        # 중앙 영역
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.create_center_area(center_layout)
        main_page_layout.addWidget(center_widget, 2)  # 가중치 추가

        # 우측 영역
        self.right_area = RightArea(self)
        self.right_area.setFixedWidth(330)  # 오른쪽 영역 너비를 300으로 설정
        main_page_layout.addWidget(self.right_area)

        self.stacked_widget.addWidget(self.main_page)

        # 다른 페이지들 추가
        self.add_asset_page = AddAssetWindow(self)
        self.view_assets_page = ViewAssetsWindow(self)
        self.cvt_calculation_page = CVTCalculationWindow(self)
        self.defense_assets_page = ViewDefenseAssetWindow(self)
        self.view_cop_page = ViewCopWindow(self)
        self.weapon_system_page = WeaponSystemWindow(self)
        self.enemy_base_page = EnemyBaseWindow(self)
        self.enemy_spec_page = EnemySpecWindow(self)
        self.setting_page = SettingWindow(self)
        self.stacked_widget.addWidget(self.add_asset_page)
        self.stacked_widget.addWidget(self.view_assets_page)
        self.stacked_widget.addWidget(self.cvt_calculation_page)
        self.stacked_widget.addWidget(self.defense_assets_page)
        self.stacked_widget.addWidget(self.view_cop_page)
        self.stacked_widget.addWidget(self.weapon_system_page)
        self.stacked_widget.addWidget(self.enemy_base_page)
        self.stacked_widget.addWidget(self.enemy_spec_page)
        self.stacked_widget.addWidget(self.setting_page)

        self.stacked_widget.setCurrentWidget(self.main_page)

        # 창 크기 및 위치 설정
        self.showMaximized()

    def create_buttons(self, layout):
        buttons = [
            (self.tr("CAL 관리"), [
                (self.tr("CAL 입력"), self.show_add_asset_page),
                (self.tr("CAL 보기"), self.show_view_assets_page),
                (self.tr("CVT 산출"), self.show_cvt_calculation_page)
            ]),
            (self.tr("DAL 관리"), [
                (self.tr("DAL 입력/보기"), self.show_defense_assets_page),
                (self.tr("방공무기체계"), self.show_weapon_system_page)
            ]),
            (self.tr("적 정보"), [
                (self.tr("적 미사일 발사기지"), self.show_enemy_base_page),
                (self.tr("적 미사일 제원"), self.show_enemy_spec_page)
            ]),
            (self.tr("공통상황도"), self.show_view_cop_page),
            (self.tr("종  료"), self.close)
        ]

        button_table = QTableWidget()
        button_table.setColumnCount(1)
        button_table.setRowCount(len(buttons))
        button_table.verticalHeader().setVisible(False)
        button_table.horizontalHeader().setVisible(False)
        button_table.setShowGrid(False)
        button_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        button_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for i, (text, sub_buttons) in enumerate(buttons):
            main_btn = QPushButton(text)
            main_btn.setStyleSheet("""
                text-align: left;
                padding: 15px;
                font-weight: bold;
                font-size: 18px;
                background-color: #3498db;
                color: white;
                border: none;
                margin-bottom: 2px;
            """)

            if isinstance(sub_buttons, list):
                sub_widget = QWidget()
                sub_layout = QVBoxLayout(sub_widget)
                sub_layout.setContentsMargins(0, 0, 0, 0)
                sub_layout.setSpacing(2)
                for sub_text, func in sub_buttons:
                    sub_btn = QPushButton(sub_text)
                    sub_btn.setStyleSheet("""
                        text-align: left;
                        padding: 10px 20px;
                        font-size: 16px;
                        background-color: #ecf0f1;
                        color: #2c3e50;
                        border: none;
                        margin-left: 15px;
                    """)
                    sub_btn.clicked.connect(func)
                    sub_layout.addWidget(sub_btn)

                cell_widget = QWidget()
                cell_layout = QVBoxLayout(cell_widget)
                cell_layout.setContentsMargins(0, 0, 0, 5)
                cell_layout.setSpacing(2)
                cell_layout.addWidget(main_btn)
                cell_layout.addWidget(sub_widget)

                main_btn.clicked.connect(lambda checked, w=sub_widget: self.toggle_sub_buttons(w))
            else:
                cell_widget = main_btn
                main_btn.clicked.connect(sub_buttons)

            button_table.setCellWidget(i, 0, cell_widget)

        button_table.resizeRowsToContents()

        scroll_area = QScrollArea()
        scroll_area.setWidget(button_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #f9f9f9;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
            }
        """)

        layout.addWidget(scroll_area)

    def toggle_sub_buttons(self, sub_widget):
        sub_widget.setVisible(not sub_widget.isVisible())
        self.sender().parentWidget().parentWidget().parentWidget().resizeRowsToContents()

    def create_center_area(self, layout):
        # 중앙 영역을 위한 위젯 생성
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        # 배경 이미지
        background_label = QLabel()
        pixmap = QPixmap("image/airdefense10.png")
        background_label.setPixmap(pixmap)
        background_label.setScaledContents(True)
        background_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        center_layout.addWidget(background_label, 1)  # stretch factor 1

        # 데이터베이스 요약 정보 (테이블)
        summary_table = self.create_summary_table()
        center_layout.addWidget(summary_table)

        # 저작권 정보
        copyright_label = QLabel("© 2024 ROK AF LT.COL Jo Yongho and ROK Navy CDR Cho Hyunchel. All rights reserved.")
        copyright_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        center_layout.addWidget(copyright_label)

        # 중앙 위젯을 메인 레이아웃에 추가
        layout.addWidget(center_widget)

    def create_summary_table(self):
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(1)

        # 테이블 헤더 설정
        table.setHorizontalHeaderLabels([self.tr("CAL 자산"), self.tr("DAL 자산"), self.tr("적 기지")])

        # 데이터 가져오기
        cal_assets_count = self.get_count("cal_assets_en")
        dal_assets_count = self.get_count("dal_assets_en")
        enemy_bases_count = self.get_count("enemy_bases_en")

        # 데이터 설정
        table.setItem(0, 0, QTableWidgetItem(str(cal_assets_count)))
        table.setItem(0, 1, QTableWidgetItem(str(dal_assets_count)))
        table.setItem(0, 2, QTableWidgetItem(str(enemy_bases_count)))

        # 테이블 스타일 설정
        table.setStyleSheet("""
            QTableWidget {
                background-color: #f0f0f0;
                alternate-background-color: #e0e0e0;
                selection-background-color: #a6a6a6;
            }
            QHeaderView::section {
                background-color: #646464;
                color: white;
                padding: 4px;
                border: 1px solid #fffff8;
                font-weight: bold;
            }
        """)

        # 테이블 크기 조정
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setFixedHeight(100)  # 테이블의 높이를 고정

        # 행 번호 열 숨기기
        table.verticalHeader().setVisible(False)

        # 테이블 아이템 중앙 정렬
        for i in range(table.rowCount()):
            for j in range(table.columnCount()):
                item = table.item(i, j)
                if item is not None:
                    item.setTextAlignment(Qt.AlignCenter)

        return table

    def get_count(self, table_name):
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return self.cursor.fetchone()[0]

    def show_main_page(self):
        self.refresh_database()
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.titleBar.update_title(self.tr("C D M S"), self.tr("CAL/DAL Management System"))

    def show_add_asset_page(self):
        self.refresh_database()
        self.add_asset_page.refresh()
        self.stacked_widget.setCurrentWidget(self.add_asset_page)
        self.titleBar.update_title(self.tr("CAL 관리"), self.tr("CAL 입력"))

    def show_edit_asset_page(self):
        self.refresh_database()
        self.stacked_widget.setCurrentWidget(self.add_asset_page)
        self.titleBar.update_title(self.tr("CAL 관리"), self.tr("CAL 수정"))

    def show_view_assets_page(self):
        self.refresh_database()
        self.view_assets_page.refresh()
        self.stacked_widget.setCurrentWidget(self.view_assets_page)
        self.view_assets_page.load_assets()
        self.titleBar.update_title(self.tr("CAL 관리"), self.tr("CAL 보기"))

    def show_cvt_calculation_page(self):
        self.refresh_database()
        self.cvt_calculation_page.refresh()
        self.stacked_widget.setCurrentWidget(self.cvt_calculation_page)
        self.cvt_calculation_page.load_all_assets()
        self.titleBar.update_title(self.tr("CAL 관리"), self.tr("CVT 산출"))

    def show_defense_assets_page(self):
        self.refresh_database()
        self.defense_assets_page.refresh()
        self.stacked_widget.setCurrentWidget(self.defense_assets_page)
        self.defense_assets_page.load_all_assets()
        self.titleBar.update_title(self.tr("DAL 관리"), self.tr("DAL 입력/보기"))

    def show_weapon_system_page(self):
        # 방공무기체계 페이지 구현
        weapon_system_window = WeaponSystemWindow(self)
        weapon_system_window.show()

    def show_enemy_base_page(self):
        # 적 미사일 발사기지 페이지 구현
        self.refresh_database()
        self.enemy_base_page.refresh()
        self.stacked_widget.setCurrentWidget(self.enemy_base_page)
        self.titleBar.update_title(self.tr("적 미사일 기지정보"), self.tr("적 미사일 발사위치"))

    def show_enemy_spec_page(self):
        enemy_spec_window = EnemySpecWindow(self)
        enemy_spec_window.show()

    def show_view_cop_page(self):
        self.refresh_database()
        self.view_cop_page.refresh()
        self.stacked_widget.setCurrentWidget(self.view_cop_page)
        self.view_cop_page.load_assets()
        self.titleBar.update_title(self.tr("공통상황도"), self.tr("Common Operational Picture"))

    def create_database(self):
        """SQLite 데이터베이스 생성 및 테이블 설정"""
        self.conn = sqlite3.connect(self.db_path)  # 'assets.db' 데이터베이스에 연결
        self.cursor = self.conn.cursor()  # 커서 생성
        # 자산 정보를 저장할 테이블 생성
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
        self.conn.commit()  # 변경사항 커밋
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
        self.conn.commit()
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
        self.cursor.execute('''
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

    def refresh_database(self):
        """데이터베이스 연결을 새로 고치기 위한 메서드"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def closeEvent(self, event):
        """창 닫기 이벤트 처리 - 데이터베이스 연결 종료"""
        self.conn.close()  # 데이터베이스 연결 종료

    def load_assets(self):
        self.refresh_database()  # 데이터 갱신
        self.view_assets_page.load_assets()

    def logoff(self):
        reply = QMessageBox.question(self, self.tr('로그아웃'), self.tr("정말 로그아웃하시겠습니까?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            new_instance = AssetManager()
            new_instance.show()

class FancyTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        # 왼쪽 섹터
        self.logo_title_widget = LogoTitleWidget()
        layout.addWidget(self.logo_title_widget, 1)

        # 중앙 섹터
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        self.title_label = TitleLabel(self.tr("C D M S"), self.tr("CAL/DAL Management System"))
        center_layout.addWidget(self.title_label, 0, Qt.AlignCenter)
        layout.addWidget(center_widget, 2)

        # 오른쪽 섹터
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        self.korea_flag = QLabel()
        pixmap = QPixmap("image/korea.png")
        self.korea_flag.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        right_layout.addWidget(self.korea_flag, 0, Qt.AlignRight)
        layout.addWidget(right_widget, 1)

        self.setLayout(layout)

    def update_title(self, title, subtitle=None):
        self.title_label.update_title(title, subtitle)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 그라데이션 배경
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(20, 40, 80))    # 진한 네이비
        gradient.setColorAt(0.5, QColor(40, 70, 120)) # 중간 네이비
        gradient.setColorAt(1, QColor(20, 40, 80))    # 진한 네이비
        painter.fillRect(self.rect(), gradient)

        # 상단 하이라이트
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawLine(0, 1, self.width(), 1)

        # 하단 그림자
        painter.setPen(QPen(QColor(0, 0, 0, 50), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        # 패턴 오버레이
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.SolidLine))
        for i in range(0, self.width(), 40):
            painter.drawLine(i, 0, i, self.height())

        super().paintEvent(event)

class TitleLabel(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.setMinimumHeight(70)
        self.setMinimumWidth(600)  # 최소 너비 설정

    def update_title(self, title, subtitle=None):
        self.title = title
        self.subtitle = subtitle if subtitle else ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 타이틀 설정
        title_font = QFont("Arial", 32, QFont.Bold)
        title_metrics = QFontMetrics(title_font)
        title_width = title_metrics.width(self.title)

        # 서브타이틀 설정
        subtitle_font = QFont("Arial", 14)
        subtitle_metrics = QFontMetrics(subtitle_font)

        # 타이틀 그리기
        title_path = QPainterPath()
        title_path.addText(QPointF(0, 45), title_font, self.title)

        # 그림자 효과
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.translate(2, 2)
        painter.drawPath(title_path)
        painter.translate(-2, -2)

        # 타이틀 그라데이션
        title_gradient = QLinearGradient(0, 0, title_width, 0)
        title_gradient.setColorAt(0, QColor(255, 215, 0))
        title_gradient.setColorAt(1, QColor(255, 140, 0))

        # 타이틀 테두리
        painter.strokePath(title_path, QPen(QColor(100, 100, 100), 2))
        painter.fillPath(title_path, title_gradient)

        # 서브타이틀
        painter.setFont(subtitle_font)
        x = title_width + 10
        y = 45

        for char in self.subtitle:
            if (self.subtitle == "CAL/DAL Management System" and char in "CDMS") or (self.subtitle == "Common Operational Picture" and char in "COP") :
                painter.setPen(QColor(255, 255, 0))  # 강조 색상
                painter.setFont(QFont("Arial", 16, QFont.Bold))
            else:
                painter.setPen(QColor(220, 220, 220))  # 일반 텍스트 색상
                painter.setFont(subtitle_font)

            painter.drawText(QPointF(x, y), char)
            x += painter.fontMetrics().width(char)

    def sizeHint(self):
        return QSize(500, 70)  # 적절한 크기 힌트 제공

class LogoTitleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QHBoxLayout(self)

        # 로고
        self.logoLabel = QLabel()
        logo_pixmap = QPixmap("image/logo.png")
        self.logoLabel.setPixmap(logo_pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        main_layout.addWidget(self.logoLabel)

        # 타이틀 레이아웃
        title_layout = QVBoxLayout()

        # 타이틀 컨테이너
        title_container = QWidget()
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(0, 0, 0, 0)
        title_container_layout.setSpacing(0)

        # 한글 타이틀
        self.koreanLabel = QLabel("대한민국 국방부")
        self.koreanLabel.setFont(QFont('맑은 고딕', 14, QFont.Bold))
        self.koreanLabel.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        title_container_layout.addWidget(self.koreanLabel)

        # 영어 타이틀
        self.englishLabel = QLabel("Ministry of National Defense")
        self.englishLabel.setFont(QFont('Arial', 8))
        self.englishLabel.setStyleSheet("color: #FFFFFF;")
        title_container_layout.addWidget(self.englishLabel)

        title_container_layout.setAlignment(Qt.AlignLeft)  # 컨테이너 내부 왼쪽 정렬
        title_layout.addWidget(title_container)
        title_layout.setAlignment(Qt.AlignVCenter)  # 세로 중앙 정렬

        main_layout.addLayout(title_layout)
        main_layout.setAlignment(Qt.AlignLeft)  # 전체를 왼쪽 정렬
        main_layout.setContentsMargins(10, 10, 10, 10)  # 여백 추가

        self.setLayout(main_layout)

class RightArea(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_user = self.parent.current_user
        self.login_time = datetime.now()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.create_right_area(layout)

    def create_right_area(self, layout):
        # 로그인 정보
        login_info = QGroupBox()
        login_info.setStyleSheet("""
            QGroupBox {
                background-color: #f0f0f0;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        login_layout = QVBoxLayout(login_info)

        # 사용자 정보
        user_label = QLabel(f"사용자: {self.current_user}")
        user_label.setFont(QFont("Arial", 12, QFont.Bold))
        login_layout.addWidget(user_label)

        # 로그인 시간 및 경과 시간
        time_layout = QVBoxLayout()  # QHBoxLayout에서 QVBoxLayout으로 변경

        # 로그인 시간
        login_time_layout = QHBoxLayout()
        login_time_icon = QLabel()
        login_time_icon.setPixmap(QPixmap("path/to/clock_icon.png").scaled(16, 16, Qt.KeepAspectRatio))
        login_time_label = QLabel(self.tr(f"로그인: {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"))
        login_time_layout.addWidget(login_time_icon)
        login_time_layout.addWidget(login_time_label)
        login_time_layout.addStretch()

        # 경과 시간
        duration_layout = QHBoxLayout()
        duration_icon = QLabel()
        duration_icon.setPixmap(QPixmap("path/to/timer_icon.png").scaled(16, 16, Qt.KeepAspectRatio))
        self.duration_label = QLabel(self.tr("경과 시간: 00:00:00"))
        duration_layout.addWidget(duration_icon)
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()

        time_layout.addLayout(login_time_layout)
        time_layout.addLayout(duration_layout)
        login_layout.addLayout(time_layout)

        # 경과 시간 업데이트를 위한 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.timer.start(1000)  # 1초마다 업데이트

        # 버튼 레이아웃 생성
        button_layout = QHBoxLayout()

        # PW 변경 버튼 추가
        change_pw_btn = QPushButton(self.tr("PW 변경"))
        change_pw_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFA500;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #FF8C00;
                    }
                """)
        change_pw_btn.clicked.connect(self.show_change_password)
        button_layout.addWidget(change_pw_btn)

        # 로그아웃 버튼
        logout_btn = QPushButton(self.tr("로그아웃"))
        logout_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
        logout_btn.clicked.connect(self.parent.logoff)
        button_layout.addWidget(logout_btn)

        login_layout.addLayout(button_layout)

        layout.addWidget(login_info)

        # 설정 버튼을 테이블로 변경
        settings_table = QTableWidget()
        settings_table.setColumnCount(1)
        settings_table.setRowCount(1)
        settings_table.verticalHeader().setVisible(False)
        settings_table.horizontalHeader().setVisible(False)
        settings_table.setShowGrid(False)
        settings_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        settings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        main_btn = QPushButton(self.tr("설 정"))
        main_btn.setIcon(QIcon("path/to/settings_icon.png"))
        main_btn.setStyleSheet("""
                    text-align: center;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 18px;
                    background-color: #3498db;
                    color: white;
                    border: none;
                    margin-bottom: 2px;
                """)

        sub_widget = QWidget()
        sub_layout = QVBoxLayout(sub_widget)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(2)

        map_settings_btn = QPushButton(self.tr("지도설정"))
        map_settings_btn.setStyleSheet("""
                    text-align: left;
                    padding: 10px 20px;
                    font-size: 16px;
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: none;
                    margin-left: 15px;
                """)
        map_settings_btn.clicked.connect(self.show_setting_page)

        db_integration_btn = QPushButton(self.tr("데이터베이스 통합"))
        db_integration_btn.setStyleSheet("""
                    text-align: left;
                    padding: 10px 20px;
                    font-size: 16px;
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: none;
                    margin-left: 15px;
                """)
        # 데이터베이스 통합 버튼의 기능 구현
        db_integration_btn.clicked.connect(self.show_db_integration)

        sub_layout.addWidget(map_settings_btn)
        sub_layout.addWidget(db_integration_btn)

        cell_widget = QWidget()
        cell_layout = QVBoxLayout(cell_widget)
        cell_layout.setContentsMargins(0, 0, 0, 5)
        cell_layout.setSpacing(2)
        cell_layout.addWidget(main_btn)
        cell_layout.addWidget(sub_widget)

        main_btn.clicked.connect(lambda checked, w=sub_widget: self.toggle_sub_buttons(w))

        settings_table.setCellWidget(0, 0, cell_widget)
        settings_table.resizeRowsToContents()

        layout.addWidget(settings_table)
        layout.addStretch()

    def update_duration(self):
        # 로그인 경과 시간 계산 및 업데이트
        elapsed_time = datetime.now() - self.login_time
        hours, remainder = divmod(elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.duration_label.setText(f"경과 시간: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def toggle_sub_buttons(self, widget):
        widget.setVisible(not widget.isVisible())

    # 새로운 페이지 표시 메서드
    def show_setting_page(self):
        # 설정 페이지 구현
        setting_window = SettingWindow(self)
        setting_window.show()

    def show_db_integration(self):
        integration_window = DatabaseIntegrationWindow(self)
        integration_window.exec_()

    def show_change_password(self):
        change_pw_window = ChangePasswordWindow(self.current_user, self)
        if change_pw_window.exec_() == QDialog.Accepted:
            # 비밀번호가 성공적으로 변경됨, user_credentials.db 업데이트
            self.update_password_in_db(self.current_user, change_pw_window.new_password)
            QMessageBox.information(self, "성공", "비밀번호가 변경되었습니다.")

    def update_password_in_db(self, username, new_password):
        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()

        # 시큐어 코딩 가이드에 따라 최소 길이 및 복잡성 검사 추가
        if not self.check_password_complexity(new_password):
            QMessageBox.warning(self, "오류", "비밀번호는 최소 8자 이상이어야 하며, 대문자, 소문자, 숫자 및 특수 문자를 포함해야 합니다.")
            return False  # 비밀번호 변경 실패를 나타냄

        # bcrypt를 사용하여 비밀번호 해싱 - work factor 조정
        hashed_password = hashpw(new_password.encode('utf-8'), gensalt(rounds=12))  # work factor 12로 조정

        cursor.execute("UPDATE users SET password=? WHERE username=?", (hashed_password, username))
        conn.commit()
        conn.close()
        return True  # 비밀번호 변경 성공을 나타냄

    def check_password_complexity(self, password):
        # 최소 길이 8자, 대문자, 소문자, 숫자, 특수 문자 포함 여부 확인
        if len(password) < 8:
            return False
        if not re.search("[a-z]", password):
            return False
        if not re.search("[A-Z]", password):
            return False
        if not re.search("[0-9]", password):
            return False
        if not re.search("[!@#$%^&*()]", password):  # 특수문자 범위 명시
            return False
        return True

class ChangePasswordWindow(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("비밀번호 변경"))
        self.username = username
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.current_pw_input = QLineEdit()
        self.current_pw_input.setEchoMode(QLineEdit.Password)
        form.addRow(self.tr("현재 비밀번호:"), self.current_pw_input)

        self.new_pw_input = QLineEdit()
        self.new_pw_input.setEchoMode(QLineEdit.Password)
        form.addRow(self.tr("새 비밀번호:"), self.new_pw_input)

        self.confirm_pw_input = QLineEdit()
        self.confirm_pw_input.setEchoMode(QLineEdit.Password)
        form.addRow(self.tr("비밀번호 확인:"), self.confirm_pw_input)

        self.ok_button = QPushButton(self.tr("확인"))
        self.ok_button.clicked.connect(self.check_password)
        layout.addLayout(form)
        layout.addWidget(self.ok_button)

    def check_password(self):
        current_pw = self.current_pw_input.text()
        new_pw = self.new_pw_input.text()
        confirm_pw = self.confirm_pw_input.text()

        # 현재 비밀번호와 새 비밀번호가 같은지 확인
        if current_pw == new_pw:
            QMessageBox.warning(self, self.tr("오류"), self.tr("현재 비밀번호와 다른 비밀번호를 입력해야됩니다."))
            return

        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (self.username,))
        db_password = cursor.fetchone()[0]
        conn.close()

        # 비밀번호 복잡성 검사 추가 - RightArea의 메서드 활용
        if self.parent().check_password_complexity(new_pw):
            if new_pw == confirm_pw:
                if checkpw(current_pw.encode('utf-8'), db_password):
                    self.new_password = new_pw
                    # RightArea에서 비밀번호 업데이트 및 결과 처리
                    if self.parent().update_password_in_db(self.username, new_pw):
                        self.accept()
                else:
                    QMessageBox.warning(self, self.tr("오류"), self.tr("현재 비밀번호가 일치하지 않습니다."))
            else:
                QMessageBox.warning(self, self.tr("오류"), self.tr("새 비밀번호가 일치하지 않습니다."))
        else:
            QMessageBox.warning(self,self.tr("오류"), self.tr("비밀번호는 최소 8자 이상이어야 하며, 대문자, 소문자, 숫자 및 특수 문자를 포함해야 합니다."))

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # QApplication 인스턴스 생성
    app.setFont(QtGui.QFont("바른공군체", 12, QtGui.QFont.Bold))  # 애플리케이션 전역 글꼴 설정
    # 앱 인스턴스 생성 및 실행
    window = AssetManager()  # AssetManager 인스턴스 생성
    window.show()  # 창 표시
    sys.exit(app.exec_())  # 애플리케이션 실행
