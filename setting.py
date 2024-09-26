import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget, QDialog, QHBoxLayout, QCheckBox, QPushButton, QLineEdit, QComboBox
import os
import configparser
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QGridLayout, QMessageBox, QGroupBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QIcon



class SettingWindow(QDialog):
    settingsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("지도 설정"))
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
                border-radius: 10px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.initUI()
        self.loadSettings()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 초기 위치 설정
        location_group = QGroupBox(self.tr("초기 위치"))
        location_layout = QHBoxLayout()
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        location_layout.addWidget(QLabel(self.tr("위도:")))
        location_layout.addWidget(self.lat_input)
        location_layout.addWidget(QLabel(self.tr("경도:")))
        location_layout.addWidget(self.lon_input)
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)

        # 줌 레벨 설정
        zoom_group = QGroupBox(self.tr("줌 레벨"))
        zoom_layout = QHBoxLayout()
        self.zoom_input = QLineEdit()
        zoom_layout.addWidget(QLabel(self.tr("줌:")))
        zoom_layout.addWidget(self.zoom_input)
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)

        # 지도 스타일 설정
        style_group = QGroupBox(self.tr("지도 스타일"))
        style_layout = QHBoxLayout()
        self.style_combo = QComboBox()
        self.style_combo.addItems(
            ["OpenStreetMap", "Cartodb Positron", "CartoDB Voyager"])
        style_layout.addWidget(QLabel(self.tr("스타일:")))
        style_layout.addWidget(self.style_combo)
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # 저장 및 취소 버튼
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.tr("저장"))
        save_button.clicked.connect(self.saveSettings)
        save_button.setIcon(QIcon("image/save.png"))
        cancel_button = QPushButton(self.tr("취소"))
        cancel_button.clicked.connect(self.reject)
        cancel_button.setIcon(QIcon("image/cancel.png"))
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    # loadSettings 및 saveSettings 메서드는 이전과 동일하게 유지

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
        try:
            latitude = float(self.lat_input.text())
            longitude = float(self.lon_input.text())
            zoom = int(self.zoom_input.text())

            if not (-90 <= latitude <= 90):
                raise ValueError("위도는 -90에서 90 사이의 값이어야 합니다.")
            if not (-180 <= longitude <= 180):
                raise ValueError("경도는 -180에서 180 사이의 값이어야 합니다.")
            if not (0 <= zoom <= 18):
                raise ValueError("줌 레벨은 0에서 18 사이의 정수여야 합니다.")

            new_settings = {
                'latitude': str(latitude),
                'longitude': str(longitude),
                'zoom': str(zoom),
                'style': self.style_combo.currentText()
            }

            config = configparser.ConfigParser()
            config['Map'] = new_settings
            with open('map_settings.ini', 'w') as configfile:
                config.write(configfile)
            self.settingsChanged.emit(new_settings)
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "입력 오류", str(e))
            self.loadSettings()  # 초기값으로 리셋
        except Exception as e:
            QMessageBox.warning(self, "오류", f"설정을 저장하는 중 오류가 발생했습니다: {str(e)}")
            self.loadSettings()  # 초기값으로 리셋

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

        self.settings = self.loadSettings()
        self.updateMap()

        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('맵 애플리케이션')

    def openSettings(self):
        self.setting_window = SettingWindow(self)
        self.setting_window.settingsChanged.connect(self.updateSettings)
        self.setting_window.exec_()

    def updateSettings(self, new_settings):
        self.settings['latitude'] = float(new_settings['latitude'])
        self.settings['longitude'] = float(new_settings['longitude'])
        self.settings['zoom'] = int(new_settings['zoom'])
        self.settings['style'] = new_settings['style']
        self.updateMap()

    def loadSettings(self):
        config = configparser.ConfigParser()
        if os.path.exists('map_settings.ini'):
            config.read('map_settings.ini')
            return {
                'latitude': config.getfloat('Map', 'latitude', fallback=37.5665),
                'longitude': config.getfloat('Map', 'longitude', fallback=126.9780),
                'zoom': config.getint('Map', 'zoom', fallback=7),
                'style': config.get('Map', 'style', fallback='OpenStreetMap'),
            }
        else:
            return {
                'latitude': 37.5665,
                'longitude': 126.9780,
                'zoom': 7,
                'style': 'OpenStreetMap',
            }

    def saveSettings(self):
        config = configparser.ConfigParser()
        config['Map'] = self.settings
        with open('map_settings.ini', 'w') as configfile:
            config.write(configfile)

    def updateMap(self):
        style_dict = {
            "OpenStreetMap": {"tiles": "OpenStreetMap", "attr": "© OpenStreetMap contributors"},
            "Cartodb Positron": {"tiles": "cartodbpositron", "attr": "© OpenStreetMap contributors © CARTO"},
            "CartoDB Voyager": {"tiles": "cartodbvoyager", "attr": "© OpenStreetMap contributors © CARTO"},
        }


        tile = style_dict.get(self.settings['style'], style_dict["OpenStreetMap"])

        m = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=tile["tiles"],
            attr=tile.get("attr", "© OpenStreetMap contributors")
        )

        # 지도 데이터를 HTML로 변환
        data = m.get_root().render()
        self.web_view.setHtml(data)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapApp()
    ex.show()
    sys.exit(app.exec_())
