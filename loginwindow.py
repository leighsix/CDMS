import sys
import sqlite3
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTranslator, QLocale, QLibraryInfo, QObject, QPoint, QRectF, QRect, QSize, QPointF
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen

class TitleLabel(QLabel):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.setMinimumHeight(150)
        self.flag_image = QPixmap("image/korea.png")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 배경 그라데이션 (둥근 모서리와 남색 계열)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(65, 105, 225))  # 로열 블루
        gradient.setColorAt(1, QColor(25, 25, 112))  # 미드나이트 블루

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 15, 15)
        painter.fillPath(path, gradient)

        # 타이틀 설정
        title_font = QFont("Arial", 48, QFont.Bold)
        title_path = QPainterPath()
        title_path.addText(QPointF(20, 70), title_font, self.title)

        # 서브타이틀 설정
        subtitle_font = QFont("Arial", 18)
        subtitle_path = QPainterPath()
        subtitle_path.addText(QPointF(25, 110), subtitle_font, self.subtitle)

        # 그림자 효과
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.translate(3, 3)
        painter.drawPath(title_path)
        painter.drawPath(subtitle_path)
        painter.translate(-3, -3)

        # 타이틀 그라데이션
        title_gradient = QLinearGradient(0, 0, self.width(), 0)
        title_gradient.setColorAt(0, QColor(255, 215, 0))
        title_gradient.setColorAt(1, QColor(255, 140, 0))

        # 타이틀 테두리
        painter.strokePath(title_path, QPen(QColor(100, 100, 100), 2))
        painter.fillPath(title_path, title_gradient)

        # 서브타이틀
        painter.setPen(QColor(220, 220, 220))  # 밝은 회색으로 변경
        painter.setFont(subtitle_font)
        painter.drawPath(subtitle_path)

        # 장식 효과
        painter.setPen(QPen(QColor(200, 200, 255), 2))
        painter.drawLine(20, 120, self.width() - 20, 120)

        # 한국 국기 이미지 추가 (비율 유지)
        flag_height = 70  # 원하는 국기 높이
        flag_width = int(flag_height * (self.flag_image.width() / self.flag_image.height()))
        flag_x = self.width() - flag_width - 10  # 우측 여백 10픽셀
        flag_y = 10  # 상단 여백 10픽셀
        scaled_flag = self.flag_image.scaled(flag_width, flag_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(flag_x, flag_y, scaled_flag)

class LoginWindow(QDialog, QObject):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.setWindowTitle("CAL/DAL Management System")
        self.setFixedSize(600, 800)
        self.setWindowIcon(QIcon("image/logo.png"))
        # 로그인 창의 배경색 설정
        self.setStyleSheet("background-color: #F0F0F0;")
        self.init_database()  # 데이터베이스 초기화 메서드 호출
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""

            QDialog {
                background-image: url(image/login_background.png);
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-size: cover;
                border: none;
            }
            QLabel {
                font: 강한공군체;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QLineEdit {
                font: 강한공군체;
                font-size: 20px;
                padding: 10px;
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                font: 강한공군체;
                font-size: 22px;
                font-weight: bold;
                padding: 10px;
                background-color: #007BFF;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            #form_container {
                background: rgba(50, 50, 50, 0.8);
                border: 1px solid gray;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.5);
            }
        """)

        # 배경을 위한 QLabel 추가
        background_label = QLabel(self)
        background_label.setGeometry(0, 0, 600, 800)
        background_label.setStyleSheet("""
                    background-image: url(image/login_background.png);
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: cover;
                """)
        background_label.lower()  # 배경을 다른 위젯 뒤로 보냄



        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # 제목 추가
        title_label = TitleLabel("CDMS", "CAL/DAL Management System")

        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_container.setObjectName("form_container")

        self.username_label = QLabel(self.tr("아이디:"))
        self.username_input = QLineEdit()
        form_layout.addRow(self.username_label, self.username_input)

        self.password_label = QLabel(self.tr("비밀번호:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(self.password_label, self.password_input)

        main_layout.addWidget(form_container)

        self.login_button = QPushButton(self.tr("로 그 인"))
        self.login_button.clicked.connect(self.login)
        main_layout.addWidget(self.login_button)

        main_layout.setContentsMargins(100, 50, 100, 50)
        self.setLayout(main_layout)

    def show_message(self, title, message, icon):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setFont(QFont("강한공군체", 15, QFont.Bold))
        # 스타일시트 적용
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
            }
            QLabel {
                color: black;
                font-weight: bold;
                text-shadow: 2px 2px 2px black;
            }
        """)
        # 아이콘 크기 조절
        icon_label = msg_box.findChild(QLabel, "qt_msgboxex_icon_label")
        if icon_label:
            icon_pixmap = icon_label.pixmap()
            if icon_pixmap:
                scaled_pixmap = icon_pixmap.scaled(23, 23, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)

        msg_box.exec_()

    def init_database(self):
        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                db_name TEXT
            )
        ''')
        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]
        if count == 0:
            id_list = ['navy', 'army', 'airforce']
            cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", ('admin', 'admin', 'assets_management.db'))
            for id in id_list:
                cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (id, id, f'assets_{id}.db'))
            conn.commit()
        conn.close()

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            self.show_message(self.tr("로그인 성공"), self.tr("로그인에 성공했습니다."), QMessageBox.Information)
            self.username = username
            self.db_name = user[2]  # 데이터베이스 파일명 저장
            self.accept()
        else:
            self.show_message(self.tr("로그인 실패"), self.tr("아이디 또는 비밀번호가 잘못되었습니다."), QMessageBox.Critical)
            # 로그인 실패 시 입력 필드 초기화
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setFocus()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    if window.exec_() == QDialog.Accepted:
        print(f"로그인 성공: {window.username}")
        print(f"사용할 데이터베이스: {window.db_name}")
    sys.exit(app.exec_())
