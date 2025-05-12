import os
import csv
import cv2
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPixmap
from ultralytics import YOLO  # YOLOv8 라이브러리 임포트

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # UI 파일 로드
        self.form, self.window = uic.loadUiType("./res/mainWindow.ui")
        self.ui = self.form()
        self.ui.setupUi(self)

        # SaveButton 클릭 이벤트 연결
        self.ui.SaveButton.clicked.connect(self.save_data)

        # PhotoButton 클릭 이벤트 연결
        self.ui.photoButton.clicked.connect(self.capture_photo)

        # 웹 카메라 초기화
        self.cap = cv2.VideoCapture(0)  # 0번 카메라(기본 웹캠)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", "웹 카메라를 열 수 없습니다.")
            return

        # 타이머 설정 (웹캠 프레임 업데이트)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms마다 업데이트

        # YOLOv8 모델 로드
        self.model = YOLO("./best.pt")  # YOLOv8 모델 경로

        # 사진 파일 경로 초기화
        self.current_photo_path = ""

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        results = self.model(frame)

        # 'empty space' 개체 수 계산
        empty_space_count = 0

        # 클래스 매핑 정의
        label_map = {
            0: ('empty space', (255, 0, 0)),     
            1: ('parked place', (0, 0, 255))    
        }

        for result in results[0].boxes:
            x1, y1, x2, y2 = map(int, result.xyxy[0])
            cls = int(result.cls.item())  # 클래스 번호
            conf = float(result.conf.item())  # 신뢰도
            label_name, color = label_map.get(cls, ("unknown", (0, 0, 255)))

            # 'empty space' 개체 수 증가
            if label_name == 'empty space':
                empty_space_count += 1

            label = f"{label_name} {conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # UI에 'empty space' 개체 수 표시
        self.ui.lineEditPhone.setText(str(empty_space_count))  # 기존 phone 필드에 표시

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.ui.lblCamera.setPixmap(QPixmap.fromImage(qimg))

    def capture_photo(self):
        # 이름 입력 필드에서 파일 이름 가져오기
        name = self.ui.lineEditName.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "이름을 입력하세요.")
            return

        # 웹 카메라에서 현재 프레임 캡처
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(self, "Error", "사진을 캡처할 수 없습니다.")
            return

        # webImages 폴더 생성 (없으면 생성)
        save_dir = "./webImages"
        os.makedirs(save_dir, exist_ok=True)

        # 파일 이름 생성 (이름 기반)
        file_name = os.path.join(save_dir, f"{name}.jpg")

        # 이미지 저장
        try:
            cv2.imwrite(file_name, frame)
            self.current_photo_path = file_name  # 현재 사진 경로 저장
            # 저장된 파일 경로를 fileName에 표시
            self.ui.fileName.setText(file_name)
            # 저장된 파일 이름과 경로를 사용자에게 알림
            QMessageBox.information(self, "Success", f"사진이 저장되었습니다!\n파일 이름: {name}.jpg\n경로: {file_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"사진 저장에 실패했습니다: {e}")

    def save_data(self):
        # 입력 필드에서 데이터 가져오기
        name = self.ui.lineEditName.text().strip()  # QLineEdit에서 텍스트 가져오기
        empty_space_count = self.ui.lineEditPhone.text().strip()  # 'empty space' 개체 수 가져오기
        note = self.ui.textEditRemark.toPlainText().strip()  # QTextEdit에서 텍스트 가져오기

        # 입력값 검증
        if not name:
            QMessageBox.warning(self, "Validation Error", "동을 입력하시오.")
            return
        if not empty_space_count.isdigit():
            QMessageBox.warning(self, "Validation Error", "'empty space' 개체 수가 유효하지 않습니다.")
            return
        if len(note) > 200:
            QMessageBox.warning(self, "Validation Error", "참고사항은 200자를 초과할 수 없습니다.")
            return
        if not self.current_photo_path:
            QMessageBox.warning(self, "Validation Error", "사진을 먼저 촬영하세요.")
            return

        # 데이터 저장 (CSV 파일에 추가)
        try:
            with open("data.csv", "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([name, empty_space_count, note])  # 데이터를 한 줄로 추가
            QMessageBox.information(self, "Success", "데이터가 'data.csv' 파일에 성공적으로 저장되었습니다!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"데이터 저장에 실패했습니다: {e}")

    def closeEvent(self, event):
        # 창 닫힐 때 웹 카메라 해제
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec()