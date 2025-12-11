import csv
from datetime import datetime
import os
import glob
import cv2
import shutil
from cv2.gapi.streaming import timestamp
import numpy as np
import sys
sys.path.append(os.path.abspath('..'))
import smart_scan
import motionplanning
import pre_process_data
import Camera

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
    return sheet_dimensions, camera_coords

def get_grid_info(camera_coords):
    xs = sorted({p[0] for p in camera_coords})
    ys = sorted({p[1] for p in camera_coords})
    num_rows = len(xs)
    num_cols = len(ys)
    grid_size = (num_rows, num_cols)
    return grid_size, num_rows, num_cols, (xs, ys)

def create_save_dir(input_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.basename(input_dir) == "temp":
        data_dir = os.path.abspath(input_dir).replace("temp", "working")
    else:
        data_dir_parent = os.path.join(os.path.dirname(os.path.abspath(input_dir)), "saved")
        data_dir = os.path.join(data_dir_parent, os.path.basename(input_dir)+f"_output_{timestamp}")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class Defects:
    def __init__(self,csv_file):
        self.csv_file = csv_file
        
        self.image_data = []

        self.read_csv()

    def read_csv(self):
        with open(self.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp, image_defects = self.read_csv_row(row)
                self.image_data.append((timestamp, image_defects))

    def read_csv_row(self, row):
        image_timestamp = row["Date Time"]
        defects = []
        defect_buffer = []

        # Loop through all columns *after* the first
        for key in list(row.keys())[1:]:
            val = row[key].strip()
            val = None if val == "" else val

            defect_buffer.append(val)

            # Every 3 values = one defect (x, y, z)
            if len(defect_buffer) == 3:
                # If all 3 are None → ignore this defect
                if any(v is not None for v in defect_buffer):
                    defects.append(tuple(defect_buffer))
                defect_buffer = []
        return image_timestamp, defects


class ConvertImages:
    def __init__(self, raw_dir, exp_type, csv_file=None):
        self.raw_dir = raw_dir
        self.exp_type = exp_type
        
        if self.exp_type == "annotated":
            self.csv_file = csv_file
            defects = Defects(self.csv_file)
            self.image_defects = defects.image_data

        self.create_exp_dir()
        self.convert_iamges()
 
    def create_exp_dir(self):
        self.exp_dir = os.path.abspath(self.raw_dir).replace("raw", self.exp_type)
        os.makedirs(self.exp_dir, exist_ok=True)

        for img in os.listdir(self.raw_dir):
            self.raw_path = os.path.join(self.raw_dir, img)
            self.exp_path = os.path.join(self.exp_dir, img)
            shutil.copy(self.raw_path, self.exp_path)

    def get_col_range(self):
        mins = []
        maxs = []
        for img in self.conv_images:
            img_32 = cv2.imread(img, cv2.IMREAD_UNCHANGED)
            img_32 = np.nan_to_num(img_32, nan=np.nanmin(img_32))
            mins.append(np.min(img_32))
            maxs.append(np.max(img_32))
        min_mean = np.mean(mins)
        max_mean = np.mean(maxs)
                   
        self.col_range = (min_mean, max_mean)
        self.col_range = (-10.0, 0.0)
        self.col_range = (-20.0, 30.0)

    def bit16_to_bit8_col(self, img_32, range=None, color=True):
        if not range:
            img_8 = cv2.normalize(img_32, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        else:
            img_thresh = np.clip(img_32, range[0], range[1])
            img_8 = ((img_thresh - range[0]) / (range[1] - range[0]) * 255).astype(np.uint8)
        if color:
            img_8_col = cv2.applyColorMap(img_8, cv2.COLORMAP_JET)
        else:
            img_8_col = cv2.cvtColor(img_8, cv2.COLOR_GRAY2RGB)
        return img_8_col

    def convert_iamges(self):
        self.conv_images = glob.glob(os.path.join(self.exp_dir, "*.tiff"))
        self.get_col_range()
        for i in range(len(self.conv_images)):
            img_32 = cv2.imread(self.conv_images[i], cv2.IMREAD_UNCHANGED)
            # img_32 = np.nan_to_num(img_32, nan=0)
            # img_32 = np.nan_to_num(img_32, nan=np.nanmin(img_32))
            img_8 = self.bit16_to_bit8_col(img_32, range=self.col_range, color=False)# range=self.col_range)

            if self.exp_type == "annotated":
                for defect in self.image_defects[i][1]:
                    self.annotate_img(img_8, defect)

            # print(i)
            # if (i + 1) % 5 != 0:
            #     img_8 = cv2.rotate(img_8, cv2.ROTATE_180)
            # else:
            #     # print("True")
            #     img_8 = cv2.flip(img_8, 1)
            # img_8 = cv2.rotate(img_8, cv2.ROTATE_180)
            cv2.imwrite(self.conv_images[i], img_8)


    def annotate_img(self,img,defect):
        h, w = img.shape[:2]
        if defect[0] is not None and defect[1] is not None:
            coord = (int(w-float(defect[0])), int(h-float(defect[1])))
        else:
            coord = None
        if coord:
            cv2.circle(img, coord, 20, (0,0,255), 5)

def get_img_grid(grid_size, images):
    img_grid = []
    index = 0
    for c in range(grid_size[1]):
        for r in range(grid_size[0]):
            if index < len(images):
                img_grid.append((images[index], r, c))
                index += 1
    return img_grid

def resize_with_crop_or_pad(img, target_w, target_h):
    h, w = img.shape[:2]

    # ---- CROP IF TOO LARGE ----
    # Crop height
    if h > target_h:
        extra = h - target_h
        top = extra // 2
        bottom = h - (extra - top)
        img = img[top:bottom, :]
        h = target_h

    # Crop width
    if w > target_w:
        extra = w - target_w
        left = extra // 2
        right = w - (extra - left)
        img = img[:, left:right]
        w = target_w

    # ---- PAD IF TOO SMALL ----
    delta_h = target_h - h
    delta_w = target_w - w

    top = delta_h // 2
    bottom = delta_h - top
    left = delta_w // 2
    right = delta_w - left

    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=0)

    return img

def stitch_imgs(grid_size, img_grid, img_dir):
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
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        img = resize_with_crop_or_pad(img, img_w, img_h)
        images[(r,c)] = img

    for (r, c), img in images.items():
        y1 = r * img_h
        y2 = y1 + img_h
        x1 = c * img_w
        x2 = x1 + img_w
        img_stitch[y1:y2, x1:x2] = img

    dest_path = os.path.join(img_dir, "image_stitched.png")
    cv2.imwrite(dest_path, img_stitch)

    return dest_path


def main(input_dir):
    global sheet_dimensions
    global camera_grid
    global grid_size
    global img_raw_grid
    global img_unann_grid
    global img_ann_grid
    global img_raw_stitched
    global img_unann_stitched
    global img_ann_stitched

    data_dir = create_save_dir(input_dir)
    
    sheet_dimensions, camera_coords = get_camera_coords()
    camera_coords.sort(key = lambda x: x[1])
    grid_size, num_rows, num_cols, camera_grid = get_grid_info(camera_coords)

    if os.path.basename(input_dir) == "temp":
        csv_file = pre_process_data.main(input_dir, data_dir, "move")
    else:
        csv_file = pre_process_data.main(input_dir, data_dir, "copy")
    img_raw_dir = os.path.join(data_dir, "raw")
    unannotated_images = ConvertImages(img_raw_dir, "unannotated")
    if csv_file:
        annotated_images = ConvertImages(img_raw_dir, "annotated", csv_file=csv_file)
    else:
        annotated_images = unannotated_images

    images_raw = glob.glob(os.path.join(img_raw_dir, "*.tiff"))

    img_raw_grid = get_img_grid(grid_size, images_raw)
    img_unann_grid = get_img_grid(grid_size, unannotated_images.conv_images)
    img_ann_grid = get_img_grid(grid_size, annotated_images.conv_images)

    img_raw_stitched = stitch_imgs(grid_size, img_raw_grid, img_raw_dir)
    img_unann_stitched = stitch_imgs(grid_size, img_unann_grid, unannotated_images.exp_dir)
    img_ann_stitched = stitch_imgs(grid_size, img_ann_grid, annotated_images.exp_dir)

