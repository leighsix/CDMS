import numpy as np
from pyswarm import pso
import sys, os
import multiprocessing as mp
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache


class OptimizationThread(QThread):
    progress_updated = pyqtSignal(int)
    optimization_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, optimizer, selected_weapon_assets):
        super().__init__()
        self.optimizer = optimizer
        self.selected_weapon_assets = selected_weapon_assets
        self.max_iterations = self.optimizer.max_iterations

    def run(self):
        try:
            optimized_locations = self.optimizer.optimize_locations(self.selected_weapon_assets, self.progress_callback)
            self.progress_updated.emit(100)  # 최종 100% 진행률 표시
            self.optimization_complete.emit(optimized_locations)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def progress_callback(self, iteration):
        progress = int((iteration / self.max_iterations) * 100)
        self.progress_updated.emit(progress)

class MissileDefenseOptimizer:
    def __init__(self, trajectories, weapon_systems_info, grid_bounds, engagement_calculator):
        try:
            self.trajectories = trajectories
            self.weapon_systems_info = weapon_systems_info

            # grid_bounds를 float로 변환
            self.grid_bounds = (
                (float(grid_bounds[0][0]), float(grid_bounds[0][1])),
                (float(grid_bounds[1][0]), float(grid_bounds[1][1]))
            )

            self.engagement_calculator = engagement_calculator
            self.optimized_locations = []
            self.grid_centers = self.create_grid()
            self.current_iteration = 0
            self.max_iterations = 100
            self.min_defense_rate = None
            self.defense_cache = {}
        except Exception as e:
            print(f"MissileDefenseOptimizer 초기화 중 오류 발생: {e}")
            raise

    def create_grid(self):
        try:
            # 모든 입력값을 명시적으로 float로 변환
            lat_step = float(20.0 / 111)

            # grid_bounds 값들을 float로 확실하게 변환
            center_lat = float(self.grid_bounds[0][0])
            center_lon = float(self.grid_bounds[1][0])

            lon_step = float(20.0 / (111 * np.cos(np.radians(center_lat))))

            grid_centers = {}
            alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

            lat_index = 0
            for lat in np.arange(float(self.grid_bounds[0][1]),
                                 float(self.grid_bounds[0][0]),
                                 -lat_step):
                lon_index = 0
                for lon in np.arange(float(self.grid_bounds[1][0]),
                                     float(self.grid_bounds[1][1]),
                                     lon_step):
                    if lat_index < 26 and lon_index < 26:
                        grid_name = f"{alphabet[lon_index]}{lat_index + 1}"
                        grid_centers[grid_name] = (float(lat), float(lon))
                    lon_index += 1
                lat_index += 1

            return grid_centers

        except Exception as e:
            print(f"그리드 생성 중 오류 발생: {e}")
            print(f"grid_bounds: {self.grid_bounds}")
            print(f"데이터 타입 - grid_bounds[0][0]: {type(self.grid_bounds[0][0])}")
            raise

    def optimize_locations(self, selected_weapon_assets, progress_callback):
        """
        무기체계의 최적 배치 위치를 찾는 함수
        Args:
            selected_weapon_assets: 선택된 무기체계 목록
            progress_callback: 진행률을 업데이트하는 콜백 함수
        Returns:
            최적화된 배치 해결책
        """
        try:
            if not selected_weapon_assets:
                raise ValueError("선택된 무기체계가 없습니다.")

            best_solution = None
            best_defense_rate = -float('inf')
            original_max_iterations = self.max_iterations
            self.optimal_found = False  # 전역 플래그 추가

            # 3번의 최적화 시도를 수행
            for attempt in range(3):
                try:
                    self.current_iteration = 0
                    np.random.seed(42 + attempt)  # 재현성을 위한 시드 설정

                    def objective_function(x):
                        if self.optimal_found:  # 최적해를 찾았다면 더 이상의 계산을 하지 않음
                            return -len(self.trajectories)
                        self.current_iteration += 1
                        current_progress = (self.current_iteration + attempt * original_max_iterations) / (
                                    3 * original_max_iterations)
                        progress_callback(int(current_progress * 100))

                        num_defense_systems = len(selected_weapon_assets)
                        grid_positions = np.array(list(self.grid_centers.values()))
                        position_indices = x[:num_defense_systems].astype(int) % len(grid_positions)
                        azimuth_indices = (x[num_defense_systems:].astype(int) % 36) * 10
                        positions = grid_positions[position_indices]

                        # 벡터화된 연산을 위해 모든 궤적을 한 번에 처리
                        trajectories = np.array([trajectory['trajectory'] for trajectory in self.trajectories])
                        total_defended = np.zeros(len(self.trajectories), dtype=bool)

                        # 모든 방어 시스템의 결과를 병렬로 계산
                        for pos, az, wa in zip(positions, azimuth_indices, selected_weapon_assets):
                            current_defense = self.engagement_calculator.check_engagement_possibility_vectorized(pos[0],
                                                                                                                 pos[1],
                                                                                                                 wa[4],
                                                                                                                 trajectories,
                                                                                                                 az)
                            total_defended |= current_defense

                            # 100% 방어율 달성 시 즉시 종료
                            if np.all(total_defended):
                                self.optimal_found = True  # 최적해 발견 시 플래그 설정
                                return -len(self.trajectories)  # 최소화 문제이므로 가장 낮은 값 반환

                        defended_count = np.sum(total_defended)
                        return -defended_count  # 최소화 문제이므로 음수 반환

                    # 최적화 범위 설정
                    num_defense_systems = len(selected_weapon_assets)
                    grid_positions = np.array(list(self.grid_centers.values()))

                    # 경계값 설정
                    lb = np.zeros(num_defense_systems * 2)
                    ub = np.concatenate([
                        np.array([len(grid_positions)] * num_defense_systems) - 1,
                        np.array([36] * num_defense_systems)  # 0-350도 범위 설정
                    ])

                    # PSO 최적화 수행
                    optimized_values, _ = pso(objective_function, lb, ub,
                                              swarmsize=100,
                                              maxiter=self.max_iterations,
                                              omega=0.7,
                                              phip=2.0,
                                              phig=2.0,
                                              minstep=1e-8,
                                              minfunc=1e-8,
                                              debug=False)

                    # 최적해 생성 및 평가
                    current_solution = self._create_solution(optimized_values, selected_weapon_assets)
                    current_rate = self.calculate_total_defense_rate(current_solution)

                    if current_rate > best_defense_rate:
                        best_defense_rate = current_rate
                        best_solution = current_solution

                except Exception as e:
                    print(f"최적화 시도 {attempt + 1} 중 오류 발생: {e}")
                    continue

            # 최적화 결과가 초기 배치보다 나쁜 경우 초기 배치 반환
            original_defense_rate = self.calculate_initial_defense_rate(selected_weapon_assets)
            if best_defense_rate < original_defense_rate:
                return self.get_original_locations(selected_weapon_assets)

            return best_solution

        except Exception as e:
            error_msg = f"위치 최적화 중 오류 발생: {e}"
            print(error_msg)
            raise

    def _create_solution(self, optimized_values, selected_weapon_assets):
        num_defense_systems = len(selected_weapon_assets)
        grid_positions = np.array(list(self.grid_centers.values()))
        optimized_indices = optimized_values[:num_defense_systems].astype(int)
        optimized_azimuths = [(int(optimized_values[i + num_defense_systems]) * 10) % 360
                              for i in range(num_defense_systems)]

        solution = []
        for index, azimuth, weapon_asset in zip(optimized_indices, optimized_azimuths, selected_weapon_assets):
            position = tuple(grid_positions[index % len(grid_positions)])
            grid_name = list(self.grid_centers.keys())[list(self.grid_centers.values()).index(position)]
            defense_rate = self.calculate_defense_rate(position, weapon_asset[4], azimuth)

            solution.append({
                'defense_name': grid_name,
                'defense_coordinate': position,
                'threat_azimuth': azimuth,
                'defense_rate': defense_rate,
                'weapon_type': weapon_asset[4]
            })

        return solution

    def calculate_defense_rate(self, position, weapon_type, azimuth):
        try:
            total_trajectories = len(self.trajectories)
            if total_trajectories == 0:
                return 0

            trajectories = np.array([trajectory['trajectory'] for trajectory in self.trajectories])
            engagement_results = self.engagement_calculator.check_engagement_possibility_vectorized(
                position[0], position[1], weapon_type, trajectories, azimuth
            )

            defended_trajectories = np.sum(engagement_results)
            return (defended_trajectories / total_trajectories) * 100

        except Exception as e:
            print(f"방어율 계산 중 오류 발생: {e}")
            print(f"입력값 - position: {position}, weapon_type: {weapon_type}, azimuth: {azimuth}")
            raise

    def calculate_initial_defense_rate(self, selected_weapon_assets):
        defended_trajectories = set()  # 방어된 궤적을 추적하기 위한 집합
        total_trajectories = len(self.trajectories)

        for asset in selected_weapon_assets:
            lat, lon = self.parse_coordinates(asset[3])
            weapon_type = asset[4]
            azimuth = int(asset[6])

            # 각 무기체계별로 방어 가능한 궤적 확인
            trajectories = np.array([trajectory['trajectory'] for trajectory in self.trajectories])
            engagement_results = self.engagement_calculator.check_engagement_possibility_vectorized(
                lat, lon, weapon_type, trajectories, azimuth
            )

            # 방어 가능한 궤적의 인덱스를 집합에 추가
            defended_trajectories.update(np.where(engagement_results)[0])

        # 전체 궤적 대비 방어 가능한 궤적의 비율 계산
        if total_trajectories == 0:
            return 0
        return (len(defended_trajectories) / total_trajectories) * 100

    def get_original_locations(self, selected_weapon_assets):
        original_locations = []
        original_loc_dic ={}
        for asset in selected_weapon_assets:
            lat, lon = self.parse_coordinates(asset[3])
            position = (float(lat), float(lon))
            defense_rate = self.calculate_defense_rate(position, asset[4], int(asset[6]))
            original_loc_dic['defense_name'] = asset[0]
            original_loc_dic['defense_coordinate'] = position
            original_loc_dic['threat_azimuth'] = asset[6]
            original_loc_dic['defense_rate'] = defense_rate
            original_loc_dic['weapon_type'] = asset[4]
            original_locations.append(original_loc_dic)
        return original_locations

    def calculate_total_defense_rate(self, locations):
        if not locations:
            return 0

        # 모든 위치에서 방어 가능한 전체 궤적의 수를 계산
        total_trajectories = len(self.trajectories)
        if total_trajectories == 0:
            return 0

        defended_trajectories = set()
        for location in locations:
            pos = location['defense_coordinate']
            if isinstance(pos, str):
                lat, lon = self.parse_coordinates(pos)
            else:
                lat, lon = pos

            trajectories = np.array([trajectory['trajectory'] for trajectory in self.trajectories])
            engagement_results = self.engagement_calculator.check_engagement_possibility_vectorized(
                lat, lon, location['weapon_type'], trajectories, location['threat_azimuth']
            )
            defended_trajectories.update(np.where(engagement_results)[0])

        return (len(defended_trajectories) / total_trajectories) * 100

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon





