import cv2
import torch
import sqlalchemy
import function.utils_rotate as utils_rotate
import function.helper as helper
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from sqlalchemy import Boolean, DateTime, Integer, LargeBinary
from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base
from flask import Flask, render_template
import serial


# Define the database URL
#db_url = 'mysql://ulxn85vhqppynkyr:zEkEO66wKdpoiTZLwcJo@brtmsyfrdxo3ucwbxjmx-mysql.services.clever-cloud.com:3306/brtmsyfrdxo3ucwbxjmx'
db_url = 'mysql://root:@192.168.63.40:3306/parkpal'

# Create the SQLAlchemy engine
engine = create_engine(db_url)

# Create a sessionmaker
Session = sessionmaker(bind=engine)

# Create a base class for declarative class definitions
Base = sqlalchemy.orm.declarative_base()

    


class car_plates(Base):
    __tablename__ = 'car_plates'  # Specify the table name
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    plate_number = Column(String(50), nullable=False)
    
class parking(Base):
    __tablename__ = 'parking'  # Specify the table name
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    id_user = Column(Integer, nullable=False)
    car_number = Column(String(50), nullable=False)
    time_in = Column(DateTime, nullable=True)
    time_out = Column(DateTime, nullable=True)
    image_in = Column(LargeBinary, nullable=True)
    image_out = Column(LargeBinary, nullable=True)

yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.5

roi_top_left1 = (0, 420)
roi_bottom_right1 = (640, 480)
license_plate_counts = {}
count = 0

# Kết nối đến webcam
vid = cv2.VideoCapture("http://192.168.63.250:81/stream")
#arduino = serial.Serial('COM6', 38400) # Adjust the port as needed
running=False
# Đọc và hiển thị khung hình từ webcam
while True:
    ret, frame = vid.read()
    plates = yolo_LP_detect(frame, size=640)
    list_plates = plates.pandas().xyxy[0].values.tolist()
    for plate in list_plates:
        flag = 0
        x = int(plate[0]) # xmin
        y = int(plate[1]) # ymin
        w = int(plate[2] - plate[0]) # xmax - xmin
        h = int(plate[3] - plate[1]) # ymax - ymin
        cv2.rectangle(frame, (int(x), int(y)), (int(x) + int(w), int(y) + int(h)), color = (0,0,225), thickness = 2)
        if (x >= roi_top_left1[0] and y + h >= roi_top_left1[1] and x + w <= roi_bottom_right1[0] and y + h <= roi_bottom_right1[1]):
            running = True
        if running==True:
            crop_img = frame[y:y+h, x:x+w]
            cv2.rectangle(frame, (int(plate[0]),int(plate[1])), (int(plate[2]),int(plate[3])), color = (0,0,225), thickness = 2)
            cv2.imwrite("result/img1.jpg", crop_img)
            rc_image = cv2.imread("result/img1.jpg")
            lp = ""
            for cc in range(0, 2):
                for ct in range(0, 2):
                    lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                    if lp != ('unknown',):
                        count += 1
                        if lp in license_plate_counts:
                            license_plate_counts[lp] += 1
                        else:
                            license_plate_counts[lp] = 1
                        cv2.putText(frame, f"{lp}", (int(plate[0]), int(plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                        flag = 1
                        break
                if flag == 1:
                    break
            if count >= 50:
                with open('result/img1.jpg', 'rb') as file:
                    image_data = file.read()
                last_lp = max(license_plate_counts, key=license_plate_counts.get)
                print(last_lp)
                license_plate_counts.clear()
                count = 0
                running = False
                
                # DÀNH CHO CAM VÀO
                # Create a session
                session = Session()
                
                co_ton_tai_bien_so = session.query(car_plates).filter_by(plate_number=last_lp).first()
                
                da_co_trong_bang_do_xe_chua = session.query(parking).filter_by(car_number=last_lp).filter(parking.time_out.is_(None)).first()
                
                if co_ton_tai_bien_so and da_co_trong_bang_do_xe_chua:
                    print('Xe nay dang o trong bai')
                    
                if co_ton_tai_bien_so and not da_co_trong_bang_do_xe_chua:
                    # Mở rào chắn lên
                    print('Xe nay chua o trong bai -> Se mo barrier')
                    # Thêm biển số vào bảng do_xe
                    id_tk = co_ton_tai_bien_so.user_id
                    new_parking = parking(id_user=id_tk, car_number=last_lp, time_in=datetime.utcnow() + timedelta(hours=7),image_in=image_data)

                    session.add(new_parking)
                    session.commit()
                    session.close()
                    #arduino.write(b'1')

    # Hiển thị khung hình
    cv2.rectangle(frame, roi_top_left1, roi_bottom_right1, color=(0, 255, 0), thickness=2)
    cv2.imshow('Cam vao', frame)
    
    # Dừng vòng lặp nếu nhấn phím 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên và đóng cửa sổ
vid.release()
cv2.destroyAllWindows()