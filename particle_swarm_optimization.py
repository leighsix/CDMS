import numpy as np
from pyswarm import pso
import sys, os
import multiprocessing
import multiprocessing as mp
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pyswarms.single import GlobalBestPSO
from pyswarms.utils.functions import single_obj as fx


class OptimizationWorker(QObject):
    progress = pyqtSignal(int)  # 전체 진행률
    iteration_progress = pyqtSignal(int, int)  # 현재 시도 횟수, 현재 반복 진행률
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, optimizer, selected_weapon_assets):
        super().__init__()
        self.optimizer = optimizer
        self.selected_weapon_assets = selected_weapon_assets
        self._is_running = False
        self._stop_flag = False

    @property
    def is_running(self):
        return self._is_running

    def run(self):
        self._is_running = True
        try:
            def progress_callback(progress, attempt, max_iterations):
                if self._stop_flag:
                    raise StopIteration()
                # 현재 반복의 진행률 업데이트 (0-100%)
                self.iteration_progress.emit(attempt, progress)
                # 전체 진행률 업데이트 (각 시도는 10%씩 차지)
                total_progress = min(((attempt * 100) + progress) // 10, 100)
                self.progress.emit(total_progress)

            if not self._stop_flag:
                try:
                    result, summary = self.optimizer.optimize_locations(
                        self.selected_weapon_assets,
                        progress_callback
                    )
                    if not self._stop_flag:
                        self.finished.emit((result, summary))
                except StopIteration:
                    print("최적화가 취소되었습니다.")
                    return

        except Exception as e:
            print(f"최적화 작업 중 오류 발생: {e}")
            if not self._stop_flag:
                self.error.emit(str(e))
        finally:
            self._is_running = False

    def stop(self):
        self._stop_flag = True
        self._is_running = False
        if hasattr(self, 'optimizer'):
            self.optimizer.stop_optimization()


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
            self.attempts = 10
            self.min_defense_rate = None
            self.defense_cache = {}
            self.trajectory_array = None  # 궤적 배열 미리 계산
            self.priority_weights = None  # 우선순위 가중치 미리 계산
            self.grid_positions = None  # 그리드 위치 미리 계산
            self.selected_weapon_assets = None
            self._initialize_arrays()  # 배열 초기화
        except Exception as e:
            print(f"MissileDefenseOptimizer 초기화 중 오류 발생: {e}")
            raise

    def _initialize_arrays(self):
        # 궤적 배열을 3차원 배열로 변환하여 저장
        self.trajectory_array = np.array([trajectory['trajectory'] for trajectory in self.trajectories])
        if len(self.trajectory_array.shape) == 2:
            self.trajectory_array = self.trajectory_array.reshape(len(self.trajectories), -1, 2)

        priorities = np.array([float(trajectory['priority']) for trajectory in self.trajectories])
        max_priority = np.max(priorities)
        self.priority_weights = max_priority + 1 - priorities
        self.grid_positions = np.array(list(self.grid_centers.values()))

    def get_optimal_thread_count(self, attempts):
        # 시스템의 CPU 코어 수 확인
        cpu_count = multiprocessing.cpu_count()
        # 시도 횟수와 CPU 코어 수 중 작은 값을 선택
        # CPU 코어의 75%만 사용하도록 설정 (다른 작업을 위한 여유 확보)
        optimal_threads = min(attempts, max(1, int(cpu_count * 0.75)))
        return optimal_threads

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

    @lru_cache(maxsize=2048)
    def _check_engagement_batch(self, pos_tuple, weapon_type, azimuth):
        # 벡터화된 연산을 위해 배치 처리
        positions = np.array([pos_tuple] * len(self.trajectories))

        # azimuth를 브로드캐스팅 가능한 형태로 확장
        azimuth_array = np.full(positions.shape[0], azimuth)

        # trajectory_array 형상 확인 및 조정
        if len(self.trajectory_array.shape) == 3:
            trajectories = self.trajectory_array
        else:
            trajectories = np.array([t for t in self.trajectory_array])

        # positions 배열의 위도와 경도를 개별적으로 추출
        lat_array = positions[:, 0]  # 위도 배열
        lon_array = positions[:, 1]  # 경도 배열

        engagement_results = self.engagement_calculator.check_engagement_possibility_vectorized(
            lat_array,  # 위도 배열
            lon_array,  # 경도 배열
            weapon_type,  # 무기 타입
            trajectories,  # 궤적 배열
            azimuth_array  # 방위각 배열
        )

        return engagement_results

    def optimize_locations(self, selected_weapon_assets, progress_callback):
        try:
            if not selected_weapon_assets:
                raise ValueError("선택된 무기체계가 없습니다.")

            self.selected_weapon_assets = selected_weapon_assets
            completed_attempts = 0

            # ThreadPoolExecutor 부분 수정
            optimal_threads = self.get_optimal_thread_count(self.attempts)
            with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
                futures = []
                for attempt in range(self.attempts):
                    future = executor.submit(
                        self._single_optimization_attempt,
                        attempt,
                        selected_weapon_assets,
                        lambda x, y, z: progress_callback(x, y, z)
                    )
                    futures.append(future)

                # 모든 최적화 결과 수집
                all_solutions = []
                for future in as_completed(futures):
                    try:
                        solution, objective = future.result()
                        if solution is not None:
                            all_solutions.append((solution, objective))
                        completed_attempts += 1
                    except Exception as e:
                        print(f"최적화 시도 중 오류 발생: {e}")

            # 최적의 해결책 선택
            if all_solutions:
                best_solution, best_objective = min(all_solutions, key=lambda x: x[1])

                # 초기 배치와 비교
                initial_solution = self.get_original_locations(selected_weapon_assets)
                initial_objective = self._calculate_objective_value(initial_solution)

                # 상세 점수 계산
                best_scores = self._calculate_detailed_scores(best_solution)
                initial_scores = self._calculate_detailed_scores(initial_solution)

                summary = {
                    'attempts': len(all_solutions),
                    'best_scores': best_scores,
                    'initial_scores': initial_scores,
                    'is_improved': best_objective < initial_objective
                }

                return (best_solution if best_objective < initial_objective else initial_solution), summary
            else:
                initial_solution = self.get_original_locations(selected_weapon_assets)
                initial_scores = self._calculate_detailed_scores(initial_solution)
                summary = {
                    'attempts': 0,
                    'best_scores': None,
                    'initial_scores': initial_scores,
                    'is_improved': False
                }
                return initial_solution, summary

        except Exception as e:
            print(f"위치 최적화 중 오류 발생: {e}")
            raise

    def _calculate_detailed_scores(self, solution):
        """상세 점수 계산 메서드"""
        try:
            defense_matrix = np.zeros((len(solution), len(self.trajectories)))

            # 방어 매트릭스 계산
            for j, loc in enumerate(solution):
                defense_matrix[j] = self._check_engagement_batch(
                    tuple(loc['defense_coordinate']),
                    loc['weapon_type'],
                    loc['threat_azimuth']
                )

            defense_counts = np.sum(defense_matrix, axis=0)
            is_defended = defense_counts > 0

            # 기본 점수 계산
            defense_rate = np.mean(is_defended)
            priority_score = np.sum(is_defended * self.priority_weights) / np.sum(self.priority_weights)
            system_defense_rates = np.mean(defense_matrix, axis=1)
            min_system_defense = np.min(system_defense_rates)

            # 페널티 계산
            min_defense_penalty = 0 if min_system_defense >= 0.2 else -20000 * (0.2 - min_system_defense)
            coverage_penalty = 0 if defense_rate >= 0.8 else -20000 * (0.8 - defense_rate)
            overlap_penalty = -5000 * (np.sum(defense_counts > 1) / len(self.trajectories))

            return {
                'priority_score': priority_score * 2000,
                'defense_rate_score': np.mean(system_defense_rates) * 500,
                'min_defense_penalty': min_defense_penalty,
                'coverage_penalty': coverage_penalty,
                'overlap_penalty': overlap_penalty,
                'total_defense_rate': defense_rate * 100,
                'total_score': (priority_score * 2000 +
                                np.mean(system_defense_rates) * 500 +
                                min_defense_penalty +
                                coverage_penalty +
                                overlap_penalty)
            }

        except Exception as e:
            print(f"상세 점수 계산 중 오류 발생: {e}")
            return None

    def _single_optimization_attempt(self, attempt, selected_weapon_assets, progress_callback):
        """단일 최적화 시도를 수행하는 메서드"""
        try:
            # 중단 플래그 초기화
            self._stop_requested = False
            self._current_iteration = 0
            np.random.seed(42 + attempt)
            num_defense_systems = len(selected_weapon_assets)
            position_cache = {}

            # 벡터화된 목적 함수
            def objective_function(X, **kwargs):
                if hasattr(self, '_stop_requested') and self._stop_requested:
                    raise StopIteration("최적화가 사용자에 의해 중단되었습니다.")

                # 목적 함수가 호출될 때마다 반복 횟수 증가 및 진행률 업데이트
                self._current_iteration += 1
                progress = int((self._current_iteration / self.max_iterations) * 100)
                progress_callback(progress, attempt, self.max_iterations)


                penalties = np.zeros(len(X))
                position_indices = X[:, :num_defense_systems].astype(int) % len(self.grid_positions)
                azimuth_indices = (X[:, num_defense_systems:].astype(int) % 36) * 10

                # 배치 처리를 위한 벡터화된 연산
                for i, (pos_idx, az) in enumerate(zip(position_indices, azimuth_indices)):
                    cache_key = tuple(np.concatenate([pos_idx, az]))
                    if cache_key in position_cache:
                        penalties[i] = position_cache[cache_key]
                        continue

                    positions = self.grid_positions[pos_idx]
                    defense_matrix = np.zeros((num_defense_systems, len(self.trajectories)))

                    # 병렬 처리를 위한 벡터화된 교전 검사
                    for j, (pos, az_val, wa) in enumerate(zip(positions, az, selected_weapon_assets)):
                        defense_matrix[j] = self._check_engagement_batch(tuple(map(float, pos)), wa[4], az_val)

                    defense_counts = np.sum(defense_matrix, axis=0)
                    is_defended = defense_counts > 0
                    defense_rate = np.mean(is_defended)
                    priority_score = np.sum(is_defended * self.priority_weights) / np.sum(self.priority_weights)
                    system_defense_rates = np.mean(defense_matrix, axis=1)
                    min_system_defense = np.min(system_defense_rates)

                    # 페널티 계산 최적화

                    min_defense_penalty = np.where(min_system_defense < 0.2, -20000 * (0.2 - min_system_defense), 0)
                    coverage_penalty = np.where(defense_rate < 0.8, -20000 * (0.8 - defense_rate), 0)
                    overlap_penalty = -5000 * (np.sum(defense_counts > 1) / len(self.trajectories))


                    final_penalty = -(priority_score * 2000 + np.mean(
                        system_defense_rates) * 500 + min_defense_penalty + coverage_penalty + overlap_penalty)

                    position_cache[cache_key] = final_penalty
                    penalties[i] = final_penalty

                return penalties

            # PSO 매개변수 최적화
            n_particles = 150  # 입자 수 조정
            dimensions = num_defense_systems * 2
            bounds = (np.zeros(dimensions),
                      np.concatenate([
                          np.array([len(self.grid_positions)] * num_defense_systems) - 1,
                          np.array([36] * num_defense_systems)
                      ]))

            optimizer = GlobalBestPSO(
                n_particles=n_particles,
                dimensions=dimensions,
                options={'c1': 1.5, 'c2': 1.5, 'w': 0.7},  # PSO 매개변수 미세 조정
                bounds=bounds
            )

            best_cost, best_pos = optimizer.optimize(
                objective_function,
                iters=self.max_iterations,
                verbose=False
            )

            if best_cost == float('inf'):
                raise Exception("최적화 실패: 유효한 해를 찾을 수 없습니다.")
            return self._create_solution(best_pos, selected_weapon_assets), best_cost


        except StopIteration as e:
            return None, float('inf')

        except Exception as e:
            print(f"최적화 시도 중 오류 발생: {e}")
            raise

    def _calculate_objective_value(self, solution):
        if not solution:
            return float('inf')

        try:
            defense_matrix = np.zeros((len(solution), len(self.trajectories)))

            # 각 방어 시스템별 방어 가능성 계산
            for j, loc in enumerate(solution):
                defense_matrix[j] = self._check_engagement_batch(
                    tuple(loc['defense_coordinate']),
                    loc['weapon_type'],
                    loc['threat_azimuth']
                )

            # 방어 횟수 계산
            defense_counts = np.sum(defense_matrix, axis=0)
            is_defended = defense_counts > 0

            # 방어율 및 우선순위 점수 계산
            defense_rate = np.mean(is_defended)
            priority_score = np.sum(is_defended * self.priority_weights) / np.sum(self.priority_weights)

            # 각 시스템별 방어율 계산
            system_defense_rates = np.mean(defense_matrix, axis=1)
            min_system_defense = np.min(system_defense_rates)

            # 페널티 계산 강화
            min_defense_penalty = 0 if min_system_defense >= 0.2 else -20000 * (0.2 - min_system_defense)
            coverage_penalty = 0 if defense_rate >= 0.8 else -20000 * (0.8 - defense_rate)
            overlap_penalty = -5000 * (np.sum(defense_counts > 1) / len(self.trajectories))

            # 최종 점수 계산
            final_score = (priority_score * 2000 +
                           np.mean(system_defense_rates) * 500 +
                           min_defense_penalty +
                           coverage_penalty +
                           overlap_penalty)

            return -final_score  # 최소화 문제로 변환

        except Exception as e:
            print(f"목적 함수 계산 중 오류 발생: {e}")
            return float('inf')

    def _create_solution(self, optimized_values, selected_weapon_assets):
        num_defense_systems = len(selected_weapon_assets)
        grid_positions = np.array(list(self.grid_centers.values()))
        grid_names = list(self.grid_centers.keys())

        # 위치 인덱스와 방위각 분리
        position_indices = optimized_values[:num_defense_systems].astype(int) % len(grid_positions)
        azimuth_values = optimized_values[num_defense_systems:].astype(int) % 36 * 10

        solution = []
        used_positions = set()  # 중복 위치 방지용

        for i, (pos_idx, azimuth, weapon_asset) in enumerate(
                zip(position_indices, azimuth_values, selected_weapon_assets)):
            # 이미 사용된 위치면 다른 위치 선택
            while tuple(grid_positions[pos_idx]) in used_positions:
                pos_idx = (pos_idx + 1) % len(grid_positions)

            position = tuple(grid_positions[pos_idx])
            used_positions.add(position)

            # grid_name 할당
            grid_name = grid_names[pos_idx]

            # 방어율 계산 최적화
            defense_matrix = self._check_engagement_batch(position, weapon_asset[4], azimuth)
            defense_rate = np.mean(defense_matrix) * 100

            solution.append({
                'defense_name': grid_name,
                'defense_coordinate': position,
                'threat_azimuth': int(azimuth),
                'defense_rate': float(defense_rate),
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


    def get_original_locations(self, selected_weapon_assets):
        original_locations = []
        for asset in selected_weapon_assets:
            original_loc_dic = {}
            lat, lon = self.parse_coordinates(asset[3])
            position = (float(lat), float(lon))
            defense_rate = self.calculate_defense_rate(position, asset[4], int(asset[6]))
            original_loc_dic['defense_name'] = asset[2]
            original_loc_dic['defense_coordinate'] = position
            original_loc_dic['threat_azimuth'] = asset[6]
            original_loc_dic['defense_rate'] = defense_rate
            original_loc_dic['weapon_type'] = asset[4]
            original_locations.append(original_loc_dic)
        return original_locations

    @staticmethod
    def parse_coordinates(coord_string):
        """경위도 문자열을 파싱하여 위도와 경도를 반환합니다."""
        lat_str, lon_str = coord_string.split(',')
        lat = float(lat_str[1:])  # 'N' 제거
        lon = float(lon_str[1:])  # 'E' 제거
        return lat, lon

    def stop_optimization(self):
        try:
            # 최적화 중단 플래그 설정
            self._stop_requested = True

            # GlobalBestPSO의 최적화 중단을 위한 속성 설정
            if hasattr(self, 'optimizer'):
                # PSO 최적화 강제 종료를 위한 플래그
                self.optimizer.iteration = self.max_iterations + 1

            # 진행 중인 스레드 풀 작업 취소
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=False)

            # 캐시 및 상태 초기화
            self.current_iteration = 0
            self.optimized_locations = []
            self.defense_cache.clear()

            print("최적화가 중단되었습니다.")
            return True

        except Exception as e:
            print(f"최적화 중단 중 오류 발생: {e}")
            return False





