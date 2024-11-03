import sys
import sqlite3
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTranslator, QLocale, QLibraryInfo, QObject, QPoint, QRectF, QRect, QSize, QPointF
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
import bcrypt
import time
import os
import hashlib



def escape_filter_chars(input_string):
    try:
        from ldap3.utils.conv import escape_filter_chars
        return escape_filter_chars(input_string)
    except ImportError:
        filtered_string = input_string.replace("'", "''")
        filtered_string = filtered_string.replace(";", "")
        filtered_string = filtered_string.replace("--", "")
        filtered_string = filtered_string.replace("/*", "")
        filtered_string = filtered_string.replace("*/", "")
        return filtered_string

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.hex(), salt.hex()

def verify_password(password, hashed_password, salt):
    return bcrypt.checkpw(password.encode('utf-8'), bytes.fromhex(hashed_password))

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
            QPushButton#login_button {
                font: 강한공군체;
                font-size: 22px;
                font-weight: bold;
                padding: 10px;
                background-color: #007BFF;
                color: white;
                border: none;
            }
            QPushButton#register_button {
                font: 강한공군체;
                font-size: 22px;
                font-weight: bold;
                padding: 10px;
                background-color: #808080;
                color: white;
                border: none;
            }
            QPushButton#login_button:hover {
                background-color: #0056b3;
            }
            QPushButton#register_button:hover {
                background-color: #666666;
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
        self.login_button.setObjectName("login_button")
        self.login_button.clicked.connect(self.login)
        main_layout.addWidget(self.login_button)

        # 로그인 버튼 아래에 사용자 등록 버튼 추가
        button_layout = QHBoxLayout()

        self.find_cred_button = QPushButton(self.tr("아이디/비밀번호 찾기"))
        self.find_cred_button.setObjectName("register_button")
        self.find_cred_button.clicked.connect(self.show_find_credentials_dialog)
        button_layout.addWidget(self.find_cred_button)

        self.register_button = QPushButton(self.tr("사용자 등록"))
        self.register_button.setObjectName("register_button")
        self.register_button.clicked.connect(self.show_register_dialog)
        button_layout.addWidget(self.register_button)

        main_layout.addLayout(button_layout)

        main_layout.setContentsMargins(100, 50, 100, 50)
        self.setLayout(main_layout)

    @staticmethod
    def show_message(title, message, icon):
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

    @staticmethod
    def init_database():
        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    salt TEXT, 
                    db_name TEXT,
                    military_type TEXT,
                    military_number TEXT,
                    name TEXT,
                    failed_login_attempts INTEGER DEFAULT 0,
                    last_failed_login REAL DEFAULT 0
                )
            ''')

            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            count = cursor.fetchone()[0]

            if count == 0:
                id_list = ['navy', 'army', 'airforce']
                for id in ['admin'] + id_list:
                    hashed_password, salt = hash_password(id)
                    db_name = 'assets_management.db' if id == 'admin' else f'assets_{id}.db'
                    cursor.execute("""
                        INSERT INTO users (
                            username, password, salt, db_name, 
                            military_type, military_number, name,
                            failed_login_attempts, last_failed_login
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (id, hashed_password, salt, db_name,
                          id if id != 'admin' else None,
                          f"{id}001" if id != 'admin' else None,
                          id.title() if id != 'admin' else 'Administrator',
                          0, 0))
                conn.commit()

        except sqlite3.Error as e:
            print(f"데이터베이스 오류: {e}")
            conn.rollback()
        finally:
            conn.close()

    def show_find_credentials_dialog(self):
        dialog = FindCredentialsDialog(self)
        dialog.exec_()

    def show_register_dialog(self):
        dialog = RegisterDialog(self)
        dialog.exec_()

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        conn = sqlite3.connect('user_credentials.db')
        cursor = conn.cursor()
        try:
            username = escape_filter_chars(username)
            cursor.execute(
                "SELECT password, salt, db_name, failed_login_attempts, last_failed_login FROM users WHERE username = ?",
                (username,))
            result = cursor.fetchone()
            if result:
                stored_password, salt, self.db_name, failed_attempts, last_failed = result
                if failed_attempts >= 5 and time.time() - last_failed < 600:
                    raise ValueError(self.tr("로그인 시도 횟수 초과. 10분 후 다시 시도하세요."))
                if verify_password(password, stored_password, salt):
                    cursor.execute(
                        "UPDATE users SET failed_login_attempts = 0, last_failed_login = 0 WHERE username = ?",
                        (username,))
                    conn.commit()
                    self.show_message(self.tr("로그인 성공"), self.tr("로그인에 성공했습니다."), QMessageBox.Information)
                    self.username = username
                    self.accept()
                else:
                    cursor.execute(
                        "UPDATE users SET failed_login_attempts = failed_login_attempts + 1, last_failed_login = ? WHERE username = ?",
                        (time.time(), username,))
                    conn.commit()
                    raise ValueError(self.tr("비밀번호가 일치하지 않습니다."))
            else:
                raise ValueError(self.tr("존재하지 않는 사용자입니다."))
        except (sqlite3.Error, ValueError) as e:
            print(f"LOGIN Error: {e}")
            self.show_message(self.tr("로그인 실패"), self.tr(str(e)), QMessageBox.Critical)
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setFocus()
        finally:
            conn.close()


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle(self.tr("사용자 등록"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setFixedSize(500, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                font: 강한공군체;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                min-width: 100px;
            }
            QLineEdit, QComboBox {
                font: 강한공군체;
                padding: 8px;
                border: 2px solid #404040;
                border-radius: 5px;
                font-size: 18px;
                min-height: 30px;
                min-width: 300px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #007BFF;
            }
            QPushButton {
                font: 강한공군체;
                background-color: #007BFF;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        self.initUI()

    def initUI(self):
        # 클래스 멤버 변수로 선언
        self.military_combo = None
        self.mil_num_input = None
        self.name_input = None
        self.id_input = None
        self.pw_input = None
        self.pw_confirm_input = None

        layout = QVBoxLayout()
        layout.setSpacing(40)
        layout.setContentsMargins(20, 20, 20, 20)

        field_layouts = [
            (self.tr("군 구분:"), self.create_combo_box([self.tr("육군"), self.tr("해군"), self.tr("공군")])),
            (self.tr("군  번:"), QLineEdit()),
            (self.tr("이  름:"), QLineEdit()),
            (self.tr("아이디:"), QLineEdit()),
            (self.tr("비밀번호:"), self.create_password_field()),
            (self.tr("비밀번호 확인:"), self.create_password_field())
        ]

        # 각 필드를 클래스 멤버 변수에 할당
        for label_text, field in field_layouts:
            field_layout = QHBoxLayout()
            label = QLabel(label_text)
            field_layout.addWidget(label)
            field_layout.addWidget(field, alignment=Qt.AlignRight)
            field_layout.setSpacing(10)
            field_layout.addStretch()
            layout.addLayout(field_layout)

            # 각 필드를 해당하는 클래스 멤버 변수에 할당
            if label_text == self.tr("군 구분:"):
                self.military_combo = field
            elif label_text == self.tr("군  번:"):
                self.mil_num_input = field
            elif label_text == self.tr("이  름:"):
                self.name_input = field
            elif label_text == self.tr("아이디:"):
                self.id_input = field
            elif label_text == self.tr("비밀번호:"):
                self.pw_input = field
            else:
                self.pw_confirm_input = field

        # 비밀번호 입력 필드에 이벤트 연결
        self.pw_input.editingFinished.connect(self.validate_password_input)
        self.pw_confirm_input.editingFinished.connect(self.check_password_match)

        register_btn = QPushButton(self.tr("등 록"))
        register_btn.clicked.connect(self.register_user)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(register_btn)
        btn_layout.addStretch()

        layout.addSpacing(20)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setLayout(layout)

    @staticmethod
    def create_combo_box(items):
        combo = QComboBox()
        combo.addItems(items)
        return combo

    @staticmethod
    def create_password_field():
        field = QLineEdit()
        field.setEchoMode(QLineEdit.Password)
        return field

    def register_user(self):
        try:
            print("회원가입 프로세스 시작")

            military_type_map = {
                self.tr("육군"): "army",
                self.tr("해군"): "navy",
                self.tr("공군"): "airforce"
            }

            military_type = military_type_map.get(self.military_combo.currentText())
            military_number = self.mil_num_input.text().strip()
            name = self.name_input.text().strip()
            username = self.id_input.text().strip()
            password = self.pw_input.text()
            confirm_password = self.pw_confirm_input.text()

            # 입력 검증
            if not all([military_type, military_number, name, username, password, confirm_password]):
                self.show_message(self.tr("입력 오류"), self.tr("모든 필드를 입력해주세요."), QMessageBox.Warning)
                return False

            if password != confirm_password:
                self.show_message(self.tr("비밀번호 오류"), self.tr("비밀번호가 일치하지 않습니다."), QMessageBox.Warning)
                return False

            if not self.validate_password(password):
                self.show_message(self.tr("비밀번호 오류"),
                                  self.tr("비밀번호는 다음 조건을 만족해야 합니다:\n"
                                          "- 최소 8자 이상\n"
                                          "- 영문 소문자 포함\n"
                                          "- 숫자 포함\n"
                                          "- 특수문자 포함"), QMessageBox.Warning)
                return False

            conn = None
            try:
                conn = sqlite3.connect('user_credentials.db')
                cursor = conn.cursor()

                # 중복 군, 군번 검사
                cursor.execute("SELECT username FROM users WHERE military_type = ? AND military_number = ?",
                               (military_type, military_number))
                if cursor.fetchone():
                    self.show_message(self.tr("등록 오류"), self.tr("해당 군, 군번은 이미 등록되어 있습니다."), QMessageBox.Warning)
                    return False

                # 중복 아이디 검사
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    self.show_message(self.tr("등록 오류"), self.tr("이미 존재하는 아이디입니다."), QMessageBox.Warning)
                    return False

                # 비밀번호 해싱 및 데이터베이스 저장
                hashed_password, salt = hash_password(password)
                db_name = f'assets_{username}.db'

                cursor.execute("""
                    INSERT INTO users (username, password, salt, db_name, military_type, 
                    military_number, name, failed_login_attempts, last_failed_login) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (username, hashed_password, salt, db_name, military_type,
                      military_number, name))

                conn.commit()

                self.show_message(self.tr("등록 성공"), self.tr("사용자 등록이 완료되었습니다."), QMessageBox.Information)

                self.close()  # accept() 대신 close() 사용
                return True

            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                self.show_message(self.tr("데이터베이스 오류"),
                                  self.tr(f"등록 중 오류가 발생했습니다: {str(e)}"),
                                  QMessageBox.Critical)
                return False
            finally:
                if conn:
                    conn.close()
                    print("데이터베이스 연결 종료")

        except Exception as e:
            self.show_message(self.tr("오류"),
                              self.tr(f"예상치 못한 오류가 발생했습니다: {str(e)}"),
                              QMessageBox.Critical)
            return False

    @staticmethod
    def validate_password(password):
        # 대문자 요구사항 제거, 나머지 조건만 검증
        if len(password) < 8:
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        if not any(not c.isalnum() for c in password):
            return False
        return True

    def validate_password_input(self):
        password = self.pw_input.text()
        if password and not self.validate_password(password):
            self.show_message(self.tr("비밀번호 오류"), self.tr("비밀번호는 다음 조건을 만족해야 합니다:\n"
                                "- 최소 8자 이상\n"
                                "- 영문 소문자 포함\n"
                                "- 숫자 포함\n"
                                "- 특수문자 포함"), QMessageBox.Warning)

            self.pw_input.clear()
            self.pw_input.setFocus()

    def check_password_match(self):
        password = self.pw_input.text()
        confirm_password = self.pw_confirm_input.text()
        if confirm_password and password != confirm_password:
            self.show_message(self.tr("비밀번호 오류"), self.tr("비밀번호가 일치하지 않습니다."), QMessageBox.Warning)
            self.pw_confirm_input.clear()
            self.pw_confirm_input.setFocus()

    @staticmethod
    def show_message(title, message, icon):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setFont(QFont("강한공군체", 12, QFont.Bold))  # 글자 크기 5포인트 감소
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
        icon_label = msg_box.findChild(QLabel, "qt_msgboxex_icon_label")
        if icon_label:
            icon_pixmap = icon_label.pixmap()
            if icon_pixmap:
                scaled_pixmap = icon_pixmap.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)

        msg_box.exec_()


class FindCredentialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle(self.tr("아이디/비밀번호 찾기"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setFixedSize(500, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                font: 강한공군체;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                min-width: 100px;
            }
            QLineEdit, QComboBox {
                font: 강한공군체;
                padding: 8px;
                border: 2px solid #404040;
                border-radius: 5px;
                font-size: 18px;
                min-height: 30px;
                min-width: 300px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #007BFF;
            }
            QPushButton {
                font: 강한공군체;
                background-color: #007BFF;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 입력 필드 생성
        self.military_combo = QComboBox()
        self.military_combo.addItems([self.tr("육군"), self.tr("해군"), self.tr("공군")])
        self.mil_num_input = QLineEdit()
        self.name_input = QLineEdit()

        # 폼 레이아웃에 위젯 추가
        form_layout = QFormLayout()
        form_layout.addRow(self.tr("군 구분:"), self.military_combo)
        form_layout.addRow(self.tr("군번:"), self.mil_num_input)
        form_layout.addRow(self.tr("이름:"), self.name_input)

        layout.addLayout(form_layout)

        # 버튼 추가
        btn_layout = QHBoxLayout()
        find_btn = QPushButton(self.tr("아이디 찾기"))
        find_btn.clicked.connect(self.find_id)
        reset_btn = QPushButton(self.tr("비밀번호 초기화"))
        reset_btn.clicked.connect(self.reset_password)

        btn_layout.addWidget(find_btn)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def find_id(self):
        try:
            military_type_map = {
                self.tr("육군"): "army",
                self.tr("해군"): "navy",
                self.tr("공군"): "airforce"
            }

            military_type = military_type_map.get(self.military_combo.currentText())
            military_number = self.mil_num_input.text().strip()
            name = self.name_input.text().strip()

            conn = sqlite3.connect('user_credentials.db')
            cursor = conn.cursor()

            cursor.execute("""
                SELECT username FROM users 
                WHERE military_type = ? AND military_number = ? AND name = ?
            """, (military_type, military_number, name))

            result = cursor.fetchone()
            found_id = self.tr('찾은 아이디')
            if result:
                self.show_message(self.tr("아이디 찾기"), f"{found_id}: {result[0]}", QMessageBox.Information)
            else:
                self.show_message(self.tr("아이디 찾기"), self.tr("일치하는 사용자가 없습니다."), QMessageBox.Warning)

        except Exception as e:
            self.show_message(self.tr("오류"), self.tr(f"오류가 발생했습니다: {str(e)}"), QMessageBox.Critical)

        finally:
            conn.close()

    def reset_password(self):
        try:
            military_type_map = {
                self.tr("육군"): "army",
                self.tr("해군"): "navy",
                self.tr("공군"): "airforce"
            }

            military_type = military_type_map.get(self.military_combo.currentText())
            military_number = self.mil_num_input.text().strip()
            name = self.name_input.text().strip()

            conn = sqlite3.connect('user_credentials.db')
            cursor = conn.cursor()

            # 사용자 확인
            cursor.execute("""
                SELECT username, password, salt FROM users 
                WHERE military_type = ? AND military_number = ? AND name = ?
            """, (military_type, military_number, name))

            result = cursor.fetchone()
            if result:
                username, stored_password, stored_salt = result
                # 새 비밀번호 해싱
                hashed_password, salt = hash_password(military_number)
                cursor.execute("""
                    UPDATE users 
                    SET password = ?, salt = ? 
                    WHERE username = ?
                """, (hashed_password, salt, username))

                conn.commit()
                self.show_message(self.tr("비밀번호 초기화"), self.tr("비밀번호가 군번으로 초기화되었습니다."), QMessageBox.Information)
            else:
                self.show_message(self.tr("비밀번호 초기화"), self.tr("일치하는 사용자가 없습니다."), QMessageBox.Warning)

        except Exception as e:
            conn.rollback()
            self.show_message(self.tr("오류"), self.tr(f"오류가 발생했습니다: {str(e)}"), QMessageBox.Critical)

        finally:
            conn.close()

    @staticmethod
    def show_message(title, message, icon):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setFont(QFont("강한공군체", 12, QFont.Bold))  # 글자 크기 5포인트 감소
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
        icon_label = msg_box.findChild(QLabel, "qt_msgboxex_icon_label")
        if icon_label:
            icon_pixmap = icon_label.pixmap()
            if icon_pixmap:
                scaled_pixmap = icon_pixmap.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)

        msg_box.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    if window.exec_() == QDialog.Accepted:
        print(f"로그인 성공: {window.username}")
        print(f"사용할 데이터베이스: {window.db_name}")
    sys.exit(app.exec_())