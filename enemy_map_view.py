import folium
from PyQt5.QtCore import QObject, QCoreApplication
import sys, logging, io
import mgrs
import re, json

class EnemyBaseMapView(QObject):
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
        enemy_bases = self.tr("적 미사일 기지")
        weapon_systems = self.tr("적 보유 미사일")

        # 색상 정의
        color_map = {
            'Scud-B': 'red',
            'Scud-C': 'blue',
            'Nodong': 'green',
            '다종 미사일': 'purple'
        }

        for base_name, mgrs_coord, weapon_system in coordinates_list:
            weapon_systems_list = weapon_system.split(", ")
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 무기 시스템에 따른 색상 결정
                if len(weapon_systems_list) > 1:
                    color = color_map['다종 미사일']
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
                                    <b>MGRS:</b> {mgrs_coord}<br>
                                    <b>{weapon_systems}:</b> {weapon_system}
                                """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                print(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                continue

        # 범례 추가 (삼각형 아이콘으로 변경)
        legend_html = f"""
            <div id="maplegend" style="
                position: fixed; 
                bottom: 50px; 
                right: 50px; 
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
                    <span style="color:purple;">&#9650;</span> 다종 미사일
                </div>
            </div>
        """

        # 범례를 지도에 추가
        map_obj.get_root().html.add_child(folium.Element(legend_html))

class EnemyWeaponMapView(QObject):
    def __init__(self, coordinates_list, show_threat_radius, map_obj):
        super().__init__()
        self.show_threat_radius = show_threat_radius
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
        for base_name, mgrs_coord, weapon_system in coordinates_list:
            try:
                zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                mgrs_full_str = f'{zone}{square}{easting}{northing}'
                lat, lon = m_conv.toLatLon(mgrs_full_str)

                # 무기체계에 따른 색상 및 반경 선택
                info = weapon_info.get(weapon_system, {"color": "#000000", "max_radius": 0})
                color = info["color"]
                max_radius = info["max_radius"]
                    # 방어 반경 그리기
                if self.show_threat_radius:
                    self.draw_threat_radius(map_obj, lat, lon, color, max_radius)

            except Exception as e:
                logging.error(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                continue

    def draw_threat_radius(self, map_obj, lat, lon, color, max_radius):
        folium.Circle(
            location=[lat, lon],
            radius=max_radius*1000,
            color=color,
            weight=1,
            fill=True,
            fillColor=color,
            fillOpacity=0.2
        ).add_to(map_obj)

class EnemyBaseWeaponMapView(QObject):
    def __init__(self, coordinates_list, show_threat_radius, map_obj):
        super().__init__()
        self.show_threat_radius = show_threat_radius
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
        enemy_bases = self.tr("적 미사일 기지")
        weapon_systems = self.tr("적 보유 미사일")

        # 색상 정의
        color_map = {
            'Scud-B': 'red',
            'Scud-C': 'blue',
            'Nodong': 'green',
            '다종 미사일': 'purple'
        }
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


        for base_name, mgrs_coord, weapon_system in coordinates_list:
            weapon_systems_list = weapon_system.split(", ")
            for weapon in weapon_systems_list:
                try:
                    zone, square, easting, northing = self.parse_mgrs(mgrs_coord)
                    mgrs_full_str = f'{zone}{square}{easting}{northing}'
                    lat, lon = m_conv.toLatLon(mgrs_full_str)

                    # 무기체계에 따른 색상 및 반경 선택
                    info = weapon_info.get(weapon, {"color": "#000000", "max_radius": 0})
                    m_color = info["color"]
                    radius = info["max_radius"]

                    # 무기 시스템에 따른 색상 결정
                    if len(weapon_systems_list) > 1:
                        color = color_map['다종 미사일']
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
                                            <b>MGRS:</b> {mgrs_coord}<br>
                                            <b>{weapon_systems}:</b> {weapon}
                                        """, max_width=200)
                    ).add_to(map_obj)

                    # 방어 반경 그리기
                    if self.show_threat_radius:
                        self.draw_threat_radius(map_obj, lat, lon, m_color, radius)

                except Exception as e:
                    logging.error(self.tr(f"MGRS 좌표 변환 오류 {mgrs_coord}: {e}"))
                    continue

                # 범례 추가 (삼각형 아이콘으로 변경)
            legend_html = f"""
                    <div id="maplegend" style="
                        position: fixed; 
                        bottom: 50px; 
                        right: 50px; 
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
                            <span style="color:purple;">&#9650;</span> 다종 미사일
                        </div>
                    </div>
                """


        # 범례를 지도에 추가
        map_obj.get_root().html.add_child(folium.Element(legend_html))

    def draw_threat_radius(self, map_obj, lat, lon, m_color, max_radius):
        folium.Circle(
            location=[lat, lon],
            radius=max_radius*1000,
            color=m_color,
            weight=1,
            fill=True,
            fillColor=m_color,
            fillOpacity=0.2
        ).add_to(map_obj)




