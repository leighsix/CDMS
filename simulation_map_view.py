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

class SimulationCalMapView(QObject):
    def __init__(self, coordinates_list, map_obj):
        super().__init__()
        self.load_map(coordinates_list, map_obj)

    @staticmethod
    def parse_coordinates(coord_string):
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])
        lon = float(lon_str[1:])
        return lat, lon

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return

        coordinates_list.sort(key=lambda x: x[-1])
        max_priority = max(item[-1] for item in coordinates_list)
        min_priority = min(item[-1] for item in coordinates_list)

        colormap = LinearColormap(colors=['red', 'yellow', 'green'], vmin=min_priority, vmax=max_priority)
        colormap.caption = self.tr("우선순위")
        colormap.add_to(map_obj)

        colormap._width = 300
        colormap._height = 20
        colormap._font_size = '14px'
        colormap._ticklabels = [str(i) for i in range(min_priority, max_priority + 1)]

        defended_assets = self.tr("방어자산")
        critical_assets = self.tr("중요자산")
        assets_classification = self.tr("자산구분")
        legend_html = f"""
        <div style="position: fixed; bottom: 200px; right: 20px; width: auto; height: auto; background-color: white; 
            border: 2px solid grey; z-index:9999; font-size:14px">
            <strong>{assets_classification}</strong><br>
            <p><span style="color: black;">&#9733;</span> {defended_assets}</p>
            <p><span style="color: black;">&#9679;</span> {critical_assets}</p>
        </div>
        """

        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for asset_name, coordinate, dal_select, priority in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coordinate)
                color = colormap(priority)
                critical_assets = self.tr("자산")
                priorities = self.tr("우선순위")
                coordinates = self.tr("좌표")

                if dal_select == 1:
                    icon_shape = '&#9733;'  # 별표 유니코드
                else:
                    icon_shape = '&#9679;'  # 동그라미 유니코드

                icon = folium.DivIcon(html=f"""
                    <div style="
                        font-size: 24px;
                        color: {color};
                        text-shadow: 0 0 3px #ffffff;
                    ">
                        {icon_shape}
                    </div>
                """)

                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{critical_assets}:</b> {asset_name}<br>
                        <b>{coordinates}:</b> {coordinate}<br>
                        <b>{priorities}:</b> {priority}
                    """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                print(self.tr(f"좌표 변환 오류 {coordinate}: {e}"))
                continue

class SimulationWeaponMapView(QObject):
    def __init__(self, coordinates_list, map_obj, show_defense_radius):
        super().__init__()
        self.show_defense_radius = show_defense_radius
        self.load_map(coordinates_list, map_obj)

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
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
        coordinates = self.tr('좌표')
        # 범례 생성
        # "무기체계"를 .ts 파일에서 번역될 수 있도록 수정
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 20px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        """

        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon}<br>'
        legend_html += "</div>"
        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for unit, area, asset_name, coord, weapon_system, ammo_count, threat_degree, dal_select in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coord)

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
                                    <b>{coordinates}:</b> {coord}<br>
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

class SimulationEnemyBaseMapView(QObject):
    def __init__(self, coordinates_list, map_obj):
        super().__init__()
        self.load_map(coordinates_list, map_obj)

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
        m_conv = mgrs.MGRS()
        enemy_bases = self.tr("적 미사일 기지")
        weapon_systems = self.tr("적 보유 미사일")
        coordinates = self.tr("좌표")


        # 색상 정의
        color_map = {
            'Scud-B': 'red',
            'Scud-C': 'blue',
            'Nodong': 'green',
            'Various Types': 'purple'
        }

        for base_name, coord, weapon_system in coordinates_list:
            weapon_systems_list = weapon_system.split(", ")
            try:
                lat, lon = self.parse_coordinates(coord)
                # 무기 시스템에 따른 색상 결정
                if len(weapon_systems_list) > 1:
                    color = color_map['Various Types']
                else:
                    color = color_map.get(weapon_systems_list[0], 'gray')  # 알 수 없는 타입은 회색으로 표시

                # 마커 아이콘을 삼각형으로 변경
                icon = folium.DivIcon(html=f"""
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 7px solid transparent;
                        border-right: 7px solid transparent;
                        border-bottom: 15px solid {color};
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        color: white;
                        font-weight: bold;
                        font-size: 8px;
                    ">
                    </div>
                """)

                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                                    <b>{enemy_bases}:</b> {base_name}<br>
                                    <b>{coordinates}:</b> {coord}<br>
                                    <b>{weapon_systems}:</b> {weapon_system}
                                """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                print(self.tr(f"좌표 변환 오류 {coord}: {e}"))
                continue

        # 범례 추가 (삼각형 아이콘으로 변경)
        legend_html = f"""
            <div id="maplegend" style="
                position: fixed; 
                bottom: 50px; 
                right: 20px; 
                width: 150px; 
                height: auto; 
                background-color: white; 
                border: 2px solid grey; 
                z-index: 9999; 
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);
            ">
                <b>{weapon_systems}</b><br>
                <div style="margin-top: 5px;">
                    <span style="color:red;">&#9650;</span> Scud-B<br>
                    <span style="color:blue;">&#9650;</span> Scud-C<br>
                    <span style="color:green;">&#9650;</span> Nodong<br>
                    <span style="color:purple;">&#9650;</span> Various Types
                </div>
            </div>
        """

        # 범례를 지도에 추가
        map_obj.get_root().html.add_child(folium.Element(legend_html))

class SimulationEnemyWeaponMapView(QObject):
    def __init__(self, coordinates_list, map_obj, show_threat_radius):
        super().__init__()
        self.show_threat_radius = show_threat_radius
        self.load_map(coordinates_list, map_obj)

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
        # 무기체계별 색상 및 반경 정의
        # JSON 파일에서 데이터 로드
        with open('missile_info.json', 'r', encoding='utf-8') as file:
            missile_data = json.load(file)

        # 색상 정보 (JSON에 없으므로 별도로 정의)
        colors = {
            "Scud-B": "#FFB3B3",
            "Scud-C": "#B3B3FF",
            "Nodong": "#C5F5C5"
        }

        # weapon_info 딕셔너리 생성
        weapon_info = {}
        for missile, info in missile_data.items():
            weapon_info[missile] = {
                "color": colors[missile],
                "max_radius": int(info["max_radius"]),
                "function": info["function"]
            }
        for base_name, coord, weapon_system in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coord)

                # 무기체계에 따른 색상 및 반경 선택
                info = weapon_info.get(weapon_system, {"color": "#000000", "max_radius": 0})
                color = info["color"]
                max_radius = info["max_radius"]
                    # 방어 반경 그리기
                if self.show_threat_radius:
                    self.draw_threat_radius(map_obj, lat, lon, color, max_radius)

            except Exception as e:
                logging.error(self.tr(f"좌표 변환 오류 {coord}: {e}"))
                continue

    @staticmethod
    def draw_threat_radius(map_obj, lat, lon, color, max_radius):
        folium.Circle(
            location=[lat, lon],
            radius=max_radius*1000,
            color=color,
            weight=1,
            fill=True,
            fillColor=color,
            fillOpacity=0.2
        ).add_to(map_obj)
