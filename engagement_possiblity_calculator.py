import math
import numpy as np

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
        # 입력 데이터 형태 검증 및 변환
        trajectories = np.array(trajectories)
        if trajectories.size == 0:
            return np.array([])

        # 3차원 배열로 형상 변환 확인 및 조정
        if trajectories.ndim == 2:
            trajectories = trajectories.reshape(1, -1, 3)
        elif trajectories.ndim != 3:
            return np.array([False] * len(trajectories))

        # weapon_type이 없는 경우를 처리하기 위한 기본값 설정
        weapon_info = self.weapon_systems_info.get(weapon_type, {
            'min_radius': 0,
            'max_radius': 0,
            'min_altitude': 0,
            'max_altitude': 0,
            'angle': 0
        })

        range_tuple = (weapon_info.get('min_radius'), weapon_info.get('max_radius'))
        altitude_tuple = (weapon_info.get('min_altitude'), weapon_info.get('max_altitude'))
        angle = weapon_info.get('angle')

        try:
            # defense_lat과 defense_lon을 적절한 shape으로 확장
            defense_lat = np.array(defense_lat).reshape(-1, 1)
            defense_lon = np.array(defense_lon).reshape(-1, 1)

            # 거리 계산
            distances = self.calculate_distance_vectorized(
                defense_lat,
                defense_lon,
                trajectories[:, :, 0],
                trajectories[:, :, 1]
            )

            # 고도 조건 확인
            altitude_condition = np.logical_and(
                trajectories[:, :, 2] >= altitude_tuple[0],
                trajectories[:, :, 2] <= altitude_tuple[1]
            )

            # 거리 조건 확인
            range_condition = np.logical_and(
                distances >= range_tuple[0],
                distances <= range_tuple[1]
            )

            if angle >= 360:
                engagement_possible = np.any(np.logical_and(range_condition, altitude_condition), axis=1)
            else:
                # 방위각 계산
                delta_lon = trajectories[:, :, 1] - defense_lon
                delta_lat = trajectories[:, :, 0] - defense_lat
                missile_azimuths = (np.degrees(np.arctan2(delta_lon, delta_lat)) + 360) % 360

                # threat_azimuth을 적절한 shape으로 확장
                threat_azimuth = np.array(threat_azimuth).reshape(-1, 1)

                # 방위각 차이 계산
                azimuth_diff = np.minimum(
                    (missile_azimuths - threat_azimuth) % 360,
                    (threat_azimuth - missile_azimuths) % 360
                )

                angle_condition = azimuth_diff <= angle / 2
                combined_condition = np.logical_and.reduce((
                    range_condition,
                    altitude_condition,
                    angle_condition
                ))
                engagement_possible = np.any(combined_condition, axis=1)

            return engagement_possible

        except Exception as e:
            print(f"궤적 처리 중 오류 발생: {e}")
            print(f"trajectories shape: {trajectories.shape}")
            return np.array([False] * trajectories.shape[0])

    @staticmethod
    def calculate_distance_vectorized(lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c



