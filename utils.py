import cv2
import numpy as np

def warp_plate(image, pts):
    pts = np.array(pts, dtype="float32")

    (tl, tr, br, bl) = pts

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    if maxWidth < 10 or maxHeight < 10:
        return None

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    return warped

def order_points(pts):
    pts = np.array(pts)

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    top_left = pts[np.argmin(s)]
    bottom_right = pts[np.argmax(s)]
    top_right = pts[np.argmin(diff)]
    bottom_left = pts[np.argmax(diff)]

    return np.array([top_left, top_right, bottom_right, bottom_left])


def expand_points(pts, scale=1.15):  
    center = np.mean(pts, axis=0)
    expanded = (pts - center) * scale + center
    return expanded

def preprocess_for_ocr(img):
    return cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

def split_digits_simple(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    projection = np.sum(thresh, axis=0)
    projection = projection / (np.max(projection) + 1e-6)

    mask = projection > 0.1

    splits = []
    start = None

    for i, val in enumerate(mask):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start > 8:  
                splits.append(img[:, start:i])
            start = None

    if start is not None:
        splits.append(img[:, start:])

    if len(splits) == 0:
        splits = [img]

    return splits
