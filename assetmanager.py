from PyQt5 import QtGui
import sys, os
import sqlite3
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from languageselection import LanguageSelectionWindow, Translator
from loginwindow import LoginWindow
from addasset import AddAssetWindow
from cvtcalculation import CVTCalculationWindow
from viewasset import ViewAssetsWindow
from defenseasset import ViewDefenseAssetWindow
from viewcop import ViewCopWindow
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject, QPointF
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen, QPainterPath, QPixmap, QFontMetrics
from PyQt5.QtCore import Qt, QSize, QParallelAnimationGroup


class AssetManager(QtWidgets.QMainWindow, QObject):
    def __init__(self, db_path='assets_management.db'):
        super(AssetManager, self).__init__()
        self.create_database()
        self.translator = Translator(QApplication.instance())
        self.language_selection_window = LanguageSelectionWindow(self)
        self.db_path = db_path
        self.refresh_database()
        self.animation_group = None  # 애니메이션 그룹 초기화
        # 폰트 로딩 추가
        self.load_custom_font()
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
                self.initUI()
            else:
                sys.exit()
        else:
            sys.exit()

    def initUI(self):
        self.setWindowTitle(self.tr("CDMS"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1200, 600)


        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.titleBar = FancyTitleBar(self)
        main_layout.addWidget(self.titleBar)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 메인 페이지 생성
        self.main_page = QWidget()
        main_page_layout = QHBoxLayout(self.main_page)
        main_page_layout.setContentsMargins(0, 0, 0, 0)

        # 배경 이미지 설정
        self.background_label = QLabel(self.main_page)
        self.background_pixmap = QPixmap("image/airdefense7.png")
        self.background_label.setPixmap(self.background_pixmap)
        self.background_label.setScaledContents(True)
        self.background_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_page_layout.addWidget(self.background_label)

        # 버튼 컨테이너 위젯
        self.button_container = QWidget(self.background_label)
        button_layout = QVBoxLayout(self.button_container)
        button_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        button_layout.setSpacing(20)
        button_layout.setContentsMargins(20, 20, 20, 20)

        # 버튼 컨테이너의 크기 설정
        self.button_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 버튼 생성
        self.cal_management_button = QPushButton(self.tr("CAL 관리"))
        self.dal_management_button = QPushButton(self.tr("DAL 관리"))
        self.view_cop_button = QPushButton(self.tr("공통상황도"))
        self.logoff_button = QPushButton(self.tr("로그오프"))
        self.exit_button = QPushButton(self.tr("종료"))
        # 새로운 버튼 추가
        self.settings_button = QPushButton(self.tr("설정"))
        self.weapon_system_button = QPushButton(self.tr("방공무기체계"))
        self.enemy_missile_base_button = QPushButton(self.tr("적 미사일 발사기지"))

        # CAL 관리 하위 버튼
        self.cal_sub_buttons = QWidget(self.button_container)
        cal_sub_layout = QVBoxLayout(self.cal_sub_buttons)
        cal_sub_layout.setSpacing(10)
        cal_sub_layout.setContentsMargins(0, 0, 0, 0)
        self.add_asset_button = QPushButton(self.tr("CAL 입력"))
        self.view_assets_button = QPushButton(self.tr("CAL 보기"))
        self.calculate_cvt_button = QPushButton(self.tr("CVT 산출"))
        cal_sub_layout.addWidget(self.add_asset_button)
        cal_sub_layout.addWidget(self.view_assets_button)
        cal_sub_layout.addWidget(self.calculate_cvt_button)
        self.cal_sub_buttons.setVisible(False)  # 초기 상태를 숨김으로 설정

        # CAL 관리 버튼과 하위 버튼을 수직으로 배치
        cal_container = QVBoxLayout()
        cal_container.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        cal_container.addWidget(self.cal_management_button)
        cal_container.addWidget(self.cal_sub_buttons)

        # 버튼 레이아웃에 추가
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.weapon_system_button)
        button_layout.addWidget(self.enemy_missile_base_button)
        button_layout.addWidget(self.cal_management_button)

        # 버튼 레이아웃에 추가
        button_layout.addLayout(cal_container)
        button_layout.addWidget(self.dal_management_button)
        button_layout.addWidget(self.view_cop_button)
        button_layout.addWidget(self.logoff_button)
        button_layout.addWidget(self.exit_button)

        # 버튼 스타일 및 크기 설정
        main_buttons = [self.cal_management_button, self.dal_management_button, self.view_cop_button,
                        self.logoff_button, self.exit_button]
        sub_buttons = [self.add_asset_button, self.view_assets_button, self.calculate_cvt_button, self.settings_button,
                       self.weapon_system_button, self.enemy_missile_base_button]

        for button in main_buttons + sub_buttons:
            button.setFont(QFont("강한공군체", 16, QFont.Bold))
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 180);
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(200, 200, 200, 180);
                }
            """)

        for button in main_buttons:
            button.setFixedHeight(60)
            button.setMinimumWidth(220)
            button.setMaximumWidth(300)

        for button in sub_buttons:
            button.setFixedHeight(40)
            button.setMinimumWidth(170)
            button.setMaximumWidth(250)

        # 버튼 간격 조정을 위한 스페이서 추가
        for i in range(4):  # 4개의 스페이서 추가 (버튼 사이)
            spacer = QSpacerItem(40, 100, QSizePolicy.Minimum, QSizePolicy.Expanding)
            button_layout.insertItem(i * 2 + 1, spacer)

        # 버튼 클릭 이벤트 연결
        self.settings_button.clicked.connect(self.show_settings_page)
        self.weapon_system_button.clicked.connect(self.show_weapon_system_page)
        self.enemy_missile_base_button.clicked.connect(self.show_enemy_missile_base_page)
        self.cal_management_button.clicked.connect(self.toggle_cal_sub_buttons)
        self.dal_management_button.clicked.connect(self.show_defense_assets_page)
        self.view_cop_button.clicked.connect(self.show_view_cop_page)
        self.logoff_button.clicked.connect(self.logoff)
        self.exit_button.clicked.connect(self.close)
        self.add_asset_button.clicked.connect(self.show_add_asset_page)
        self.view_assets_button.clicked.connect(self.show_view_assets_page)
        self.calculate_cvt_button.clicked.connect(self.show_cvt_calculation_page)

        # 페이지 추가
        self.stacked_widget.addWidget(self.main_page)
        self.add_asset_page = AddAssetWindow(self)
        self.view_assets_page = ViewAssetsWindow(self)
        self.cvt_calculation_page = CVTCalculationWindow(self)
        self.defense_assets_page = ViewDefenseAssetWindow(self)
        self.view_cop_page = ViewCopWindow(self)
        self.stacked_widget.addWidget(self.add_asset_page)
        self.stacked_widget.addWidget(self.view_assets_page)
        self.stacked_widget.addWidget(self.cvt_calculation_page)
        self.stacked_widget.addWidget(self.defense_assets_page)
        self.stacked_widget.addWidget(self.view_cop_page)

        self.stacked_widget.setCurrentWidget(self.main_page)

        # 창 크기 및 위치 설정
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            (screen_geometry.width() - 1400) // 2,
            (screen_geometry.height() - 900) // 2,
            1400,
            900
        )

    def toggle_cal_sub_buttons(self):
        is_expanded = self.cal_sub_buttons.isVisible()
        self.cal_sub_buttons.setVisible(not is_expanded)
        self.cal_management_button.setText(self.tr("CAL 관리 ▼" if not is_expanded else "CAL 관리"))

    def logoff(self):
        reply = QMessageBox.question(self, self.tr('로그오프'), self.tr("정말 로그오프하시겠습니까?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()  # 현재 창 닫기
            new_instance = AssetManager()  # 새 인스턴스 생성
            new_instance.show()  # 새 인스턴스 표시

    def adjust_font_size(self):
        # 화면 크기에 따라 글자 크기 조정
        screen_size = self.size()
        font_size = min(screen_size.width() // 30, 16)  # 화면 크기에 기반한 최대 글자 크기
        font = QFont()
        font.setPointSize(font_size)

        # 모든 버튼에 글꼴 설정
        for button in [self.add_asset_button, self.view_assets_button, self.calculate_cvt_button,
                       self.exit_button, self.logoff_button]:
            button.setFont(font)

    def show_main_page(self):
        """메인 페이지로 이동하고 모든 페이지 새로고침"""
        self.refresh_database()  # 데이터베이스 새로고침
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.titleBar.update_title(self.tr("C D M S"), self.tr("CAL/DAL Management System"))

    # 새로운 페이지 표시 메서드
    def show_settings_page(self):
        # 설정 페이지 구현
        settings_window = SettingsWindow(self)
        settings_window.show()

    def show_weapon_system_page(self):
        # 방공무기체계 페이지 구현
        weapon_system_window = WeaponSystemWindow(self)
        weapon_system_window.show()

    def show_enemy_missile_base_page(self):
        # 적 미사일 발사기지 페이지 구현
        enemy_missile_base_window = EnemyMissileBaseWindow(self)
        enemy_missile_base_window.show()

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
        self.titleBar.update_title(self.tr("DAL 관리"), None)

    def show_view_cop_page(self):
        self.refresh_database()
        self.view_cop_page.refresh()
        self.stacked_widget.setCurrentWidget(self.view_cop_page)
        self.view_cop_page.load_assets()
        self.titleBar.update_title(self.tr("공통상황도"), self.tr("Common Operational Picture"))

    def create_database(self):
        """SQLite 데이터베이스 생성 및 테이블 설정"""
        self.conn = sqlite3.connect('assets_management.db')  # 'assets.db' 데이터베이스에 연결
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


class FancyTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        # LogoTitleWidget 추가
        self.logo_title_widget = LogoTitleWidget()
        layout.addWidget(self.logo_title_widget)

        # 스페이서 추가
        layout.addStretch()

        # 제목 추가
        self.title_label = TitleLabel(self.tr("C D M S"), self.tr("CAL/DAL Management System"))
        layout.addWidget(self.title_label)

        # 나머지 공간을 채우기 위한 스페이서 추가
        layout.addStretch()

        # 태극기 이미지 추가
        self.korea_flag = QLabel()
        pixmap = QPixmap("image/korea.png")
        self.korea_flag.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.korea_flag)

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




if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # QApplication 인스턴스 생성
    app.setFont(QtGui.QFont("바른공군체", 12, QtGui.QFont.Bold))  # 애플리케이션 전역 글꼴 설정
    # 앱 인스턴스 생성 및 실행
    window = AssetManager()  # AssetManager 인스턴스 생성
    window.show()  # 창 표시
    sys.exit(app.exec_())  # 애플리케이션 실행
