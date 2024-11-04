import folium
from branca.colormap import LinearColormap
from PyQt5.QtCore import QObject, QCoreApplication
import sys, logging, io
import re, json, colorsys
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
            <div style="position: fixed; top: 20px; left: 20px; width: auto; height: auto; background-color: white; 
            border: 2px solid grey; z-index:9999; font-size:14px; padding: 10px; border-radius: 5px;">
            <strong>{assets_classification}</strong><br>
            <div style="margin-top: 5px;">
            <p><span style="color: black;">&#9733; </span> {defended_assets}</p>
            <p><span style="color: black;">&#9679;</span> {critical_assets}</p>
        </div></div>
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

        defense_assets = self.tr("방어자산")
        weapon_systems = self.tr("무기체계")
        max_radius = self.tr("최대반경")
        coordinates = self.tr("좌표")


        # 범례 생성
        legend_html = f"""
        <div style="position: fixed; bottom: 20px; left: 20px; width: auto; height: auto; 
        background-color: white; border: 2px solid grey; z-index:9999; font-size:14px;
        padding: 10px; border-radius: 5px;">
        <strong>{weapon_systems}</strong><br>
        <div style="margin-top: 5px;">
        """

        for weapon, info in weapon_info.items():
            legend_html += (f'<span style="background-color: {info["color"]}; color: {info["color"]}; '
                            f'border: 1px solid black;">__</span> {weapon} ({max_radius}: {info["max_radius"]}km)<br>')
        legend_html += "</div></div>"
        map_obj.get_root().html.add_child(folium.Element(legend_html))

        for unit, area, asset_name, coord, weapon_system, ammo_count, threat_degree, dal_select in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coord)

                # 무기체계에 따른 정보 가져오기
                info = weapon_info.get(weapon_system, {})
                color = info.get('color', '#000000')
                max_radius = info.get('max_radius', 0)
                angle = info.get('angle', 0)

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
                fillOpacity=0.05
            ).add_to(map_obj)

        else:
            start_angle = (threat_degree - (angle / 2) + 360) % 360
            end_angle = (threat_degree + (angle / 2) + 360) % 360
            self.draw_sector(map_obj, lat, lon, max_radius, start_angle, end_angle, color)

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
            fillOpacity=0.05
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
        enemy_bases = self.tr("적 미사일 기지")
        weapon_systems = self.tr("적 보유 미사일")
        coordinates = self.tr("좌표")
        max_radius = self.tr('최대반경')

        # JSON 파일에서 데이터 로드
        with open('missile_info.json', 'r', encoding='utf-8') as file:
            missile_data = json.load(file)

        # 무기체계 특성에 따른 자동 색상 할당
        weapon_types = list(missile_data.keys())
        color_spectrum = [
            '#%02x%02x%02x' % (
                int(255 * (1 - 0.8 * i / len(weapon_types))),  # 빨간색 성분 강화
                int(255 * (0.3 + 0.7 * i / len(weapon_types))),  # 녹색 성분 범위 확대
                int(255 * (0.2 + 0.8 * i / len(weapon_types)))  # 파란색 성분 범위 확대
            ) for i in range(len(weapon_types))
        ]

        # weapon_info 딕셔너리 생성
        weapon_info = {}
        for idx, (missile, info) in enumerate(missile_data.items()):
            weapon_info[missile] = {
                "color": color_spectrum[idx],
                "max_radius": int(info["max_radius"]),
                "function": info["function"]
            }

        # Various Types를 위한 기본 색상 추가
        weapon_info['Various Types'] = {
            "color": "#800080",  # 보라색
            "max_radius": 0,
            "function": ""
        }

        for base_name, coord, weapon_system in coordinates_list:
            weapon_systems_list = weapon_system.split(", ")
            try:
                lat, lon = self.parse_coordinates(coord)
                # 무기 시스템에 따른 색상 결정
                if len(weapon_systems_list) > 1:
                    color = weapon_info['Various Types']['color']
                else:
                    color = weapon_info.get(weapon_systems_list[0], {"color": "#808080"})["color"]

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
                bottom: 20px; 
                right: 20px; 
                width: auto; 
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
        """
        for weapon_type, info in weapon_info.items():
            if weapon_type != 'Various Types':
                legend_html += f'<span style="color:{info["color"]};">&#9650;</span> {weapon_type} ({max_radius}: {info["max_radius"]}km)<br>'
            else:
                legend_html += f'<span style="color:{info["color"]};">&#9650;</span> {weapon_type}<br>'
        legend_html += """
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

        # JSON 파일에서 데이터 로드
        with open('missile_info.json', 'r', encoding='utf-8') as file:
            missile_data = json.load(file)

        # 무기체계 특성에 따른 자동 색상 할당
        weapon_types = list(missile_data.keys())
        color_spectrum = [
            '#%02x%02x%02x' % (
                int(255 * (1 - 0.8 * i / len(weapon_types))),  # 빨간색 성분 강화
                int(255 * (0.3 + 0.7 * i / len(weapon_types))),  # 녹색 성분 범위 확대
                int(255 * (0.2 + 0.8 * i / len(weapon_types)))  # 파란색 성분 범위 확대
            ) for i in range(len(weapon_types))
        ]

        # weapon_info 딕셔너리 생성
        weapon_info = {}
        for idx, (missile, info) in enumerate(missile_data.items()):
            weapon_info[missile] = {
                "color": color_spectrum[idx],
                "max_radius": int(info["max_radius"]),
                "function": info["function"]
            }
        for base_name, coord, weapon_system in coordinates_list:
            weapon_systems_list = weapon_system.split(", ")
            try:
                lat, lon = self.parse_coordinates(coord)

                # 각 무기체계별로 위협반경 그리기
                for weapon in weapon_systems_list:
                    if weapon in weapon_info:
                        info = weapon_info[weapon]
                        if self.show_threat_radius:
                            self.draw_threat_radius(map_obj, lat, lon, info["color"], info["max_radius"])

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
            fillOpacity=0.05
        ).add_to(map_obj)
