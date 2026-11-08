
import cv2, json, sys
sys.path.insert(0,".")
from dinail_ai.detect import detect_coin
from dinail_ai.analyze import analyze
for f in ["fixtures/real_hand_coin.jpg","fixtures/real_hand_ruler.jpg"]:
    img = cv2.imread(f)
    best, cands = detect_coin(img)
    print(f, img.shape, "->", None if not best else (round(best.cx,1), round(best.cy,1), round(best.r,1), round(best.score,3)))
    if best:
        r = analyze(open(f,"rb").read(), coin="500")
        print("   quality:", r.quality["pass"], r.quality["reasons"][:2], "scale:", r.scale_px_per_mm)
