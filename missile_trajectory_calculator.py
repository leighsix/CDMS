import math,json
import numpy as np
from geopy import distance
from geopy.point import Point


class MissileTrajectoryCalculator:
    def __init__(self):
        self.EARTH_RADIUS = 6371  # 지구 반지름 (km)
        self.G = 9.81  # 중력 가속도 (m/s^2)

        with open('missile_info.json', 'r', encoding='utf-8') as f:
            self.missile_info = json.load(f)

    def calculate_trajectory(self, missile_base, target, missile_type):
        B_lat, B_lon = missile_base
        T_lat, T_lon = target

        # 1. 거리 계산 (km)
        L = self.calculate_distance(B_lat, B_lon, T_lat, T_lon)

        # 2. 미사일 정보에서 궤적 계수 가져오기
        coeffs = self.missile_info[missile_type]['trajectory_coefficients']
        a1, a2 = coeffs['alpha']['a1'], coeffs['alpha']['a2']
        b1, b2 = coeffs['beta']['b1'], coeffs['beta']['b2']

        # 3. 궤적 계수 alpha, beta 계산
        alpha = a1 * np.exp(a2 * L) + b1 * np.exp(b2 * L)
        beta = a1 * np.exp(a2 * L) + b1 * np.exp(b2 * L)

        # 3. d 값 계산
        d = (-beta + math.sqrt(beta ** 2 + 4 * alpha * L)) / (2 * alpha)

        # 4. 발사 각도 계산
        launch_angle = math.atan((4 * alpha * L) / (beta ** 2))

        # 5. 궤적 계산
        trajectory = self.calculate_ballistic_trajectory(L, alpha, beta, B_lat, B_lon, T_lat, T_lon)

        return trajectory

    def calculate_ballistic_trajectory(self, L, alpha, beta, B_lat, B_lon, T_lat, T_lon):
        bearing = self.calculate_bearing(B_lat, B_lon, T_lat, T_lon)

        trajectory = []
        steps = 1000
        for i in range(steps + 1):
            t = (i / steps) * L
            x = t
            z = (t / L) * (1 - (t / L)) * (alpha * L + beta * (t / L)) * L
            z = z/1000

            current_point = self.calculate_point_at_distance_and_bearing(Point(B_lat, B_lon), x, bearing)

            if current_point:
                trajectory.append((current_point[0], current_point[1], z))

        return trajectory

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        return distance.geodesic((lat1, lon1), (lat2, lon2)).km

    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        initial_bearing = math.atan2(y, x)
        return math.degrees(initial_bearing)

    def calculate_point_at_distance_and_bearing(self, start, distance, bearing):
        start_lat = math.radians(start.latitude)
        start_lon = math.radians(start.longitude)
        bearing = math.radians(bearing)
        angular_distance = distance / self.EARTH_RADIUS

        end_lat = math.asin(
            math.sin(start_lat) * math.cos(angular_distance) +
            math.cos(start_lat) * math.sin(angular_distance) * math.cos(bearing)
        )

        end_lon = start_lon + math.atan2(
            math.sin(bearing) * math.sin(angular_distance) * math.cos(start_lat),
            math.cos(angular_distance) - math.sin(start_lat) * math.sin(end_lat)
        )

        return math.degrees(end_lat), math.degrees(end_lon)


# 사용 예시
# calculator = MissileTrajectoryCalculator()
# missile_base = (37.5665, 126.9780)  # 서울의 위도, 경도
# target = (35.6895, 139.6917)  # 도쿄의 위도, 경도
# trajectory = calculator.calculate_trajectory(missile_base, target, 'Nodong')
#
# print("궤적 포인트 (위도, 경도, 고도):")
# for point in trajectory:
#     print(f"위도: {point[0]:.4f}, 경도: {point[1]:.4f}, 고도: {point[2]:.2f} km")
