import numpy as np
from scipy.optimize import minimize
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QHBoxLayout, QSplitter, QComboBox, QLineEdit, QTableWidget, QPushButton, QLabel,
                             QGroupBox, QCheckBox, QHeaderView, QDialog, QTableWidgetItem)

class ParticleSwarmOptimization:
    def __init__(self, num_particles, num_dimensions, bounds, max_iterations=100):
        self.num_particles = num_particles
        self.num_dimensions = num_dimensions
        self.bounds = bounds
        self.max_iterations = max_iterations

        self.particles = np.random.uniform(bounds[:, 0], bounds[:, 1], (num_particles, num_dimensions))
        self.velocities = np.zeros((num_particles, num_dimensions))
        self.personal_best = self.particles.copy()
        self.global_best = self.particles[0]

    def optimize(self, objective_function):
        for _ in range(self.max_iterations):
            for i in range(self.num_particles):
                fitness = objective_function(self.particles[i])
                if fitness < objective_function(self.personal_best[i]):
                    self.personal_best[i] = self.particles[i]
                if fitness < objective_function(self.global_best):
                    self.global_best = self.particles[i]

            w = 0.5
            c1 = 1.5
            c2 = 1.5
            r1, r2 = np.random.rand(2)

            self.velocities = (w * self.velocities +
                               c1 * r1 * (self.personal_best - self.particles) +
                               c2 * r2 * (self.global_best - self.particles))

            self.particles += self.velocities
            self.particles = np.clip(self.particles, self.bounds[:, 0], self.bounds[:, 1])

        return self.global_best


class MissileDefenseOptimizer:
    def __init__(self, trajectories, weapon_systems, grid_bounds):
        self.trajectories = trajectories
        self.weapon_systems = weapon_systems
        self.grid_bounds = grid_bounds

    def objective_function(self, defense_positions):
        num_defended = 0
        for trajectory in self.trajectories:
            if self.is_trajectory_defended(trajectory, defense_positions):
                num_defended += 1
        return -num_defended  # 최대화 문제를 최소화 문제로 변환

    def is_trajectory_defended(self, trajectory, defense_positions):
        for position in defense_positions.reshape(-1, 2):
            for weapon in self.weapon_systems:
                if self.check_engagement_possibility(position, weapon, trajectory):
                    return True
        return False

    def check_engagement_possibility(self, position, weapon, trajectory):
        # 여기에 무기 시스템의 교전 가능성을 확인하는 로직 구현
        # 예: 거리 계산, 고도 확인 등
        pass

    def optimize(self, num_defense_systems):
        num_dimensions = num_defense_systems * 2  # 각 방어 시스템의 위도와 경도
        bounds = np.tile(self.grid_bounds, (num_defense_systems, 1))

        pso = ParticleSwarmOptimization(num_particles=50, num_dimensions=num_dimensions, bounds=bounds)
        best_positions = pso.optimize(self.objective_function)

        return best_positions.reshape(-1, 2)


def optimize_locations(self):
    try:
        # 격자 범위 설정
        grid_bounds = np.array([[33.5, 38.5], [125.5, 129.5]])

        # 최적화 객체 생성
        optimizer = MissileDefenseOptimizer(self.trajectories, self.weapon_systems_info, grid_bounds)

        # 방어 시스템 수 설정 (예: 5개)
        num_defense_systems = 5

        # 최적화 실행
        optimized_positions = optimizer.optimize(num_defense_systems)

        # 최적화 결과 저장
        self.optimized_locations = []
        for position in optimized_positions:
            for trajectory in self.trajectories:
                if optimizer.is_trajectory_defended(trajectory, position):
                    self.optimized_locations.append({
                        'defense_coordinate': tuple(position),
                        'trajectory': trajectory['trajectory'],
                        'base_name': trajectory['base_name'],
                        'target_name': trajectory['target_name'],
                        'missile_type': trajectory['missile_type'],
                        'weapon_type': 'Optimal'  # 실제 무기 유형은 추가 로직으로 결정 가능
                    })

        # 결과 출력 및 지도 업데이트
        self.update_result_table()
        self.update_map_with_optimized_locations()

    except Exception as e:
        QMessageBox.critical(self, self.tr("오류"), self.tr(f"최적 방공포대 위치 산출 오류: {e}"))



def update_result_table(self):
    self.result_table.setRowCount(0)
    self.result_table.setColumnCount(4)
    self.result_table.setHorizontalHeaderLabels(["최적 위치", "방어 가능 자산", "무기 유형", "위협 방위각"])

    for location in self.optimized_locations:
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(str(location['defense_coordinate'])))
        self.result_table.setItem(row, 1, QTableWidgetItem(location['target_name']))
        self.result_table.setItem(row, 2, QTableWidgetItem(location['weapon_type']))
        self.result_table.setItem(row, 3, QTableWidgetItem("N/A"))  # 방위각은 추가 계산 필요


def run_location_optimization(self):
    try:
        self.calculate_trajectories()
        self.optimize_locations()

        if not self.optimized_locations:
            QMessageBox.warning(self, "경고", "최적화된 위치가 없습니다.")
            return

        self.update_result_table()
        self.update_map_with_optimized_locations()

    except Exception as e:
        QMessageBox.critical(self, self.tr("오류"), self.tr(f"최적 방공포대 위치 산출 오류: {e}"))

