import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget, QDialog, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PyQt5.QtCore import QObject, QPointF, Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon, QLinearGradient, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtWidgets, QtGui
import folium
import io
import mgrs
import re
from branca.colormap import LinearColormap
import math
import os
import configparser
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
from PyQt5.QtCore import pyqtSignal


class SettingWindow(QDialog):
    settingsChanged = pyqtSignal(dict)  # 시그널 추가
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("지도 설정"))
        self.initUI()
        self.loadSettings()

    def initUI(self):
        layout = QVBoxLayout()

        # 초기 위치 설정
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel(self.tr("초기 위치:")))
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        location_layout.addWidget(self.lat_input)
        location_layout.addWidget(self.lon_input)
        layout.addLayout(location_layout)

        # 줌 레벨 설정
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel(self.tr("줌 레벨:")))
        self.zoom_input = QLineEdit()
        zoom_layout.addWidget(self.zoom_input)
        layout.addLayout(zoom_layout)

        # 지도 스타일 설정
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel(self.tr("지도 스타일:")))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["OpenStreetMap", "Stamen Terrain", "Stamen Toner", "Cartodb Positron"])
        style_layout.addWidget(self.style_combo)
        layout.addLayout(style_layout)

        # 저장 및 취소 버튼
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.tr("저장"))
        save_button.clicked.connect(self.saveSettings)
        cancel_button = QPushButton(self.tr("취소"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def loadSettings(self):
        config = configparser.ConfigParser()
        if os.path.exists('map_settings.ini'):
            config.read('map_settings.ini')
            self.lat_input.setText(config.get('Map', 'latitude', fallback='37.5665'))
            self.lon_input.setText(config.get('Map', 'longitude', fallback='126.9780'))
            self.zoom_input.setText(config.get('Map', 'zoom', fallback='7'))
            self.style_combo.setCurrentText(config.get('Map', 'style', fallback='OpenStreetMap'))
        else:
            self.lat_input.setText('37.5665')
            self.lon_input.setText('126.9780')
            self.zoom_input.setText('7')

    def saveSettings(self):
        config = configparser.ConfigParser()
        new_settings = {
            'latitude': self.lat_input.text(),
            'longitude': self.lon_input.text(),
            'zoom': self.zoom_input.text(),
            'style': self.style_combo.currentText()
        }
        config['Map'] = new_settings
        with open('map_settings.ini', 'w') as configfile:
            config.write(configfile)
        self.settingsChanged.emit(new_settings)
        self.accept()


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        settings_button = QPushButton("설정")
        settings_button.clicked.connect(self.openSettings)
        layout.addWidget(settings_button)

        self.settings = {
            'latitude': 37.5665,
            'longitude': 126.9780,
            'zoom': 10,
            'style': 'OpenStreetMap'
        }
        self.updateMap()

        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('맵 애플리케이션')

    def openSettings(self):
        self.setting_window = SettingWindow(self)
        self.setting_window.settingsChanged.connect(self.updateSettings)
        self.setting_window.exec_()  # show() 대신 exec_() 사용

    def updateSettings(self, new_settings):
        self.settings['latitude'] = float(new_settings['latitude'])
        self.settings['longitude'] = float(new_settings['longitude'])
        self.settings['zoom'] = int(new_settings['zoom'])
        self.settings['style'] = new_settings['style']
        self.updateMap()

    def updateMap(self):
        style_dict = {
            "OpenStreetMap": "OpenStreetMap",
            "Stamen Terrain": "Stamen Terrain",
            "Stamen Toner": "Stamen Toner",
            "Cartodb Positron": "cartodbpositron"
        }

        tile = style_dict.get(self.settings['style'], "OpenStreetMap")

        m = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=tile
        )

        # 지도 데이터를 HTML로 변환
        data = m.get_root().render()
        self.web_view.setHtml(data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapApp()
    ex.show()
    sys.exit(app.exec_())
