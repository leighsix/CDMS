import sys, logging
import folium
from PyQt5.QtCore import Qt, QCoreApplication, QTranslator, QObject, QDir
from branca.colormap import LinearColormap


class CalMapView(QObject):
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

        composition_group = self.tr('구성군')
        assets_name = self.tr('자산명')
        coordinates = self.tr('좌표')
        engagement_effects = self.tr('교전효과 수준')
        bmd_priorities = self.tr('BMD 우선순위')

        # 구성군별 색상 정의
        unit_colors = {
            self.tr('지상군'): 'red',
            self.tr('해군'): 'blue',
            self.tr('공군'): 'skyblue',
            self.tr('기타'): 'black'
        }

        # BMD 우선순위별 모양 정의 (고정된 매핑)
        bmd_shapes = {
            self.tr('지휘통제시설'): 1,  # 원
            self.tr('비행단'): 2,  # 삼각형
            self.tr('군수기지'): 3,  # 사각형
            self.tr('해군기지'): 4,  # 다이아몬드
            self.tr('주요레이다'): 5,  # 오각형
            self.tr('None'): 6  # 육각형
        }



        # 구성군 범례 생성
        legend_html = f'''
        <div style="position: fixed; bottom: 20px; right: 20px; width: 150px; 
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

        # BMD 우선순위 범례 생성
        bmd_legend_html = f'''
        <div style="position: fixed; bottom: 20px; left: 20px; width: 150px; 
                    border:2px solid grey; z-index:9999; font-size:14px; background-color:white;">
            <div style="position: relative; top: 3px; left: 3px;">
            <strong>{bmd_priorities}</strong><br>
        '''
        for priority, shape in bmd_shapes.items():
            bmd_legend_html += f'''
            <div style="display: flex; align-items: center; margin: 3px;">
                <div style="width: 15px; height: 15px; margin-right: 5px; display: flex; justify-content: center; align-items: center;">
                    {self.get_shape_html(shape, 'black')}
                </div>
                <span>{priority}</span>
            </div>
            '''
        bmd_legend_html += '</div></div>'

        for unit, asset_name, area, coordinate, engagement_effectiveness, bmd_priority in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coordinate)

                # 구성군에 따른 색상 선택
                color = unit_colors.get(unit, 'black')

                # BMD 우선순위에 따른 모양 선택
                shape = bmd_shapes[bmd_priority]

                # 커스텀 아이콘 생성
                icon = folium.DivIcon(html=self.get_shape_html(shape, color))

                # 마커 생성
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{composition_group}:</b> {unit}<br>
                        <b>{assets_name}:</b> {asset_name}<br>
                        <b>{coordinates}:</b> {coordinate}<br>
                        <b>{engagement_effects}:</b> {engagement_effectiveness}<br>
                        <b>{bmd_priorities}:</b> {bmd_priority}<br>
                    """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                logging.error(self.tr(f"좌표 변환 오류 {coordinate}: {e}"))
                continue

        map_obj.get_root().html.add_child(folium.Element(legend_html))
        map_obj.get_root().html.add_child(folium.Element(bmd_legend_html))

    # 모양별 HTML 생성 함수
    @staticmethod
    def get_shape_html(shape_num, color):
        shapes = {
            1: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 5 L61 35 L98 35 L68 57 L79 91 L50 70 L21 91 L32 57 L2 35 L39 35 Z" fill="{color}"/>
                <circle cx="50" cy="50" r="10" fill="white"/>
            </svg>''',
            2:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 10 L10 90 H90 Z" fill="{color}"/>
                <path d="M50 30 L30 70 H70 Z" fill="white"/>
            </svg>''',
            3:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M20 0 H80 L100 20 V80 L80 100 H20 L0 80 V20 Z" fill="{color}"/>
                <rect x="30" y="30" width="40" height="40" fill="white"/>
            </svg>''',
            4:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 0 L100 50 L50 100 L0 50 Z" fill="{color}"/>
                <circle cx="50" cy="50" r="20" fill="white"/>
            </svg>''',
            5: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="50" fill="{color}"/>
                <path d="M50 20 L80 80 H20 Z" fill="white"/>
                <circle cx="50" cy="50" r="10" fill="{color}"/>
            </svg>''',
            6: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="{color}"/>
            </svg>'''
            }
        return shapes[shape_num].format(color)

class PriorityCalMapView(QObject):
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

        priorities = self.tr('우선순위')
        composition_group = self.tr('구성군')
        assets_name = self.tr('자산명')
        coordinates = self.tr('좌표')
        engagement_effects = self.tr('교전효과 수준')
        bmd_priorities = self.tr('BMD 우선순위')

        # 우선순위 정렬 및 색상 계산
        coordinates_list.sort(key=lambda x: x[0])  # 우선순위로 정렬
        max_priority = max(item[0] for item in coordinates_list)
        min_priority = min(item[0] for item in coordinates_list)

        # 그라데이션 색상맵 생성
        colormap = LinearColormap(colors=['red', 'yellow', 'green'], vmin=int(min_priority), vmax=int(max_priority))
        colormap.caption = priorities
        colormap.add_to(map_obj)

        # BMD 우선순위별 모양 정의 (고정된 매핑)
        bmd_shapes = {
            self.tr('지휘통제시설'): 1,  # 원
            self.tr('비행단'): 2,  # 삼각형
            self.tr('군수기지'): 3,  # 사각형
            self.tr('해군기지'): 4,  # 다이아몬드
            self.tr('주요레이다'): 5,  # 오각형
            self.tr('None'): 6  # 육각형
        }

        for priority, unit, asset_name, area, coordinate, engagement_effectiveness, bmd_priority in coordinates_list:
            try:
                lat, lon = self.parse_coordinates(coordinate)

                # 우선순위에 따른 색상 선택
                color = colormap(int(priority))

                # BMD 우선순위에 따른 모양 선택
                shape = bmd_shapes[bmd_priority]

                # 커스텀 아이콘 생성
                icon = folium.DivIcon(html=self.get_shape_html(shape, color))

                # 마커 생성
                folium.Marker(
                    location=[lat, lon],
                    icon=icon,
                    popup=folium.Popup(f"""
                        <b>{priorities}:</b> {priority}<br>
                        <b>{composition_group}:</b> {unit}<br>
                        <b>{assets_name}:</b> {asset_name}<br>
                        <b>{coordinates}:</b> {coordinate}<br>
                        <b>{engagement_effects}:</b> {engagement_effectiveness}<br>
                        <b>{bmd_priorities}:</b> {bmd_priority}<br>
                    """, max_width=200)
                ).add_to(map_obj)

            except Exception as e:
                logging.error(self.tr(f"좌표 변환 오류 {coordinate}: {e}"))
                continue

        # BMD 우선순위 범례 생성
        bmd_legend_html = f'''
        <div style="position: fixed; bottom: 20px; left: 20px; width: 150px; 
                    border:2px solid grey; z-index:9999; font-size:14px; background-color:white;">
            <div style="position: relative; top: 3px; left: 3px;">
            <strong>{bmd_priorities}</strong><br>
        '''
        for priority, shape in bmd_shapes.items():
            bmd_legend_html += f'''
            <div style="display: flex; align-items: center; margin: 3px;">
                <div style="width: 15px; height: 15px; margin-right: 5px; display: flex; justify-content: center; align-items: center;">
                    {self.get_shape_html(shape, 'black')}
                </div>
                <span>{priority}</span>
            </div>
            '''
        bmd_legend_html += '</div></div>'

        map_obj.get_root().html.add_child(folium.Element(bmd_legend_html))

    # 모양별 HTML 생성 함수
    @staticmethod
    def get_shape_html(shape_num, color):
        shapes = {
            1: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 5 L61 35 L98 35 L68 57 L79 91 L50 70 L21 91 L32 57 L2 35 L39 35 Z" fill="{color}"/>
                <circle cx="50" cy="50" r="10" fill="white"/>
            </svg>''',
            2:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 10 L10 90 H90 Z" fill="{color}"/>
                <path d="M50 30 L30 70 H70 Z" fill="white"/>
            </svg>''',
            3:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M20 0 H80 L100 20 V80 L80 100 H20 L0 80 V20 Z" fill="{color}"/>
                <rect x="30" y="30" width="40" height="40" fill="white"/>
            </svg>''',
            4:f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <path d="M50 0 L100 50 L50 100 L0 50 Z" fill="{color}"/>
                <circle cx="50" cy="50" r="20" fill="white"/>
            </svg>''',
            5: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="50" fill="{color}"/>
                <path d="M50 20 L80 80 H20 Z" fill="white"/>
                <circle cx="50" cy="50" r="10" fill="{color}"/>
            </svg>''',
            6: f'''<svg width="20" height="20" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="{color}"/>
            </svg>'''
            }
        return shapes[shape_num].format(color)



