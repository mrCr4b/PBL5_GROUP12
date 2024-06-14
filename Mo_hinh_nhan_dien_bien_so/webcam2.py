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
import requests

#BASE = "http://127.0.0.1:5000/"
BASE = "http://192.168.63.40:5003/"


yolo_LP_detect = torch.hub.load('cam_ra', 'custom', path='model/license_plate.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load('cam_ra', 'custom', path='model/letters.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.5

# Kết nối đến webcam
vid = cv2.VideoCapture("http://192.168.63.145:81/stream")
arduino = serial.Serial('COM6', 38400) # Adjust the port as needed
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
        crop_img = frame[y:y+h, x:x+w]
        lp = {}
        for cc in range(0, 2):
            for ct in range(0, 2):
                lp, confidence = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                if lp != "unknown":
                    confidence = round(confidence * 100,1)
                    cv2.imwrite("result/img1.jpg", crop_img)
                    with open('result/img2.jpg', 'rb') as file:
                        image_data = file.read()
                    print(lp, confidence)
                    # DÀNH CHO CAM RA
                    payload = {
                        'bien_so': lp
                    }
                    #files = {'image': hinh_anh}
                    files = {'image': ('img2.jpg', image_data, 'image/jpeg')}
            
                    response = requests.post(BASE + "camra", data=payload, files=files)
                    response_data = response.json()
                    
                    if response_data is not None and 'ket_qua' in response_data:
                        kq = response_data['ket_qua']
                        if kq == 'xe_ra_khoi_bai_thanh_cong':
                            # Mở rào chắn lên 
                            print('Xe nay se ra khoi bai -> Se mo barrier')
                            arduino.write(b'1')
                    cv2.putText(frame, f"{lp}", (int(plate[0]), int(plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,225), 2)
                    cv2.putText(frame, f"{confidence}%", (int(plate[0]), int(plate[1]-46)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,225), 2)
                    flag = 1
                    break
            if flag == 1:
                break
    # Hiển thị khung hình
    cv2.imshow('Cam ra', frame)
    
    # Dừng vòng lặp nếu nhấn phím 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên và đóng cửa sổ
vid.release()
cv2.destroyAllWindows()