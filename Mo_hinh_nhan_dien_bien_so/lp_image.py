import cv2
import torch
import function.utils_rotate as utils_rotate
import os
import function.helper as helper

yolo_LP_detect = torch.hub.load('cam_ra', 'custom', path='model/license_plate.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load('cam_ra', 'custom', path='model/letters.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.5

while True:
    file_name = input("Mời nhập tên file test (hoặc nhập 'exit' để thoát): ")
    if file_name.lower() == 'exit':
        break
    file_path = os.path.join("test_image", file_name)
    if not os.path.exists(file_path):
        print("File không tồn tại. Vui lòng kiểm tra lại.")
        continue
    img = cv2.imread(file_path)
    plates = yolo_LP_detect(img, size=640)
    list_plates = plates.pandas().xyxy[0].values.tolist()
    if len(list_plates) == 0:
        print("Không thấy gì cả")
    else:
        for plate in list_plates:
            flag = 0
            x = int(plate[0]) # xmin
            y = int(plate[1]) # ymin
            w = int(plate[2] - plate[0]) # xmax - xmin
            h = int(plate[3] - plate[1]) # ymax - ymin 
            crop_img = img[y:y+h, x:x+w]
            cv2.rectangle(img, (int(plate[0]),int(plate[1])), (int(plate[2]),int(plate[3])), color = (0,0,225), thickness = 2)
            lp = ""
            for cc in range(0,2):
                for ct in range(0,2):
                    lp, confidence = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                    if lp != "unknown":
                        cv2.imwrite("result/img.jpg", crop_img)
                        confidence = round(confidence * 100,1)
                        print(f"License Plate Found: {lp}")
                        print(f"Tỷ lệ chính xác: {confidence}%")
                        cv2.putText(img, f"{lp}", (int(plate[0]), int(plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                        flag = 1
                        break
                if flag == 1:
                    break
    cv2.imshow(file_name, img)
    cv2.waitKey()
    cv2.destroyAllWindows()
