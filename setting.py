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

        # 최적화 범위 설정 추가
        optimization_group = QGroupBox(self.tr("최적화 범위 설정"))
        optimization_layout = QGridLayout()

        self.lat_min_input = QLineEdit()
        self.lat_max_input = QLineEdit()
        self.lon_min_input = QLineEdit()
        self.lon_max_input = QLineEdit()

        optimization_layout.addWidget(QLabel(self.tr("위도 최소값:")), 0, 0)
        optimization_layout.addWidget(self.lat_min_input, 0, 1)
        optimization_layout.addWidget(QLabel(self.tr("위도 최대값:")), 0, 2)
        optimization_layout.addWidget(self.lat_max_input, 0, 3)
        optimization_layout.addWidget(QLabel(self.tr("경도 최소값:")), 1, 0)
        optimization_layout.addWidget(self.lon_min_input, 1, 1)
        optimization_layout.addWidget(QLabel(self.tr("경도 최대값:")), 1, 2)
        optimization_layout.addWidget(self.lon_max_input, 1, 3)

        optimization_group.setLayout(optimization_layout)
        layout.addWidget(optimization_group)

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
            # 최적화 범위 설정 로드
            self.lat_min_input.setText(config.get('Optimization', 'lat_min', fallback='34.4'))
            self.lat_max_input.setText(config.get('Optimization', 'lat_max', fallback='38.2'))
            self.lon_min_input.setText(config.get('Optimization', 'lon_min', fallback='126.0'))
            self.lon_max_input.setText(config.get('Optimization', 'lon_max', fallback='129.8'))
            self.style_combo.setCurrentText(config.get('Map', 'style', fallback='OpenStreetMap'))
        else:
            self.lat_input.setText('37.5665')
            self.lon_input.setText('126.9780')
            self.zoom_input.setText('7')
            # 최적화 범위 기본값 설정
            self.lat_min_input.setText('34.4')
            self.lat_max_input.setText('38.2')
            self.lon_min_input.setText('126.0')
            self.lon_max_input.setText('129.8')

    def saveSettings(self):
        try:
            latitude = float(self.lat_input.text())
            longitude = float(self.lon_input.text())
            zoom = int(self.zoom_input.text())
            # 최적화 범위 유효성 검사
            lat_min = float(self.lat_min_input.text())
            lat_max = float(self.lat_max_input.text())
            lon_min = float(self.lon_min_input.text())
            lon_max = float(self.lon_max_input.text())

            if not (-90 <= latitude <= 90):
                raise ValueError("위도는 -90에서 90 사이의 값이어야 합니다.")
            if not (-180 <= longitude <= 180):
                raise ValueError("경도는 -180에서 180 사이의 값이어야 합니다.")
            if not (0 <= zoom <= 18):
                raise ValueError("줌 레벨은 0에서 18 사이의 정수여야 합니다.")
            if not (-90 <= lat_min <= lat_max <= 90):
                raise ValueError("위도 범위가 올바르지 않습니다.")
            if not (-180 <= lon_min <= lon_max <= 180):
                raise ValueError("경도 범위가 올바르지 않습니다.")

            new_settings = {
                'latitude': str(latitude),
                'longitude': str(longitude),
                'zoom': str(zoom),
                'style': self.style_combo.currentText(),
                'lat_min': str(lat_min),
                'lat_max': str(lat_max),
                'lon_min': str(lon_min),
                'lon_max': str(lon_max)
            }

            config = configparser.ConfigParser()
            config['Map'] = {k: v for k, v in new_settings.items() if k in ['latitude', 'longitude', 'zoom', 'style']}
            config['Optimization'] = {
                'lat_min': new_settings['lat_min'],
                'lat_max': new_settings['lat_max'],
                'lon_min': new_settings['lon_min'],
                'lon_max': new_settings['lon_max']
            }

            with open('map_settings.ini', 'w') as configfile:
                config.write(configfile)
            self.settingsChanged.emit(new_settings)
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "입력 오류", str(e))
            self.loadSettings()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"설정을 저장하는 중 오류가 발생했습니다: {str(e)}")
            self.loadSettings()

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
        self.settings.update({
            'latitude': float(new_settings['latitude']),
            'longitude': float(new_settings['longitude']),
            'zoom': int(new_settings['zoom']),
            'style': new_settings['style'],
            'lat_min': float(new_settings['lat_min']),
            'lat_max': float(new_settings['lat_max']),
            'lon_min': float(new_settings['lon_min']),
            'lon_max': float(new_settings['lon_max'])
        })
        self.updateMap()

    @staticmethod
    def loadSettings():
        config = configparser.ConfigParser()
        if os.path.exists('map_settings.ini'):
            config.read('map_settings.ini')
            return {
                'latitude': config.getfloat('Map', 'latitude', fallback=37.5665),
                'longitude': config.getfloat('Map', 'longitude', fallback=126.9780),
                'zoom': config.getint('Map', 'zoom', fallback=7),
                'style': config.get('Map', 'style', fallback='OpenStreetMap'),
                'lat_min': config.getfloat('Optimization', 'lat_min', fallback=34.4),
                'lat_max': config.getfloat('Optimization', 'lat_max', fallback=38.2),
                'lon_min': config.getfloat('Optimization', 'lon_min', fallback=126.0),
                'lon_max': config.getfloat('Optimization', 'lon_max', fallback=129.8)
            }
        else:
            return {
                'latitude': 37.5665,
                'longitude': 126.9780,
                'zoom': 7,
                'style': 'OpenStreetMap',
                'lat_min': 34.4,
                'lat_max': 38.2,
                'lon_min': 126.0,
                'lon_max': 129.8
            }

    def saveSettings(self):
        config = configparser.ConfigParser()
        config['Map'] = {
            'latitude': str(self.settings['latitude']),
            'longitude': str(self.settings['longitude']),
            'zoom': str(self.settings['zoom']),
            'style': self.settings['style']
        }
        config['Optimization'] = {
            'lat_min': str(self.settings['lat_min']),
            'lat_max': str(self.settings['lat_max']),
            'lon_min': str(self.settings['lon_min']),
            'lon_max': str(self.settings['lon_max'])
        }
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

        # 최적화 범위 표시를 위한 사각형 추가
        folium.Rectangle(
            bounds=[[self.settings['lat_min'], self.settings['lon_min']],
                   [self.settings['lat_max'], self.settings['lon_max']]],
            color='blue',
            fill=True,
            fillOpacity=0.2
        ).add_to(m)

        data = m.get_root().render()
        self.web_view.setHtml(data)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapApp()
    ex.show()
    sys.exit(app.exec_())
