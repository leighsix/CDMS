import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QApplication
from PyQt5.QtGui import QIcon
from branca.colormap import LinearColormap
from PyQt5.QtCore import QObject, QCoreApplication
import sys, logging, io
import mgrs
import re, json
import html
from PyQt5.QtCore import QUrl, QTemporaryFile
from PyQt5.QtGui import QPainter, QPagedPaintDevice
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
import os
import math



class CommonMapView(QObject):
    def __init__(self, coordinates_list, map_obj):
        super().__init__()
        self.load_map(coordinates_list, map_obj)

    def parse_mgrs(self, mgrs_string):
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
        m_conv = mgrs.MGRS()

        coordinates_list.sort(key=lambda x: x[-1])
        max_priority = max(item[-1] for item in coordinates_list)
        min_priority = min(item[-1] for item in coordinates_list)

        colormap = LinearColormap(colors=['red', 'yellow', 'green'], vmin=min_priority, vmax=max_priority)
        # "우선순위"를 .ts 파일에서 번역될 수 있도록 수정
        colormap.caption = self.tr("우선순위")
        colormap.add_to(map_obj)

        colormap._width = 300
        colormap._height = 20
        colormap._font_size = '14px'
        colormap._ticklabels = [str(i) for i in range(min_priority, max_priority + 1)]

        for asset_name, mgrs_coord, priority in coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                color = colormap(priority)
                critical_assets = self.tr("자산")
                priorities = self.tr("우선순위")

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
                    # "자산", "우선순위"를 .ts 파일에서 번역될 수 있도록 수정
                    popup=folium.Popup(f"""
                        <b>{critical_assets}:</b> {asset_name}<br>
                        <b>MGRS:</b> {mgrs_coord}<br>
                        <b>{priorities}:</b> {priority}
                    """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                print(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                continue


class DefenseAssetCommonMapView(QObject):
    def __init__(self, coordinates_list, show_defense_radius, map_obj):
        super().__init__()
        self.show_defense_radius = show_defense_radius
        self.load_map(coordinates_list, map_obj)

    def parse_mgrs(self, mgrs_string):
        mgrs_string = re.sub(r'\s+', '', mgrs_string)
        pattern = r'^(\d{1,2}[A-Z])([A-Z]{2})(\d{5})(\d{5})$'
        match = re.match(pattern, mgrs_string)
        if not match:
            raise ValueError(self.tr(f"잘못된 MGRS 형식: {mgrs_string}"))
        return match.group(1), match.group(2), match.group(3), match.group(4)

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
        m_conv = mgrs.MGRS()
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

        defense_assets = self.tr("방어자산")
        weapon_systems = self.tr("무기체계")
        # 범례 생성
        # "무기체계"를 .ts 파일에서 번역될 수 있도록 수정
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        """

        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon}<br>'
        legend_html += "</div>"
        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for asset_name, mgrs_coord, weapon_system, threat_degree in coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 무기체계에 따른 색상 및 반경 선택
                info = weapon_info.get(weapon_system, {"color": "#000000", "max_radius": 0, "angle": 0})
                color = info["color"]
                max_radius = info["max_radius"]
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

                # "방어자산", "무기체계"를 .ts 파일에서 번역될 수 있도록 수정
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                                    <b>{defense_assets}:</b> {asset_name}<br>
                                    <b>MGRS:</b> {mgrs_coord}<br>
                                    <b>{weapon_systems}:</b> {weapon_system}
                                """, max_width=200)
                ).add_to(map_obj)

                # 방어 반경 그리기
                if self.show_defense_radius:
                    self.draw_defense_radius(map_obj, lat, lon, threat_degree, color, max_radius, angle)

            except Exception as e:
                logging.error(self.tr(f"오류발생: {e}"))
                continue

    def draw_defense_radius(self, map_obj, lat, lon, threat_degree, color, max_radius, angle):
        if angle == 360:
            folium.Circle(
                location=[lat, lon],
                radius=max_radius * 1000,
                color=color,
                weight=1,
                fill=True,
                fillColor=color,
                fillOpacity=0.2
            ).add_to(map_obj)

        else:
            start_angle = (threat_degree - (angle / 2) + 360) % 360
            end_angle = (threat_degree + (angle / 2) + 360) % 360
            self.draw_sector(map_obj, lat, lon, max_radius, start_angle, end_angle, color)

    def draw_sector(self, map_obj, lat, lon, max_radius, start_angle, end_angle, color):
        points = [(lat, lon)]  # 중심점 추가

        # 시계 방향으로 각도 계산
        if start_angle > end_angle:
            angles = [i for i in range(int(start_angle), 360)] + [i for i in range(0, int(end_angle) + 1)]
        else:
            angles = [i for i in range(int(start_angle), int(end_angle) + 1)]
        for ang in angles:
            rad = math.radians(90 - ang)
            x = lon + (max_radius*1000 / 111000) * math.cos(rad) / math.cos(math.radians(lat))
            y = lat + (max_radius*1000 / 111000) * math.sin(rad)
            points.append((y, x))

        points.append((lat, lon))  # 중심점 다시 추가하여 폐곡선 만들기

        folium.Polygon(
            locations=points,
            color=color,
            fill=True,
            weight=1,
            fillColor=color,
            fillOpacity=0.2
        ).add_to(map_obj)



