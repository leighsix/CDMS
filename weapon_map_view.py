import sys, logging
import folium
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QApplication
import io, json
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir
import math, colorsys


def logger_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

class WeaponAssetMapView(QObject):
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

    @staticmethod
    def generate_distinct_colors(n):
        colors = []
        for i in range(n):
            hue = i / n
            saturation = 0.7 + (i % 3) * 0.1  # 0.7-0.9 사이의 채도
            value = 0.8 + (i % 2) * 0.1  # 0.8-0.9 사이의 명도

            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            hex_color = '#%02x%02x%02x' % (
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return

        # JSON 파일에서 무기 정보 불러오기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_info = json.load(file)

        # 무기체계 목록 추출
        weapon_types = list(weapon_info.keys())

        # 무기체계 수에 따라 색상 자동 생성
        colors = self.generate_distinct_colors(len(weapon_types))

        # 무기체계별 색상 매핑
        color_info = dict(zip(weapon_types, colors))

        # 무기 정보에 색상 추가
        for weapon, data in weapon_info.items():
            data['color'] = color_info[weapon]

        units = self.tr("구성군")
        areas = self.tr("지역")
        weapon_assets = self.tr("방어포대명")
        coordinates = self.tr("좌표")
        ammo_counts = self.tr("보유탄수")
        threat_degrees = self.tr("위협방위")
        weapon_systems = self.tr("무기체계")
        # 범례 생성
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        """

        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon}<br>'
        legend_html += "</div></div>"
        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for unit, area, asset_name, coord, weapon_system, ammo_count, threat_degree in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coord)

                # 무기체계에 따른 색상 및 반경 선택
                info = weapon_info.get(weapon_system, {"color": "#000000", "max_radius": 0, "angle": 0})
                color = info["color"]
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
                                    <b>{units}:</b> {unit}<br>
                                    <b>{areas}:</b> {area}<br>
                                    <b>{weapon_assets}:</b> {asset_name}<br>
                                    <b>{coordinates}:</b> {coord}<br>
                                    <b>{weapon_systems}:</b> {weapon_system}<br>
                                    <b>{ammo_counts}:</b> {ammo_count}<br>
                                    <b>{threat_degrees}:</b> {threat_degree}<br>
                                """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                logging.error(self.tr(f"오류발생: {e}"))
                continue

class WeaponMapView(QObject):
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

    @staticmethod
    def generate_distinct_colors(n):
        colors = []
        for i in range(n):
            hue = i / n
            saturation = 0.7 + (i % 3) * 0.1  # 0.7-0.9 사이의 채도
            value = 0.8 + (i % 2) * 0.1  # 0.8-0.9 사이의 명도

            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            hex_color = '#%02x%02x%02x' % (
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors

    def load_map(self, coordinates_list, map_obj):
        if not coordinates_list:
            return
        # JSON 파일에서 무기 정보 불러오기
        with open('weapon_systems.json', 'r', encoding='utf-8') as file:
            weapon_info = json.load(file)

        # 무기체계 목록 추출
        weapon_types = list(weapon_info.keys())

        # 무기체계 수에 따라 색상 자동 생성
        colors = self.generate_distinct_colors(len(weapon_types))

        # 무기체계별 색상 매핑
        color_info = dict(zip(weapon_types, colors))

        # 무기 정보에 색상 추가
        for weapon, data in weapon_info.items():
            data['color'] = color_info[weapon]

        weapon_systems = self.tr("무기체계")
        max_radius = self.tr("최대반경")
        # 범례 생성
        legend_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        """

        for weapon, info in weapon_info.items():
            legend_html += f'<span style="background-color: {info["color"]}; color: {info["color"]}; border: 1px solid black;">__</span> {weapon} ({max_radius}: {info["max_radius"]}km)<br>'
        legend_html += "</div></div>"
        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for unit, area, asset_name, coord, weapon_system, ammo_count, threat_degree in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coord)

                # 무기체계에 따른 정보 가져오기
                info = weapon_info.get(weapon_system, {})
                color = info.get('color', '#000000')
                max_radius = info.get('max_radius', 0)
                angle = info.get('angle', 0)

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
                fillOpacity=0.05
            ).add_to(map_obj)

        else:
            try:
                threat_degree = float(threat_degree)  # 문자열을 실수로 변환
                start_angle = (threat_degree - (angle / 2) + 360) % 360
                end_angle = (threat_degree + (angle / 2) + 360) % 360
                self.draw_sector(map_obj, lat, lon, max_radius, start_angle, end_angle, color)
            except ValueError:
                logging.error(self.tr(f"위협방위 값을 실수로 변환할 수 없습니다: {threat_degree}"))

    @staticmethod
    def draw_sector(map_obj, lat, lon, max_radius, start_angle, end_angle, color):
        points = [(lat, lon)]  # 중심점 추가

        # 시계 방향으로 각도 계산
        if start_angle > end_angle:
            angles = [i for i in range(int(start_angle), 360)] + [i for i in range(0, int(end_angle) + 1)]
        else:
            angles = [i for i in range(int(start_angle), int(end_angle) + 1)]
        for ang in angles:
            rad = math.radians(90 - ang)
            x = lon + (max_radius * 1000 / 111000) * math.cos(rad) / math.cos(math.radians(lat))
            y = lat + (max_radius * 1000 / 111000) * math.sin(rad)
            points.append((y, x))

        points.append((lat, lon))  # 중심점 다시 추가하여 폐곡선 만들기

        folium.Polygon(
            locations=points,
            color=color,
            fill=True,
            weight=1,
            fillColor=color,
            fillOpacity=0.05
        ).add_to(map_obj)
