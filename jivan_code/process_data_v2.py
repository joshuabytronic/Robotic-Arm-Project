#!/usr/bin/env python3
"""
run_processing.py

Wrapper around your existing pipeline. Accepts <temp_dir> as argv[1].
Produces:
 - output_dir/ (contains raw/ annotated/ ...)
 - writes grid.json in the output_dir
 - prints the absolute output_dir path as the last stdout line (GUI reads this)
"""

import csv
from datetime import datetime
import os
import glob
import cv2
import shutil
import numpy as np
import sys
sys.path.append(os.path.abspath('..'))

# keep your imports (ensure these modules are importable from this location)
import smart_scan
import motionplanning
import pre_process_data
import json


class Defects:
    def __init__(self,csv_row):
        self.csv_row = csv_row
        self.timestamp = self.csv_row["Date Time"]
        self.read_csv_row()
        self.image_data = (self.timestamp, self.defects)

    def read_csv_row(self):
        self.defects = []
        defect_buffer = []

        # Loop through all columns *after* the first two
        for key in list(self.csv_row.keys())[1:]:
            val = self.csv_row[key].strip()
            val = None if val == "" else val

            defect_buffer.append(val)

            # Every 3 values = one defect (x, y, z)
            if len(defect_buffer) == 3:
                # If all 3 are None → ignore this defect
                if any(v is not None for v in defect_buffer):
                    self.defects.append(tuple(defect_buffer))
                defect_buffer = []


def annotate_img(img,defect):
    if defect[0] is not None and defect[1] is not None:
        coord = (int(float(defect[0])), int(float(defect[1])))
    else:
        coord = None
    if coord:
        cv2.circle(img, coord, 20, (0,0,255), 5)


def stitch_imgs(grid_size,img_grid,dest_dir):
    img_00 = cv2.imread(img_grid[0][0], cv2.IMREAD_UNCHANGED)
    if img_00 is None:
        raise RuntimeError("Could not read image for stitching: " + str(img_grid[0][0]))
    img_h, img_w = img_00.shape[0:2]
    num_r, num_c = grid_size
    img_tot_h = num_r * img_h
    img_tot_w = num_c * img_w

    if len(img_00.shape) == 2:  # grayscale
        img_stitch = np.zeros((num_r * img_h, num_c * img_w), dtype=img_00.dtype)
    else:  # multi-channel
        img_stitch = np.zeros((num_r * img_h, num_c * img_w, img_00.shape[2]), dtype=img_00.dtype)

    images = {}
    for img_path, r, c in img_grid:
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise RuntimeError("Could not read image for stitching: " + img_path)
        images[(r,c)] = img

    for (r, c), img in images.items():
        y1 = r * img_h
        y2 = y1 + img_h
        x1 = c * img_w
        x2 = x1 + img_w
        img_stitch[y1:y2, x1:x2] = img

    dest_path = os.path.join(dest_dir, "image_stitched.png")
    cv2.imwrite(dest_path, img_stitch)

    return img_stitch


def main(temp_dir):
    # if absolute paths are desired, make them absolute
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = os.path.abspath(temp_dir).replace("20251202", f"output_{timestamp}")
    os.makedirs(data_dir, exist_ok=True)

    image_defects = []
    csv_file = pre_process_data.main(temp_dir, data_dir, "copy")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_defect = Defects(row)
            image_defects.append(image_defect.image_data)

    # NOTE: you used both smart_scan.get_smart_coords() and motionplanning.get_surface_coords()
    # Keep existing behavior but be robust in case one of these functions fails.
    try:
        camera_coords = smart_scan.get_smart_coords()
    except Exception:
        camera_coords = []
    try:
        camera_coords = motionplanning.get_surface_coords()
    except Exception:
        pass

    camera_coords.sort(key = lambda x: x[1])
    xs = sorted({p[0] for p in camera_coords})
    ys = sorted({p[1] for p in camera_coords})
    num_rows = len(xs)
    num_cols = len(ys)
    if num_rows == 0 or num_cols == 0:
        # fallback: attempt to infer grid from number of images (square-ish)
        images_temp = glob.glob(os.path.join(os.path.abspath(temp_dir), "*.tiff"))
        n = max(1, len(images_temp))
        num_rows = int(np.ceil(np.sqrt(n)))
        num_cols = int(np.ceil(n / num_rows))

    grid_size = (num_rows, num_cols)
    num_imgs = num_cols * num_rows

    img_raw_dir = os.path.join(data_dir, "raw")
    img_ann_dir = os.path.abspath(img_raw_dir).replace("raw", "annotated")
    os.makedirs(img_ann_dir, exist_ok=True)

    for img in os.listdir(img_raw_dir):
        raw_path = os.path.join(img_raw_dir, img)
        ann_path = os.path.join(img_ann_dir, img)
        shutil.copy(raw_path, ann_path)

    images_ann = glob.glob(os.path.join(img_ann_dir, "*.tiff"))
    images_ann = sorted(images_ann)  # deterministic order

    img_ann_grid = []
    img_raw_grid = []

    # annotate + normalize each image
    for i in range(len(images_ann)):
        img_path = images_ann[i]
        img_32 = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        img_clean = np.nan_to_num(img_32, nan=0.0)
        low_val, high_val = -12.0, 1.0
        img_clipped = np.clip(img_32, low_val, high_val)
        img_8 = ((img_clipped - low_val) / (high_val - low_val) * 255).astype(np.uint8)
        # if image_defects shorter than images_ann, guard
        if i < len(image_defects):
            for defect in image_defects[i][1]:
                annotate_img(img_8, defect)

        img_8 = cv2.rotate(img_8, cv2.ROTATE_180)
        cv2.imwrite(img_path, img_8)

    # populate grid lists row/col wise
    index = 0
    for c in range(num_cols):
        for r in range(num_rows):
            if index < len(images_ann):
                abs_ann = os.path.abspath(images_ann[index])
                img_ann_grid.append((abs_ann, r, c))
                img_raw = os.path.abspath(images_ann[index]).replace("annotated", "raw")
                img_raw_grid.append((img_raw, r, c))
                index += 1

    # print mapping for debugging
    for i in range(len(img_ann_grid)):
        print(os.path.basename(img_ann_grid[i][0]), img_ann_grid[i][1], img_ann_grid[i][2])

    # create stitched image files
    img_ann_stitched = stitch_imgs(grid_size, img_ann_grid, img_ann_dir)
    img_raw_stitched = stitch_imgs(grid_size, img_raw_grid, img_raw_dir)

    # Create grid.json mapping file in data_dir (output directory)
    grid_entries = []
    for (abs_path, r, c) in img_ann_grid:
        grid_entries.append({
            "filename": os.path.basename(abs_path),
            "annotated_path": abs_path,
            "raw_path": os.path.abspath(abs_path).replace("annotated", "raw"),
            "grid_x": int(r),
            "grid_y": int(c)
        })

    grid_json_path = os.path.join(data_dir, "grid.json")
    with open(grid_json_path, "w", encoding="utf-8") as jf:
        json.dump({
            "grid_size": {"rows": int(grid_size[0]), "cols": int(grid_size[1])},
            "entries": grid_entries,
            "annotated_dir": img_ann_dir,
            "raw_dir": img_raw_dir
        }, jf, indent=2)

    # Print the output directory path as the last line (GUI will read this)
    print(data_dir)


if __name__ == "__main__":
    # accept input dir from argv[1]
    temp_dir = sys.argv[1]

    main(temp_dir)
