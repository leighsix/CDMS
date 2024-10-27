import math
import numpy as np
import cupy as cp

class EngagementPossibilityCalculator:
    def __init__(self, weapon_systems_info, missile_info):
        self.weapon_systems_info = weapon_systems_info
        self.missile_info = missile_info

    def find_intercept_point_vectorized(self, defense_lat, defense_lon, trajectory, weapon_type, threat_azimuth):
        defense_altitude_range = (self.weapon_systems_info[weapon_type].get('min_altitude'),
                                  self.weapon_systems_info[weapon_type].get('max_altitude'))
        defense_range = (self.weapon_systems_info[weapon_type].get('min_radius'),
                         self.weapon_systems_info[weapon_type].get('max_radius'))
        angle = self.weapon_systems_info[weapon_type].get('angle')

        trajectory = np.array(trajectory)
        points = len(trajectory)
        steps = 100

        # 모든 점들에 대한 보간 매트릭스 생성
        t = np.linspace(0, 1, steps + 1)
        t = t.reshape(-1, 1)

        # 각 세그먼트에 대한 보간
        segments = np.zeros((points - 1, steps + 1, 3))
        for i in range(points - 1):
            start = trajectory[i]
            end = trajectory[i + 1]

            segments[i, :, 0] = start[0] + t.flatten() * (end[0] - start[0])  # latitude
            segments[i, :, 1] = start[1] + t.flatten() * (end[1] - start[1])  # longitude
            segments[i, :, 2] = start[2] + t.flatten() * (end[2] - start[2])  # altitude

        # 모든 점들을 하나의 배열로 재구성
        all_points = segments.reshape(-1, 3)

        # 모든 점들에 대한 거리 계산
        distances = self.calculate_distance_vectorized(defense_lat, defense_lon, all_points[:, 0], all_points[:, 1])

        if angle >= 360:
            # 조건에 맞는 점들 찾기
            valid_points = (distances >= defense_range[0]) & (distances <= defense_range[1]) & \
                           (all_points[:, 2] >= defense_altitude_range[0]) & (
                                       all_points[:, 2] <= defense_altitude_range[1])
        else:
            # 방위각 계산
            azimuths = (np.degrees(
                np.arctan2(all_points[:, 1] - defense_lon, all_points[:, 0] - defense_lat)) + 360) % 360
            azimuth_diff = np.minimum((azimuths - threat_azimuth) % 360, (threat_azimuth - azimuths) % 360)

            valid_points = (azimuth_diff <= angle / 2) & \
                           (distances >= defense_range[0]) & (distances <= defense_range[1]) & \
                           (all_points[:, 2] >= defense_altitude_range[0]) & (
                                       all_points[:, 2] <= defense_altitude_range[1])

        # 유효한 첫 번째 점 찾기
        valid_indices = np.where(valid_points)[0]
        if len(valid_indices) > 0:
            first_valid_point = all_points[valid_indices[0]]
            return tuple(first_valid_point)

        return None

    def check_engagement_possibility_vectorized(self, defense_lat, defense_lon, weapon_type, trajectories,
                                                threat_azimuth):
        # 빈 궤적 체크
        if isinstance(trajectories, np.ndarray) and trajectories.size == 0:
            return np.array([])  # 빈 배열 반환

        # trajectories가 올바른 형태인지 확인
        trajectories = np.array(trajectories)
        if trajectories.ndim < 3:  # 차원 확인
            return np.array([False] * len(trajectories))

        range_tuple = (self.weapon_systems_info[weapon_type].get('min_radius'),
                       self.weapon_systems_info[weapon_type].get('max_radius'))
        altitude_tuple = (self.weapon_systems_info[weapon_type].get('min_altitude'),
                          self.weapon_systems_info[weapon_type].get('max_altitude'))
        angle = self.weapon_systems_info[weapon_type].get('angle')

        try:
            starts = trajectories[:, :-1, :]
            ends = trajectories[:, 1:, :]
            all_points = np.concatenate([starts, ends], axis=1)

            distances = self.calculate_distance_vectorized(defense_lat, defense_lon,
                                                           all_points[:, :, 0].astype(float),
                                                           all_points[:, :, 1].astype(float))

            altitude_condition = np.logical_and(
                all_points[:, :, 2] >= altitude_tuple[0],
                all_points[:, :, 2] <= altitude_tuple[1]
            )

            range_condition = np.logical_and(
                distances >= range_tuple[0],
                distances <= range_tuple[1]
            )

            if angle >= 360:
                engagement_possible = np.any(np.logical_and(range_condition, altitude_condition), axis=1)
            else:
                delta_lon = all_points[:, :, 1].astype(float) - defense_lon
                delta_lat = all_points[:, :, 0].astype(float) - defense_lat
                missile_azimuths = (np.degrees(np.arctan2(delta_lon, delta_lat)) + 360) % 360

                azimuth_diff = np.minimum((missile_azimuths - threat_azimuth) % 360,
                                          (threat_azimuth - missile_azimuths) % 360)

                angle_condition = azimuth_diff <= angle / 2

                combined_condition = np.logical_and.reduce((range_condition, altitude_condition, angle_condition))
                engagement_possible = np.any(combined_condition, axis=1)

            return engagement_possible

        except (IndexError, ValueError) as e:
            print(f"궤적 처리 중 오류 발생: {e}")
            return np.array([False] * len(trajectories))

    @staticmethod
    def calculate_distance_vectorized(lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c



