import sys, logging
import folium
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QApplication
import io, json
import mgrs
import re
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QCheckBox, QPushButton
import math
from PyQt5.QtGui import QPagedPaintDevice, QPainter, QImage, QPageSize, QPageLayout
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtCore import QUrl, QTemporaryFile, QSize, QTimer, QMarginsF
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
import os
from branca.colormap import LinearColormap
import configparser
import os

class CalAssetMapView(QDialog):
    def __init__(self, coordinates_list, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle(self.tr("CAL 지도 보기"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style'])
        self.initUI()
        self.load_map(coordinates_list)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

    def initUI(self):
        layout = QVBoxLayout(self)
        self.map_view = QWebEngineView(self)
        layout.addWidget(self.map_view)

        # 버튼을 포함할 컨테이너 위젯 생성
        button_container = QWidget(self)
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 10, 0)  # 오른쪽 상단 여백 조정

        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.setFixedSize(230, 50)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        layout.addWidget(self.print_button)

        self.setLayout(layout)

    def parse_mgrs(self, mgrs_string):
        """MGRS 문자열을 파싱하고 유효성을 검사하는 메서드"""
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list):
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style'])
        if not coordinates_list:
            # 기본 한국 지도 표시
            data = io.BytesIO()
            self.map.save(data, close_file=False)
            self.map_view.setHtml(data.getvalue().decode())
            return
        composition_group = self.tr('구성군')
        assets_name = self.tr('자산명')
        m_conv = mgrs.MGRS()

        # 구성군별 색상 정의
        unit_colors = {
            self.tr('지상군'): 'red',
            self.tr('해군'): 'blue',
            self.tr('공군'): 'skyblue',
            self.tr('기타'): 'black'
        }

        # 범례 생성
        legend_html = f'''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 150px; height: 120px; 
                    border:2px solid grey; z-index:9999; font-size:14px; background-color:white;">
            <div style="position: relative; top: 3px; left: 3px;">
            <strong>{composition_group}</strong><br>
        '''
        for unit, color in unit_colors.items():
            legend_html += f'''
            <div style="display: flex; align-items: center; margin: 3px;">
                <div style="background-color: {color}; width: 15px; height: 15px; margin-right: 5px;"></div>
                <span>{unit}</span>
            </div>
            '''
        legend_html += '</div></div>'

        for unit, asset_name, coordinate, mgrs_coord in coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 구성군에 따른 색상 선택
                color = unit_colors.get(unit, 'black')  # 일치하는 구성군이 없으면 검정색 사용

                # 커스텀 아이콘 생성
                icon = folium.DivIcon(html=f"""
                    <div style="
                        width: 18px;
                        height: 18px;
                        border-radius: 50%;
                        background-color: {color};
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                        border: 1px solid white;
                        box-shadow: 0 0 3px rgba(0,0,0,0.3);
                    ">
                    </div>
                """)

                # 마커 생성
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{composition_group}:</b> {unit}<br>
                        <b>{assets_name}:</b> {asset_name}<br>
                        <b>MGRS:</b> {mgrs_coord}<br>
                    """, max_width=200)
                ).add_to(self.map)

            except Exception as e:
                print(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                continue

        # 범례 추가
        self.map.get_root().html.add_child(folium.Element(legend_html))

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        self.map_view.setHtml(data.getvalue().decode())

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))

            full_map = self.map_view.grab()

            content_rect = page_rect.adjusted(0, title_rect.height() + 10, 0, -30)
            scaled_image = full_map.scaled(QSize(int(content_rect.width()), int(content_rect.height())),
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)

            x = int(content_rect.left() + (content_rect.width() - scaled_image.width()) / 2)
            y = int(content_rect.top() + (content_rect.height() - scaled_image.height()) / 2)
            painter.drawImage(x, y, scaled_image.toImage())  # QPixmap을 QImage로 변환

            info_font = QFont("Arial", 8)
            painter.setFont(info_font)
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            info_text = f"인쇄 일시: {current_time}"
            painter.drawText(page_rect.adjusted(10, -20, -10, -10), Qt.AlignBottom | Qt.AlignRight, info_text)

            painter.end()
        except Exception as e:
            print(f"인쇄 중 오류 발생: {str(e)}")
            self.print_success = False
        else:
            self.print_success = True

    def print_finished(self, result):
        if self.print_success:
            QMessageBox.information(self, self.tr("인쇄 완료"), self.tr("지도가 성공적으로 출력되었습니다."))
        else:
            QMessageBox.warning(self, self.tr("인쇄 실패"), self.tr("지도 출력 중 오류가 발생했습니다."))

class PriorityMapView(QDialog):
    def __init__(self, coordinates_list, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("CAL 우선순위 지도 보기")
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style']
        )
        self.initUI()
        self.load_map(coordinates_list)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

    def initUI(self):
        layout = QVBoxLayout(self)
        self.map_view = QWebEngineView(self)
        layout.addWidget(self.map_view)

        # 버튼을 포함할 컨테이너 위젯 생성
        button_container = QWidget(self)
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 10, 0)  # 오른쪽 상단 여백 조정

        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.setFixedSize(230, 50)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        layout.addWidget(self.print_button)

        self.setLayout(layout)

    def parse_mgrs(self, mgrs_string):
        """MGRS 문자열을 파싱하고 유효성을 검사하는 메서드"""
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list):
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style'])
        if not coordinates_list:
            # 기본 한국 지도 표시
            data = io.BytesIO()
            self.map.save(data, close_file=False)
            self.map_view.setHtml(data.getvalue().decode())
            return

        m_conv = mgrs.MGRS()

        # 우선순위 정렬 및 색상 계산
        coordinates_list.sort(key=lambda x: x[-1])  # 우선순위로 정렬
        max_priority = max(item[-1] for item in coordinates_list)
        min_priority = min(item[-1] for item in coordinates_list)

        # 그라데이션 색상맵 생성
        colormap = LinearColormap(colors=['red', 'yellow', 'green'], vmin=min_priority, vmax=max_priority)
        colormap.caption = self.tr('우선순위')
        colormap.add_to(self.map)

        # 범례 크기 조정 및 정수 표현
        colormap._width = 300
        colormap._height = 20
        colormap._font_size = '14px'
        colormap._ticklabels = [str(i) for i in range(min_priority, max_priority + 1)]

        for unit, asset_name, coordinate, mgrs_coord, priority in coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 색상 계산
                color = colormap(priority)
                critical_assets = self.tr("자산")
                priorities = self.tr("우선순위")

                # 커스텀 아이콘 생성
                icon = folium.DivIcon(html=f"""
                    <div style="
                        width: 18px;
                        height: 18px;
                        border-radius: 50%;
                        background-color: {color};
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                        border: 1px solid white;
                        box-shadow: 0 0 3px rgba(0,0,0,0.3);
                    ">
                        {priority}
                    </div>
                """)

                # 마커 생성
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{critical_assets}:</b> {asset_name}<br>
                        <b>MGRS:</b> {mgrs_coord}<br>
                        <b>{priorities}:</b> {priority}
                    """, max_width=200)
                ).add_to(self.map)

            except Exception as e:
                print(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                continue

        data = io.BytesIO()
        self.map.save(data, close_file=False)
        self.map_view.setHtml(data.getvalue().decode())

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("CAL 지도 보기"))

            full_map = self.map_view.grab()

            content_rect = page_rect.adjusted(0, title_rect.height() + 10, 0, -30)
            scaled_image = full_map.scaled(QSize(int(content_rect.width()), int(content_rect.height())),
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)

            x = int(content_rect.left() + (content_rect.width() - scaled_image.width()) / 2)
            y = int(content_rect.top() + (content_rect.height() - scaled_image.height()) / 2)
            painter.drawImage(x, y, scaled_image.toImage())  # QPixmap을 QImage로 변환

            info_font = QFont("Arial", 8)
            painter.setFont(info_font)
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            info_text = f"인쇄 일시: {current_time}"
            painter.drawText(page_rect.adjusted(10, -20, -10, -10), Qt.AlignBottom | Qt.AlignRight, info_text)

            painter.end()
        except Exception as e:
            print(f"인쇄 중 오류 발생: {str(e)}")
            self.print_success = False
        else:
            self.print_success = True

    def print_finished(self, result):
        if self.print_success:
            QMessageBox.information(self, self.tr("인쇄 완료"), self.tr("지도가 성공적으로 출력되었습니다."))
        else:
            QMessageBox.warning(self, self.tr("인쇄 실패"), self.tr("지도 출력 중 오류가 발생했습니다."))

