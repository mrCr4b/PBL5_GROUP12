import numpy as np
import math
import cv2

# Function to enhance the contrast of an image using CLAHE (Contrast Limited Adaptive Histogram Equalization)
def changeContrast(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    limg = cv2.merge((cl, a, b))
    enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced_img

# Function to rotate an image by a given angle
def rotate_image(image, angle):
    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result

# Function to compute the skew angle of an image
def compute_skew(src_img, center_thres):
    if len(src_img.shape) == 3:  # Check if the image is color (3 channels)
        h, w, _ = src_img.shape
    elif len(src_img.shape) == 2:  # Check if the image is grayscale (1 channel)
        h, w = src_img.shape
    else:
        print('Unsupported image type')
    img = cv2.medianBlur(src_img, 3)  # Apply median blur to reduce noise
    edges = cv2.Canny(img, threshold1=30, threshold2=100, apertureSize=3, L2gradient=True)  # Detect edges using Canny edge detector
    # Detect lines using Hough transform
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, 30, minLineLength=w / 1.5, maxLineGap=h / 3.0)
    if lines is None:
        return 1  # If no lines are detected, return 1 as an indication of failure

    min_line = 100
    min_line_pos = 0
    # Find the line closest to the center of the image
    for i in range(len(lines)):
        for x1, y1, x2, y2 in lines[i]:
            center_point = [((x1 + x2) / 2), ((y1 + y2) / 2)]  # Calculate center point of the line
            if center_thres == 1:  # Check if center thresholding is enabled
                if center_point[1] < 7:  # If the center point is too close to the top, skip
                    continue
            if center_point[1] < min_line:
                min_line = center_point[1]
                min_line_pos = i

    angle = 0.0
    nlines = lines.size
    cnt = 0
    # Calculate the average angle of lines close to the detected line
    for x1, y1, x2, y2 in lines[min_line_pos]:
        ang = np.arctan2(y2 - y1, x2 - x1)
        if math.fabs(ang) <= 30:  # Exclude extreme rotations
            angle += ang
            cnt += 1
    if cnt == 0:
        return 0.0
    return (angle / cnt) * 180 / math.pi

# Function to deskew an image based on its skew angle
def deskew(src_img, change_cons, center_thres):
    if change_cons == 1:  # Check if contrast enhancement is enabled
        return rotate_image(src_img, compute_skew(changeContrast(src_img), center_thres))  # Deskew with contrast-enhanced image
    else:
        return rotate_image(src_img, compute_skew(src_img, center_thres))  # Deskew without contrast enhancement
