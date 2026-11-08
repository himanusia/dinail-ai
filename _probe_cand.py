
import cv2, sys, math, numpy as np
sys.path.insert(0,".")
from dinail_ai import detect

img = cv2.imread("fixtures/real_hand_coin.jpg")
small = detect.resize_for_detection(img)
gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
gray = cv2.medianBlur(gray, 5)
h,w = gray.shape
for p2 in (34, 30, 26):
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min(h,w)*0.25,
                               param1=110, param2=p2, minRadius=int(min(h,w)*0.035), maxRadius=int(min(h,w)*0.5))
    n = 0 if circles is None else len(circles[0])
    print("param2", p2, "kandidat", n)
    if circles is None: continue
    mag = detect.gradient_mag(gray)
    for cx, cy, r in np.round(circles[0],1)[:8]:
        cx2, cy2, r2 = detect.refine_circle(mag, float(cx), float(cy), float(r))
        e = detect.edge_support(mag, cx2, cy2, r2); c = detect.contrast(gray, cx2, cy2, r2)
        print(f"   ({cx2:7.1f},{cy2:7.1f}) r={r2:6.1f} edge={e:.2f} con={c:.2f} score={0.65*e+0.35*c:.3f}")
