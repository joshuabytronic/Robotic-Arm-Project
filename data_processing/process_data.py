import csv
from datetime import datetime
import os
import glob
import cv2
import shutil
import numpy as np
import sys
sys.path.append(os.path.abspath('..'))
import motionplanning
import pre_process_data
import Camera

temp_dir = r'data_output/20251202'

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


def get_camera_coords():
    surface_camera = Camera.surface_control
    sheet_dimensions = motionplanning.sheet_dimensions
    camera_offset = surface_camera.camera_offset
    scan_area = surface_camera.scan_area
    camera_coords = motionplanning.get_surface_coords(sheet_dimensions, scan_area, camera_offset)
    # for motionplanning, provide: sheet_dimensions, scan_area, offset
    #   - sheet_dimensions comes directly from motionplanning
    #   - scan_area comes from camera.scan_area
    #   - offset comes from camera.offset
    return camera_coords


def annotate_img(img,defect):
    if defect[0] is not None and defect[1] is not None:
        coord = (int(float(defect[0])), int(float(defect[1])))
    else:
        coord = None
    if coord:
        cv2.circle(img, coord, 20, (0,0,255), 5)

def stitch_imgs(grid_size,img_grid,dest_dir):
    img_00 = cv2.imread(img_grid[0][0], cv2.IMREAD_UNCHANGED)
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
        # print(r,c)
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = os.path.abspath(temp_dir).replace("20251202", f"output_{timestamp}")
    os.makedirs(data_dir, exist_ok=True)
    # data_dir = os.path.abspath(temp_dir).replace("temp", "working")
    
    image_defects = []
    csv_file = pre_process_data.main(temp_dir, data_dir, "copy")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            image_defect = Defects(row)
            image_defects.append(image_defect.image_data)

    
    # camera_coords = smart_scan.get_smart_coords()
    # camera_coords = motionplanning.get_surface_coords()
    camera_coords = get_camera_coords()
    camera_coords.sort(key = lambda x: x[1])
    print(camera_coords)
    xs = sorted({p[0] for p in camera_coords})
    ys = sorted({p[1] for p in camera_coords})
    print(xs)
    print(ys)
    num_rows = len(xs)
    num_cols = len(ys)
    print(num_rows, num_cols)
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
    # images_ann = sorted(images_ann)

    img_ann_grid = []
    img_raw_grid = []

    for i in range(len(images_ann)):
        img_32 = cv2.imread(images_ann[i], cv2.IMREAD_UNCHANGED)
        img_clean = np.nan_to_num(img_32, nan=0.0)
        # print("img_32 val ", img_32[0][0])
        # print("img_clean val ", img_clean[0][0])
        # img_8 = cv2.normalize(img_clean, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")
        low_val, high_val = -12.0, 1.0
        img_clipped = np.clip(img_32, low_val, high_val)
        img_8 = ((img_clipped - low_val) / (high_val - low_val) * 255).astype(np.uint8)
        for defect in image_defects[i][1]:
            annotate_img(img_8, defect)
        
        img_8 = cv2.rotate(img_8, cv2.ROTATE_180)
        cv2.imwrite(images_ann[i], img_8)
        # cv2.imshow("image", img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows() 

    index = 0
    for c in range(num_cols):
        for r in range(num_rows):
            if index < len(images_ann):
                img_ann_grid.append((images_ann[index], r, c))
                img_raw = os.path.abspath(images_ann[index]).replace("annotated", "raw")
                img_raw_grid.append((img_raw, r, c))
                index += 1

    for i in range(len(img_ann_grid)):
        print(os.path.basename(img_ann_grid[i][0]), img_ann_grid[i][1], img_ann_grid[i][2])
    img_ann_stitched = stitch_imgs(grid_size, img_ann_grid, img_ann_dir)
    img_raw_stitched = stitch_imgs(grid_size, img_raw_grid, img_raw_dir)


if __name__ == "__main__":
    main(temp_dir)

    # for r in scan_records:
    #     print(r)
