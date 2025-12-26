
import cv2
cap = cv2.VideoCapture(0)
print("isOpened:", cap.isOpened())
ret, frame = cap.read()
print("ret:", ret, "frame is None:", frame is None)
cap.release()
