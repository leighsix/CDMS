import sys
import io
import os
import re
import math
import mgrs
import folium
import logging
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog


class DefenseAssetMapView(QMainWindow):
    def __init__(self, coordinates_list, selected_language):
        super().__init__()
        self.setWindowTitle(self.tr("DAL 지도 보기"))
        self.setWindowIcon(QIcon("image/logo.png"))
        self.setMinimumSize(1200, 900)
        self.setStyleSheet("background-color: #ffffff; font-family: '강한 공군체'; font-size: 12pt;")

        self.selected_language = selected_language
        self.coordinates_list = coordinates_list
        self.show_defense_radius = False

        self.create_map()
        self.initUI()

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        self.load_map(coordinates_list)

    def create_map(self):
        if self.selected_language == "Korean":
            self.map = folium.Map(location=[37.5665, 126.9780], zoom_start=7)
        else:
            self.map = folium.Map(location=[25.2048, 55.2708], zoom_start=7)

    def initUI(self):
        toolbar = self.addToolBar("Controls")

        self.checkbox = QCheckBox(self.tr("방어반경 표시"))
        self.checkbox.stateChanged.connect(self.toggle_defense_radius)
        toolbar.addWidget(self.checkbox)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        self.print_button = QPushButton(self.tr("지도 출력"))
        self.print_button.setFont(QFont("강한공군체", 14, QFont.Bold))
        self.print_button.clicked.connect(self.print_map)
        toolbar.addWidget(self.print_button)

    def toggle_defense_radius(self, state):
        self.show_defense_radius = state == Qt.Checked
        self.load_map(self.coordinates_list)

    def parse_mgrs(self, mgrs_string):
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list):
        self.create_map()
        if not coordinates_list:
            QMessageBox.warning(self, self.tr("경고"), self.tr("선택된 자산이 없습니다."))
            return

        m_conv = mgrs.MGRS()

        # 무기체계별 색상 및 반경 정의
        weapon_info = {
            "KM-SAM2": {"color": "#FF0000", "radius": 50000},
            "PAC-2": {"color": "#0000FF", "radius": 70000},
            "PAC-3": {"color": "#FFFF00", "radius": 20000},
            "MSE": {"color": "#FF00FF", "radius": 45000},
            "L-SAM": {"color": "#00FFFF", "radius": 180000},
            "THAAD": {"color": "#FFA500", "radius": 200000}
        }

        # 범례 생성
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{self.tr("무기체계")}</strong><br>
        """
        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon}<br>'
        legend_html += "</div>"
        self.map.get_root().html.add_child(folium.Element(legend_html))

        for asset_name, mgrs_coord, weapon_system, threat_degree in self.coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                info = weapon_info.get(weapon_system, {"color": "#000000", "radius": 0})
                color = info["color"]
                radius = info["radius"]

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
                        <b>{self.tr("방어자산")}:</b> {asset_name}<br>
                        <b>MGRS:</b> {mgrs_coord}<br>
                        <b>{self.tr("무기체계")}:</b> {weapon_system}
                    """, max_width=200)
                ).add_to(self.map)

                # 방어 반경 그리기
                if self.show_defense_radius:
                    self.draw_defense_radius(lat, lon, weapon_system, threat_degree, color, radius)

            except Exception as e:
                logging.error(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}")
                continue
        data = io.BytesIO()
        self.map.save(data, close_file=False)
        html = data.getvalue().decode()

        # QWebEngineView에 HTML 로드
        self.view.setHtml(html, QUrl("file://"))

    def draw_defense_radius(self, lat, lon, weapon_system, threat_degree, color, radius):
        if weapon_system == "KM-SAM2":
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
            # 위협방위를 기준으로 시작 각도와 끝 각도 계산
            start_angle = (threat_degree - 60 + 360) % 360
            end_angle = (threat_degree + 60 + 360) % 360
            self.draw_sector(lat, lon, radius, threat_degree, start_angle, end_angle, color)

    def draw_sector(self, lat, lon, radius, threat_degree, start_angle, end_angle, color):
        points = [(lat, lon)]  # 중심점 추가

        # 시계 방향으로 각도 계산
        if start_angle > end_angle:
            angles = list(range(start_angle, 360)) + list(range(0, end_angle + 1))
        else:
            angles = list(range(start_angle, end_angle + 1))

        for angle in angles:
            # 각도를 라디안으로 변환 (지도에서 진북이 000도)
            rad = math.radians(90 - angle)
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
        self.preview.setMinimumSize(1000, 800)  # 미리보기 창 크기 증가
        self.preview.paintRequested.connect(self.handle_print_requested)
        self.preview.finished.connect(self.print_finished)
        self.preview.exec_()

    def handle_print_requested(self, printer):
        try:
            painter = QPainter()
            painter.begin(printer)

            # 프린터 페이지의 크기 가져오기
            page_rect = printer.pageRect(QPrinter.DevicePixel)

            # 제목 추가
            title_font = QFont("Arial", 16, QFont.Bold)
            painter.setFont(title_font)
            title_rect = painter.boundingRect(page_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")
            painter.drawText(title_rect, Qt.AlignTop | Qt.AlignHCenter, "Common Operational Picture")

            # 웹 뷰의 전체 내용 캡처
            full_map = self.view.grab()

            # 범례 캡처 시도
            legend_widget = self.findChild(QWidget, "legendWidget")
            if legend_widget:
                legend = legend_widget.grab()
                # 지도와 범례를 합친 이미지 생성
                combined_image = QImage(full_map.width(), full_map.height() + legend.height(), QImage.Format_ARGB32)
                combined_image.fill(Qt.white)

                painter_combined = QPainter(combined_image)
                painter_combined.drawPixmap(0, 0, full_map)
                painter_combined.drawPixmap(0, full_map.height(), legend)
                painter_combined.end()
            else:
                # 범례가 없는 경우 지도만 사용
                combined_image = full_map.toImage()

            # 이미지를 페이지에 맞게 스케일링
            content_rect = page_rect.adjusted(0, title_rect.height() + 10, 0, -30)
            scaled_image = combined_image.scaled(QSize(int(content_rect.width()), int(content_rect.height())),
                                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # 이미지를 페이지 중앙에 그리기
            x = content_rect.left() + (content_rect.width() - scaled_image.width()) / 2
            y = content_rect.top() + (content_rect.height() - scaled_image.height()) / 2
            painter.drawImage(x, y, scaled_image)

            # 인쇄 정보 추가
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
            QMessageBox.information(self, "인쇄 완료", "지도가 성공적으로 출력되었습니다.")
        else:
            QMessageBox.warning(self, "인쇄 실패", "지도 출력 중 오류가 발생했습니다.")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    coordinates_list_example = [
        ('NamSan Tower', '52SDH8572719195', 'PAC-3', 0),
        ('Jamsil Station', '52SDH8391122760', 'KM-SAM2', 0),
        ('Gyeongbokgung', '52SDH8248121549', 'THAAD', 0),
        ('Incheon Airport', '52SDC7996709959', 'L-SAM', 0),
        ('Suwon Hwaseong', '52SDG8551498892', 'MSE', 0)
    ]

    map_loader = DefenseAssetMapView(coordinates_list_example, "Korean")
    map_loader.show()

    sys.exit(app.exec_())
