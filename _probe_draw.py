
import cv2, sys
sys.path.insert(0,".")
from dinail_ai.detect import detect_coin
img = cv2.imread("fixtures/real_hand_coin.jpg")
best,_ = detect_coin(img)
out = img.copy()
cv2.circle(out, (int(best.cx), int(best.cy)), int(best.r), (0,255,0), 5)
cv2.imwrite("/tmp/real_detect.jpg", out)
print("ok", best.cx, best.cy, best.r)
