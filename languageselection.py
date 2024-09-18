import sys
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


class LanguageSelectionWindow(QDialog, QObject):
    def __init__(self, parent=None):
        super(LanguageSelectionWindow, self).__init__(parent)
        self.setWindowTitle("CAL/DAL Management System")
        self.setFixedSize(600, 800)
        self.setWindowIcon(QIcon("image/logo.png"))
        self.language = None
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QDialog {
                background-image: url(image/language_selection.png);
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-size: cover;
                border: none;
            }
            QLabel {
            font: 강한공군체;
            color: white;
            font-size: 24px;
            font-weight: bold;
            }
            QPushButton {
            font: 바른공군체;
            font-size: 22px;
            font-weight: bold;
            padding: 10px;
            background-color: #007BFF;
            color: white;
            border: none;
            margin: 10px;
            text-align: left;
            icon-size: 60px 60px;
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


        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # 제목 추가
        title_label = TitleLabel("CDMS", "CAL/DAL Management System")


        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_container.setObjectName("form_container")

        self.language_label = QLabel(self.tr("언어를 선택하세요:"))
        form_layout.addWidget(self.language_label)

        self.korean_button = QPushButton(self.tr("     한 국 어"))
        self.english_button = QPushButton(self.tr("     English"))

        # 국기 아이콘 추가
        self.korean_button.setIcon(QIcon("image/korea.png"))
        self.english_button.setIcon(QIcon("image/america.png"))

        # 버튼 크기 정책 설정
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        size_policy.setHeightForWidth(True)

        for button in [self.korean_button, self.english_button]:
            button.setSizePolicy(size_policy)
            button.setMinimumHeight(70)  # 버튼 높이 조정
            button.setMaximumWidth(450)
            button.setIconSize(QSize(70, 70))  # 아이콘 크기 조정
            button.setStyleSheet(button.styleSheet())

        self.korean_button.clicked.connect(lambda: self.select_language("ko"))
        self.english_button.clicked.connect(lambda: self.select_language("en"))

        form_layout.addWidget(self.korean_button)
        form_layout.addWidget(self.english_button)

        main_layout.addWidget(form_container)

        main_layout.setContentsMargins(50, 30, 50, 30)  # 여백 조정
        self.setLayout(main_layout)

    def select_language(self, lang):
        self.language = lang
        self.accept()

class Translator:
    """Helper class to load and install QTranslator"""

    translation_files = {
        "ko": "translations/app_ko.qm",
        "en": "translations/app_en.qm",
    }

    def __init__(self, app):
        self.app = app
        self.translator = QTranslator()

    def load(self, language_code):
        """Load the translation file for the given language code."""
        translation_file = self.translation_files.get(language_code)
        if (translation_file and self.translator.load(translation_file)):
            self.app.installTranslator(self.translator)
            return True
        else:
            QMessageBox.warning(None, "Warning", f"Translation for {language_code} not found.")
            return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LanguageSelectionWindow()
    window.show()
    sys.exit(app.exec_())
