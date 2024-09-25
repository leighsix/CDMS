import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class MissileDefenseApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.db_path = "missile_defense.db"  # 기본 데이터베이스 경로
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_database()

    def initUI(self):
        # 기본 UI 구조 초기화
        self.setWindowTitle(self.tr("미사일 방어 시뮬레이션"))
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Matplotlib 캔버스 생성 및 추가
        self.canvas = FigureCanvas(plt.Figure(figsize=(5, 3)))
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()

        # 메뉴바 생성
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('파일')

        # 메뉴 액션 추가
        loadAction = fileMenu.addAction('데이터 로드')
        loadAction.triggered.connect(self.load_data)

        calculateAction = fileMenu.addAction('궤적 계산')
        calculateAction.triggered.connect(self.calculate_trajectories)

        optimizeAction = fileMenu.addAction('최적화')
        optimizeAction.triggered.connect(self.optimize_locations)

        visualizeAction = fileMenu.addAction('시각화')
        visualizeAction.triggered.connect(self.visualize_results)

    def create_database(self):
        # 데이터베이스 및 테이블 생성
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS missile_bases (
            id INTEGER PRIMARY KEY, name TEXT, latitude REAL, longitude REAL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS defense_units (
            id INTEGER PRIMARY KEY, name TEXT, latitude REAL, longitude REAL)''')
        self.conn.commit()

    def load_data(self):
        # 파일로부터 미사일 기지와 방어시설 정보를 로드
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, '파일 열기', '', 'CSV Files (*.csv);;All Files (*)')
            if file_name:
                # CSV 파일 로드
                data = np.genfromtxt(file_name, delimiter=',', dtype=None, encoding=None, names=True)
                for row in data:
                    if row['type'] == 'missile_base':
                        self.cursor.execute('INSERT INTO missile_bases (name, latitude, longitude) VALUES (?, ?, ?)',
                                            (row['name'], row['latitude'], row['longitude']))
                    elif row['type'] == 'defense_unit':
                        self.cursor.execute('INSERT INTO defense_units (name, latitude, longitude) VALUES (?, ?, ?)',
                                            (row['name'], row['latitude'], row['longitude']))
                self.conn.commit()
                QMessageBox.information(self, "성공", "데이터가 성공적으로 로드되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "에러", f"데이터 로드 중 오류 발생: {str(e)}")

    def calculate_trajectories(self):
        # 미사일 궤적 계산
        try:
            self.cursor.execute('SELECT latitude, longitude FROM missile_bases')
            missile_bases = self.cursor.fetchall()
            self.cursor.execute('SELECT latitude, longitude FROM defense_units')
            defense_units = self.cursor.fetchall()

            if not missile_bases or not defense_units:
                QMessageBox.warning(self, "경고", "미사일 기지 또는 방어유닛 정보가 없습니다.")
                return

            trajectories = []
            for defense in defense_units:
                for missile in missile_bases:
                    distance = np.sqrt((defense[0] - missile[0]) ** 2 + (defense[1] - missile[1]) ** 2)
                    trajectories.append((missile, defense, distance))

            self.trajectories = trajectories
            QMessageBox.information(self, "성공", "궤적 계산이 완료되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "에러", f"궤적 계산 중 오류 발생: {str(e)}")

    def calculate_engagement_zones(self):
        # 방공포대 교전가능 공간 계산
        try:
            self.cursor.execute('SELECT latitude, longitude FROM defense_units')
            defense_units = self.cursor.fetchall()
            engagement_zones = []
            for unit in defense_units:
                # TODO: 실제 교전 가능 공간 계산 로직 구현 필요
                zone = np.random.rand(5, 2) * 100  # 예시: 실제 계산 로직으로 대체 필요
                engagement_zones.append((unit, zone))
            self.engagement_zones = engagement_zones
        except Exception as e:
            QMessageBox.critical(self, "에러", f"교전 가능 공간 계산 중 오류 발생: {str(e)}")

    def optimize_locations(self):
        # 최적 방공포대 위치 선정
        try:
            if not hasattr(self, 'engagement_zones'):
                self.calculate_engagement_zones()
            if not hasattr(self, 'trajectories'):
                self.calculate_trajectories()

            # TODO: 최적화 알고리즘 구현 필요
            optimized_locations = []  # 예시: 실제 최적화 로직으로 대체 필요
            for zone in self.engagement_zones:
                optimized_locations.append(zone[0])

            self.optimized_locations = optimized_locations
            QMessageBox.information(self, "성공", "위치 최적화가 완료되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "에러", f"위치 최적화 중 오류 발생: {str(e)}")

    def visualize_results(self):
        # 결과 시각화
        try:
            self.ax.clear()
            if hasattr(self, 'trajectories'):
                for missile, defense, distance in self.trajectories:
                    self.ax.plot([missile[1], defense[1]], [missile[0], defense[0]], 'r-')

            if hasattr(self, 'optimized_locations'):
                for location in self.optimized_locations:
                    self.ax.plot(location[1], location[0], 'go')

            self.ax.set_xlabel('경도')
            self.ax.set_ylabel('위도')
            self.ax.set_title('미사일 방어 시뮬레이션 결과')
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "에러", str(e))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MissileDefenseApp()
    ex.show()
    sys.exit(app.exec_())
