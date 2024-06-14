import math

# license plate type classification helper function
def linear_equation(x1, y1, x2, y2):
    b = y1 - (y2 - y1) * x1 / (x2 - x1)
    a = (y1 - b) / x1
    return a, b

def check_point_linear(x, y, x1, y1, x2, y2):
    a, b = linear_equation(x1, y1, x2, y2)
    y_pred = a*x+b
    return(math.isclose(y_pred, y, abs_tol = 3))

# detect character and number in license plate
def read_plate(yolo_license_plate, image):
    LP_type = "1"
    license_plate = ""
    confidence = 0
    results = yolo_license_plate(image)
    text_list = results.pandas().xyxy[0].values.tolist()
    if len(text_list) == 0 or len(text_list) < 7 or len(text_list) > 10:
        return "unknown", confidence
    center_list = []
    y_mean = 0
    y_sum = 0
    for bb in text_list:
        x_center = (bb[0]+bb[2])/2
        y_center = (bb[1]+bb[3])/2
        y_sum += y_center
        center_list.append([x_center, y_center, bb[-1], bb[4]])
    y_mean = int(int(y_sum) / len(text_list))

    # find 2 point to draw line
    left_point = center_list[0]
    right_point = center_list[0]
    for cp in center_list:
        if cp[0] < left_point[0]:
            left_point = cp
        if cp[0] > right_point[0]:
            right_point = cp
    for ct in center_list:
        if left_point[0] != right_point[0]:
            if (check_point_linear(ct[0], ct[1], left_point[0], left_point[1], right_point[0], right_point[1]) == False):
                LP_type = "2"

    # 1 line plates and 2 line plates
    line_1 = []
    line_2 = []

    if LP_type == "2":
        for c in center_list:
            if int(c[1]) > y_mean:
                line_2.append(c)
            else:
                line_1.append(c)
        for text_1 in sorted(line_1, key = lambda x: x[0]):
            license_plate += str(text_1[2])
            confidence = (confidence + text_1[3])/2
        for text_2 in sorted(line_2, key = lambda x: x[0]):
            license_plate += str(text_2[2])
            confidence = (confidence + text_2[3])/2
    else:
        for text in sorted(center_list, key = lambda x: x[0]):
            license_plate += str(text[2])
            confidence = (confidence + text[3])/2
    return license_plate, confidence