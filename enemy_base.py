from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject, QPointF
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen, QPainterPath, QPixmap, QFontMetrics
from PyQt5.QtCore import Qt, QSize, QParallelAnimationGroup
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *


class EnemyBaseWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("적 미사일 발사기지 입력"))
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        # 적 미사일 발사기지 정보 입력 위젯 추가
        # ...
        self.setLayout(layout)