class DefenseAssetMapView(QDialog):
    def __init__(self, coordinates_list, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle(self.tr("DAL 지도 보기"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style'])
        self.coordinates_list = coordinates_list
        self.show_defense_radius = False
        self.initUI()
        self.load_map(coordinates_list)
        self.view = QWebEngineView()
        # 창 크기 조절 허용
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)


    def initUI(self):
        layout = QVBoxLayout()
        self.map_view = QWebEngineView(self)
        layout.addWidget(self.map_view)

        self.checkbox = QCheckBox(self.tr("방어반경 표시"), self)
        self.checkbox.stateChanged.connect(self.toggle_defense_radius)
        layout.addWidget(self.checkbox)

        self.print_button = QPushButton(self.tr("지도 출력"), self)
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.setFixedSize(230, 50)
        self.print_button.setStyleSheet("QPushButton { text-align: center; }")
        self.print_button.clicked.connect(self.print_map)
        layout.addWidget(self.print_button)

        self.setLayout(layout)

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.load_map(self.coordinates_list)

    def parse_mgrs(self, mgrs_string):
        """MGRS 문자열을 파싱하고 유효성을 검사하는 메서드"""
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list):
        self.map = folium.Map(
            location=[self.settings['latitude'], self.settings['longitude']],
            zoom_start=self.settings['zoom'],
            tiles=self.settings['style'])
        if not coordinates_list:
            QMessageBox.warning(self, self.tr("경고"), self.tr("선택된 자산이 없습니다."))
            return

        m_conv = mgrs.MGRS()
        defense_assets = self.tr("방어자산")
        weapon_systems = self.tr("무기체계")
        # 무기체계별 색상 및 반경 정의
        # JSON 파일에서 무기 정보 불러오기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_info = json.load(file)
        # 색상 정보 추가 (JSON 파일에 없으므로 기존 색상 정보 유지)
        color_info = {
            "KM-SAM2": "#FF0000",
            "PAC-2": "#0000FF",
            "PAC-3": "#FFFF00",
            "MSE": "#FF00FF",
            "L-SAM": "#00FFFF",
            "THAAD": "#FFA500"
        }

        # 무기 정보에 색상 추가
        for weapon, data in weapon_info.items():
            data['color'] = color_info.get(weapon, "#000000")  # 기본 색상은 검정색
            data['radius'] = int(data['radius'])  # 반경을 정수로 변환
            data['angle'] = int(data['angle'])

        # 범례 생성
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        """
        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon}<br>'
        legend_html += "</div>"
        self.map.get_root().html.add_child(folium.Element(legend_html))

        for asset_name, coordinate, mgrs_coord, weapon_system, threat_degree in self.coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 무기체계에 따른 색상 및 반경 선택
                info = weapon_info.get(weapon_system, {"color": "#000000", "radius": 0, "angle": 0})
                color = info["color"]
                radius = info["radius"]
                angle = info["angle"]

                # 커스텀 아이콘 생성
                icon = folium.DivIcon(html=f"""
                                    <div style="
                                        width: 15px;
                                        height: 15px;
                                        border-radius: 0%;
                                        background-color: {color};
                                        display: flex;
                                        justify-content: center;
                                        align-items: center;
                                        color: white;
                                        font-weight: bold;
                                        font-size: 8px;
                                        border: 0.5px solid white;
                                        box-shadow: 0 0 2px rgba(0,0,0,0.2);
                                    ">
                                    </div>
                                """)

                # 마커 생성
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{defense_assets}:</b> {asset_name}<br>
                        <b>MGRS:</b> {mgrs_coord}<br>
                        <b>{weapon_systems}:</b> {weapon_system}
                    """, max_width=200)
                ).add_to(self.map)

                # 방어 반경 그리기
                if self.show_defense_radius:
                    self.draw_defense_radius(lat, lon, threat_degree, color, radius, angle)

            except Exception as e:
                logging.error(self.tr(f"오류발생: {e}"))
                continue
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)

    def draw_defense_radius(self, lat, lon, threat_degree, color, radius, angle):
        if angle == 360:
            folium.Circle(
                location=[lat, lon],
                radius=radius,
                color=color,
                weight=1,
                fill=True,
                fillColor=color,
                fillOpacity=0.2
            ).add_to(self.map)

        else:
            start_angle = (threat_degree - (angle / 2) + 360) % 360
            end_angle = (threat_degree + (angle / 2) + 360) % 360
            self.draw_sector(lat, lon, radius, start_angle, end_angle, color)

    def draw_sector(self, lat, lon, radius, start_angle, end_angle, color):
        points = [(lat, lon)]  # 중심점 추가

        # 시계 방향으로 각도 계산
        if start_angle > end_angle:
            angles = [i for i in range(int(start_angle), 360)] + [i for i in range(0, int(end_angle) + 1)]
        else:
            angles = [i for i in range(int(start_angle), int(end_angle) + 1)]
        for ang in angles:
            rad = math.radians(90 - ang)
            x = lon + (radius / 111000) * math.cos(rad) / math.cos(math.radians(lat))
            y = lat + (radius / 111000) * math.sin(rad)
            points.append((y, x))

        points.append((lat, lon))  # 중심점 다시 추가하여 폐곡선 만들기

        folium.Polygon(
            locations=points,
            color=color,
            fill=True,
            weight=1,
            fillColor=color,
            fillOpacity=0.2
        ).add_to(self.map)

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
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("DAL 지도 보기"))
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, self.tr("DAL 지도 보기"))

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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    settings = {
                'latitude': 37.5665,
                'longitude': 126.9780,
                'zoom': 7,
                'style': 'OpenStreetMap',
                'color_mode': '기본',
                'night_mode': False
            }
    # 서울 주변 예시 사용 (weapon_system과 threat_degree 추가)
    coordinates_list_example = [('해군', '원자력 발전소', 'N38.12345,E128.45321', '52S DH 52073 19653', 1),
                                ('지상군', 'asdf', 'N39.11233,E127.12345', '52S CJ 37757 30918', 2)]

    map_loader = PriorityMapView(coordinates_list_example, settings)
    map_loader.show()

    sys.exit(app.exec_())