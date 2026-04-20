import os
import torch
import torch.nn.functional as F
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms
from ultralytics import YOLO

from model import DigitCNN
from utils import (
    warp_plate,
    order_points,
    expand_points,
    preprocess_for_ocr,
    split_digits_simple
)

device = torch.device("cpu")

yolo_model = YOLO(os.path.join("models", "yolo.pt"))

model = DigitCNN().to(device)
model.load_state_dict(torch.load(
    os.path.join("models", "digit_classifier.pth"),
    map_location=device
))
model.eval()

inference_transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5])
])

def predict_digit(model, img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)

    img = inference_transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img)
        probs = F.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)

    return int(pred.item()), float(conf.item())

def process_image(image_path):

    results = yolo_model.predict(image_path, save=False, verbose=False)
    r = results[0]

    img = r.orig_img

    if r.keypoints is None or len(r.keypoints.xy) == 0 or r.boxes is None:
        return "", "!пересмотр", 0

    if len(r.boxes) > 1:
        boxes = r.boxes.xyxy.cpu().numpy()
        areas = [(x2-x1)*(y2-y1) for x1,y1,x2,y2 in boxes]

        max_area = max(areas)
        filtered = [i for i,a in enumerate(areas) if a > 0.5*max_area]

        best_idx = max(filtered, key=lambda i: areas[i]) if filtered else np.argmax(areas)
    else:
        best_idx = 0

    yolo_conf = float(r.boxes.conf[best_idx].cpu().numpy())

    if yolo_conf < 0.5:
        return "", "!пересмотр", 0

    kpts = r.keypoints.xy[best_idx].cpu().numpy()
    kpts = expand_points(order_points(kpts))

    warped = warp_plate(img, kpts)
    if warped is None:
        return "", "!пересмотр", 0

    prep = preprocess_for_ocr(warped)

    h = prep.shape[0]
    prep = prep[:int(h * 0.95), :]

    digits = split_digits_simple(prep)

    if len(digits) == 0:
        return "", "!пересмотр", 0

    valid_digits = []
    for d in digits:
        h_d, w_d = d.shape[:2]
        ratio = w_d / h_d
        if 0.15 < ratio < 1.5:
            valid_digits.append(d)

    digits = valid_digits

    if len(digits) == 0 or len(digits) > 6:
        return "", "!пересмотр", 0

    if len(digits) > 4:
        digits = digits[:4]

    digit_preds = []

    for d in digits:
        h_d, w_d = d.shape[:2]

        if h_d*w_d < 300 or w_d < 10 or h_d < 10:
            continue

        if np.mean(d) > 240:
            continue

        pred, conf = predict_digit(model, d)
        digit_preds.append((pred, conf))

    if len(digit_preds) == 0:
        return "", "!пересмотр", 0

    number = "".join([str(p[0]) for p in digit_preds]).zfill(4)

    cls_conf = min([p[1] for p in digit_preds])

    if cls_conf >= 0.98:
        status = "отлично"
    elif cls_conf >= 0.85:
        status = "!не уверена"
    else:
        status = "!пересмотр"

    return number, status, cls_conf