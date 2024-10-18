import json
import math
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
        try:
            B_lat, B_lon = missile_base
            T_lat, T_lon = target

            L = self.calculate_distance(B_lat, B_lon, T_lat, T_lon)

            coeffs = self.missile_info[missile_type]['trajectory_coefficients']
            alpha = coeffs['alpha']['a1'] * L + coeffs['alpha']['a2']
            beta = coeffs['beta']['a1'] * L + coeffs['beta']['b1']

            x, y, z = self.calculate_ballistic_trajectory(L, alpha, beta)
            bearing = self.calculate_bearing(B_lat, B_lon, T_lat, T_lon)
            trajectory = self.convert_trajectory_to_coordinates(B_lat, B_lon, T_lat, T_lon, bearing, x, y, z)
            return trajectory

        except KeyError as e:
            print(f"미사일 타입 오류: {e}")
        except ValueError as e:
            print(f"입력값 오류: {e}")
        except Exception as e:
            print(f"궤적 계산 중 예상치 못한 오류 발생: {e}")
        return None

    @staticmethod
    def calculate_ballistic_trajectory(distance, alpha, beta):
        t = np.linspace(0, 1, 1000)
        x = distance * t
        y = alpha * x * (1 - x / distance) + beta * x * (1 - x / distance) * (x / distance)
        z = np.zeros_like(x)
        return x, y, z

    def convert_trajectory_to_coordinates(self, start_lat, start_lon, end_lat, end_lon, bearing, x, y, z):
        trajectory = []
        start = Point(start_lat, start_lon)

        for i in range(len(x)):
            point = self.calculate_point_at_distance_and_bearing(start, x[i], bearing)
            if point:
                trajectory.append((point[0], point[1], y[i]))

        if trajectory:
            trajectory[-1] = (end_lat, end_lon, 0)

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
