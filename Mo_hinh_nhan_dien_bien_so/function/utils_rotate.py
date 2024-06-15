import numpy as np
import math
import cv2

# Tăng độ tương phản hình ảnh sử dụng CLAHE (Contrast Limited Adaptive Histogram Equalization)
def changeContrast(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    luminance, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(luminance)
    limg = cv2.merge((cl, a, b))
    enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced_img

# Hàm xoay hình ảnh
def rotate_image(image, angle):
    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result

# Tính toán góc xoay của hình ảnh
def compute_skew(src_img, center_thres):
    if len(src_img.shape) == 3:  # Kiểm tra nếu ảnh là ảnh màu (3 kênh màu)
        h, w, _ = src_img.shape
    elif len(src_img.shape) == 2:  # Kiểm tra nếu ảnh là ảnh xám (3 kênh màu)
        h, w = src_img.shape
    else:
        print("Loại hình ảnh không được hỗ trợ")
    img = cv2.medianBlur(src_img, 3)  # Áp dụng bộ lọc trung vị để giảm nhiễu
    edges = cv2.Canny(img, threshold1=30, threshold2=100, apertureSize=3, L2gradient=True)  # Phát hiện cạnh sử dụng thuật toán Canny
    # Phát hiện đường thẳng cạnh sử dụng thuật toán Hough transform
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, 30, minLineLength=w / 1.5, maxLineGap=h / 3.0)
    if lines is None:
        return 1  # Nếu không có đường thẳng nào được phát hiện, trả về 1 để chỉ thị thất bại

    min_line = 100
    min_line_pos = 0
    # Tìm đường thẳng gần trung tâm của ảnh nhất
    for i in range(len(lines)):
        for x1, y1, x2, y2 in lines[i]:
            center_point = [((x1 + x2) / 2), ((y1 + y2) / 2)]  # Tính toán điểm trung tâm của đường thẳng
            if center_thres == 1:  # Kiểm tra nếu ngưỡng trung tâm được bật
                if center_point[1] < 7:  # Nếu điểm trung tâm quá gần đỉnh của ảnh, bỏ qua
                    continue
            if center_point[1] < min_line:
                min_line = center_point[1]
                min_line_pos = i

    angle = 0.0
    nlines = lines.size
    cnt = 0
    # Tính toán góc trung bình của các đường thẳng gần trung tâm được phát hiện
    for x1, y1, x2, y2 in lines[min_line_pos]:
        ang = np.arctan2(y2 - y1, x2 - x1)
        if math.fabs(ang) <= 30:  # Loại bỏ các góc xoay quá lớn
            angle += ang
            cnt += 1
    if cnt == 0:
        return 0.0
    return (angle / cnt) * 180 / math.pi

# Xoay hình ảnh dựa trên góc xoay
def deskew(src_img, change_cons, center_thres):
    if change_cons == 1:  # Kiểm tra nếu là 1 thì áp dụng tăng độ tương phải
        return rotate_image(src_img, compute_skew(changeContrast(src_img), center_thres))
    else:
        return rotate_image(src_img, compute_skew(src_img, center_thres))