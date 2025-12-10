import tkinter as tk
from PIL import Image, ImageTk


import process_data_v2
import glob
import os

DEFAULT_DIR = r'data_output/20251202' # should be temp but this is for testing
# DEFAULT_DIR = r'data_output/temp'

class DynamicImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Region Click Demo")

        image_dir = r'data_output/output_20251203_100902/annotated'
        process_data_v2.main(DEFAULT_DIR)

        self.images = []
        for image in process_data_v2.img_ann_grid:
            self.images.append((Image.open(image[0]), image[1], image[2]))
        self.grid_size = process_data_v2.grid_size

        # Track current image
        self.main_original = Image.open(process_data_v2.img_ann_stitched)
        self.current_original = self.main_original

        # Create canvas
        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bind resizing + clicking
        self.root.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.on_click)

        # Back button
        self.back_btn = tk.Button(root, text="Back", command=self.show_main)
        self.showing_main = True

    def resize_image_to_canvas(self, img):
        """Resize image while keeping aspect ratio."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w < 10 or canvas_h < 10:
            return None

        # Keep aspect ratio
        img_ratio = img.width / img.height
        canvas_ratio = canvas_w / canvas_h

        if img_ratio > canvas_ratio:
            new_w = canvas_w
            new_h = int(canvas_w / img_ratio)
        else:
            new_h = canvas_h
            new_w = int(canvas_h * img_ratio)

        self.image_w = new_w
        self.image_h = new_h
        
        self.offset_x = (canvas_w - new_w) // 2
        self.offset_y = (canvas_h - new_h) // 2
        
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        return ImageTk.PhotoImage(resized)

    def on_resize(self, event):
        self.display_image()

    def display_image(self):
        """Draw the current image resized to fit."""
        tk_img = self.resize_image_to_canvas(self.current_original)
        if not tk_img:
            return

        self.last_resized = tk_img  # keep reference
        self.canvas.delete("all")

        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            anchor="center",
            image=tk_img
        )

    def on_click(self, event):
        if not self.showing_main:
            return

        # adjust for centering
        adj_x = event.x - self.offset_x
        adj_y = event.y - self.offset_y

        # ignore clicks outside image
        if adj_x < 0 or adj_y < 0:
            return
        if adj_x >= self.image_w or adj_y >= self.image_h:
            return

        cell_width  = self.image_w  // self.grid_size[1]
        cell_height = self.image_h // self.grid_size[0]

        for filename, row, column in self.images:
            x0 = column * cell_width
            x1 = x0 + cell_width

            y0 = row * cell_height
            y1 = y0 + cell_height

            if x0 <= adj_x < x1 and y0 <= adj_y < y1:
                self.show_sub(filename)
                return

    def show_sub(self, img):
        self.current_original = img
        self.showing_main = False
        self.back_btn.pack()
        self.display_image()

    def show_main(self):
        self.current_original = self.main_original
        self.showing_main = True
        self.back_btn.pack_forget()
        self.display_image()


root = tk.Tk()
app = DynamicImageApp(root)
root.mainloop()