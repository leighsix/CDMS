import folium
from PyQt5.QtCore import QObject, QCoreApplication
import sys, logging, io
import mgrs
import re, json

class EnemyBaseMapView(QObject):
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

class EnemyWeaponMapView(QObject):
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





