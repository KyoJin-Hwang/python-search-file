import sys
import os
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel, QHBoxLayout, QComboBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QMovie, QFont, QIcon

import concurrent.futures
import time

class OwenFileSearch(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("다함기술 파일검색용")
        self.resize(700, 600)  # 창 크기 설정
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            resource_path = sys._MEIPASS + "/resources/icon.ico"
        else:
            # 개발 중인 경우
            resource_path = "resources/icon.ico"
        # 아이콘 설정
        self.setWindowIcon(QIcon(resource_path))
        # 화면 중앙으로 이동
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_width = self.width()
        window_height = self.height()
        center_x = (screen_geometry.width() - window_width) // 2
        center_y = (screen_geometry.height() - window_height) // 2
        self.move(center_x, center_y)  # 윈도우를 중앙으로 이동

        # 배경 색상
        self.setStyleSheet("background-color: #2E2E2E;")  # 어두운 배경

        # 레이아웃
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)  # 외부 여백 설정
        layout.setSpacing(15)  # 각 요소 간 간격 설정

        # 입력창
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("파일명을 입력하세요...")
        self.input_field.setStyleSheet("""
            background-color: #3B3B3B;
            border-radius: 10px;
            padding: 15px;
            font-size: 16px;
            color: white;
            selection-background-color: #4CAF50;
        """)
        self.input_field.returnPressed.connect(self.start_search)  # 엔터키로 검색
        layout.addWidget(self.input_field)

        # 찾기 버튼
        self.search_btn = QPushButton("찾기", self)
        self.search_btn.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px;
            font-size: 18px;
            font-weight: bold;
        """)
        self.search_btn.clicked.connect(self.start_search)
        layout.addWidget(self.search_btn)

        # 검색 기록 셀렉트박스
        self.history_combo = QComboBox(self)
        self.history_combo.addItem("이전 검색 기록을 선택하세요")  # 기본 항목
        self.history_combo.setStyleSheet("""
            background-color: #3B3B3B;
            border-radius: 10px;
            padding: 12px;
            font-size: 16px;
            color: white;
        """)
        self.history_combo.currentIndexChanged.connect(self.load_selected_search)
        layout.addWidget(self.history_combo)

        # 결과 리스트
        self.result_list = QListWidget(self)
        self.result_list.setStyleSheet("""
            background-color: #444444;
            border: 1px solid #666;
            border-radius: 10px;
            padding: 15px;
            color: white;
        """)
        self.result_list.itemDoubleClicked.connect(self.open_folder)  # 더블클릭하면 폴더 열기
        layout.addWidget(self.result_list)

        # 상태 표시 레이블
        self.status_label = QLabel("파일 검색 준비 완료.", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 텍스트 크기 키우기
        font = QFont()
        font.setPointSize(18)  # 글꼴 크기를 18pt로 설정
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: #F1F1F1;")  # 텍스트 색상 설정
        layout.addWidget(self.status_label)

        # 로딩 애니메이션을 위한 레이아웃
        self.loading_layout = QHBoxLayout()
        self.loading_label = QLabel(self)
        self.loading_layout.addWidget(self.loading_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(self.loading_layout)

        self.setLayout(layout)

        # 검색 기록과 캐시
        self.search_history = []  # 검색 기록 저장
        self.search_cache = {}  # 검색 결과 캐시 저장

    def start_search(self):
        search_term = self.input_field.text().strip()
        if not search_term:
            self.status_label.setText("파일명을 입력하세요!")
            return

        self.result_list.clear()
        self.status_label.setText("파일을 찾는 중...")

        # 로딩 애니메이션 시작
        self.loading_label.setVisible(True)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 경우
            resource_path = sys._MEIPASS + "/images/loading.gif"
        else:
            # 개발 중인 경우
            resource_path = "images/loading.gif"
        # 애니메이션 파일 경로 수정 (로딩 애니메이션 경로를 정확히 설정)
        movie = QMovie(resource_path)  # "images/loading.gif"와 같이 경로를 정확히 설정
        self.loading_label.setMovie(movie)
        movie.start()

        # 검색 결과가 캐시된 결과인지 확인
        if search_term in self.search_cache:
            # 캐시된 결과가 있다면 바로 표시
            self.display_results(self.search_cache[search_term])
        else:
            # 캐시된 결과가 없다면 새로운 검색 시작
            # 검색 시작 시간 기록
            self.start_time = time.time()

            # 백그라운드 스레드에서 파일 검색
            self.search_thread = SearchThread(search_term)
            self.search_thread.result_signal.connect(self.cache_and_display_results)
            self.search_thread.start()

        # 검색 기록에 추가
        if search_term not in self.search_history:
            self.search_history.append(search_term)
            self.history_combo.addItem(search_term)  # 셀렉트박스에 추가

    def load_selected_search(self):
        selected_term = self.history_combo.currentText()
        if selected_term != "이전 검색 기록을 선택하세요":
            self.input_field.setText(selected_term)
            self.start_search()

    def cache_and_display_results(self, found_files):
        # 검색이 끝난 후 결과를 캐시하고 화면에 표시
        self.search_cache[self.input_field.text().strip()] = found_files
        self.display_results(found_files)

    def display_results(self, found_files):
        # 로딩 애니메이션 숨기기
        self.loading_label.setVisible(False)

        if found_files:
            self.result_list.addItems(found_files)
            self.status_label.setText(f"{len(found_files)}개의 파일을 찾았습니다.")
        else:
            self.status_label.setText("파일을 찾을 수 없습니다.")

    def open_folder(self, item):
        file_path = item.text()

        # 파일을 선택하는 명령어 (파일 탐색기에서 해당 파일을 선택)
        subprocess.run(f'explorer /select,"{file_path}"', shell=True)  # explorer를 통해 파일 선택


class SearchThread(QThread):
    result_signal = pyqtSignal(list)

    def __init__(self, search_term):
        super().__init__()
        self.search_term = search_term

    def run(self):
        found_files = self.search_files(self.search_term)
        self.result_signal.emit(found_files)

    def search_files(self, search_term):
        found_files = []
        search_path = "C:\\Users\\user"  # 검색할 폴더

        # os.walk()로 모든 하위 디렉터리를 순차적으로 검색
        # concurrent.futures를 사용해 디렉터리를 병렬 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for root, dirs, files in os.walk(search_path):
                futures.append(executor.submit(self.process_directory, root, files, search_term))

            for future in concurrent.futures.as_completed(futures):
                found_files.extend(future.result())

        return found_files

    def process_directory(self, root, files, search_term):
        found_files = []
        for file in files:
            if search_term.lower() in file.lower() and not file.lower().endswith(".lnk"):
                found_files.append(os.path.join(root, file))
        return found_files


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OwenFileSearch()
    window.show()
    sys.exit(app.exec())
