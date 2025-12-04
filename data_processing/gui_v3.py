import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import process_data_v2
import os

DEFAULT_DIR = r'data_output/20251202' # should be temp but this is for testing
# DEFAULT_DIR = r'data_output/temp'

class DynamicImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timet Surface Defect UI")
        root.iconbitmap("../I_logo.ico")

        self.directory = DEFAULT_DIR
        self.active_directory = DEFAULT_DIR
        
        self.show_annotations = False
        self.showing_main = True


        button_font = ("Arial", 12, "bold")
        style = ttk.Style()
        style.configure(
            "custom.TButton",
            font=("Arial", 12, "bold"))
        style.map(
            "custom.TButton",
            background=[("active", "#1976d2"), ("pressed", "#1565c0")],
            foreground=[("active", "white")]
        )

        self.top_bar = tk.Frame(root, bg="#ececec", height=40, relief="raised", bd=1)
        self.top_bar.pack(side="top", fill="x")
        
        self.folder_btn = ttk.Button(self.top_bar, text="Choose Directory", command=self.choose_directory, style="custom.TButton")
        self.folder_btn.pack(side="left", padx=5, pady=5)

        # Folder preview
        self.dir_label = tk.Label(self.top_bar, text=f"Current directory: {os.path.basename(self.active_directory)}", anchor="w", font=button_font, padx=15, pady=8)
        self.dir_label.pack(side="left", padx=10, pady=5)

        self.reload_btn = ttk.Button(self.top_bar, text="Reload", command=self.reload_directory, style="custom.TButton")
        self.reload_btn.pack(side="left", padx=5, pady=5)

        self.ann_btn = ttk.Button(self.top_bar, text="Show Annotations", command=self.toggle_annotations, style="custom.TButton")
        self.ann_btn.pack(side="right", padx=5, pady=5)

        self.home_btn = ttk.Button(self.top_bar, text="Home", command=self.show_main, style="custom.TButton")
        # Hidden initially
        self.home_btn.pack_forget()

        # Create canvas
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.98, relheight=0.9)


        # Bind resizing + clicking
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.on_click)

        self.load_directory(self.active_directory)

    
    def load_directory(self, directory):
        self.active_directory = directory
        self.dir_label.config(text=f"Current directory: {os.path.basename(self.active_directory)}")

        try:
            process_data_v2.main(directory)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process directory:\n{e}")
            return

        # if os.path.basename(directory) == "temp":
        #     directory = os.path.abspath(directory).replace("temp", "working")

        self.images = [
            (Image.open(path), row, col)
            for (path, row, col) in process_data_v2.img_unann_grid
        ]
        self.grid_size = process_data_v2.grid_size
        self.main_original = Image.open(process_data_v2.img_unann_stitched)
        self.current_original = self.main_original
        self.showing_main = True

        self.display_image()


    def resize_image_to_canvas(self, img):
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
        self.home_btn.pack(side="right", padx=5)
        self.display_image()

    def show_main(self):
        self.current_original = self.main_original
        self.showing_main = True
        self.home_btn.pack_forget()
        self.display_image()

    def choose_directory(self):
        initial_dir = os.path.dirname(self.active_directory)
        new_dir = filedialog.askdirectory(title="Select Image Directory", initialdir=initial_dir)
        self.active_directory = new_dir

        if not new_dir:
            return  # user cancelled

        self.directory = new_dir
        self.dir_label.config(text=f"Current directory: {os.path.basename(self.active_directory)}")

        # Try to run your processing script
        try:
            process_data_v2.main(new_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process directory:\n{e}")
            return

        # if os.path.basename(new_dir) == "temp":
        #     new_dir = os.path.abspath(new_dir).replace("temp", "working")

        # Rebuild images & grid
        self.images = [
            (Image.open(path), row, col)
            for (path, row, col) in process_data_v2.img_unann_grid
        ]
        self.grid_size = process_data_v2.grid_size

        # Update main stitched
        self.main_original = Image.open(process_data_v2.img_unann_stitched)
        self.current_original = self.main_original
        self.showing_main = True
        self.home_btn.pack_forget()
        self.display_image()

    def toggle_annotations(self):
        # Flip state
        self.show_annotations = not self.show_annotations

        # Update button text
        if self.show_annotations:
            self.ann_btn.config(text="Hide Annotations")

            grid = process_data_v2.img_ann_grid
            stitched = process_data_v2.img_ann_stitched
        else:
            self.ann_btn.config(text="Show Annotations")

            grid = process_data_v2.img_unann_grid
            stitched = process_data_v2.img_unann_stitched

        # Rebuild the image grid
        grid_map = {(row, col): path for (path, row, col) in grid}
        self.images = [(Image.open(path), row, col) for (path, row, col) in grid]
        self.grid_size = process_data_v2.grid_size

        if not self.showing_main:
            current_filename = os.path.basename(self.current_original.filename)
            self.main_original = Image.open(stitched)

            # Find matching row/col from previous grid
            for (path, row, col) in (process_data_v2.img_ann_grid +
                                    process_data_v2.img_unann_grid):
                if os.path.basename(path) == current_filename:
                    # Load the corresponding annotated/unannotated version
                    new_path = grid_map[(row, col)]
                    self.current_original = Image.open(new_path)
                    break
        else:
            self.main_original = Image.open(stitched)
            self.current_original = self.main_original
        self.display_image()


    def reload_directory(self):
        current_dir = self.active_directory
        if not current_dir or not os.path.isdir(current_dir):
            messagebox.showerror("Error", "No valid directory loaded to reload.")
            return

        # Re-run processing
        try:
            process_data_v2.main(current_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Reload failed:\n{e}")
            return

        # if os.path.basename(current_dir) == "temp":
        #     current_dir = os.path.abspath(current_dir).replace("temp", "working")

        # Force annotations OFF
        self.show_annotations = False
        self.ann_btn.config(text="Show Annotations")

        # Use unannotated grid & stitched image
        grid = process_data_v2.img_unann_grid
        stitched = process_data_v2.img_unann_stitched

        # Rebuild image grid
        self.images = [
            (Image.open(path), row, col)
            for (path, row, col) in grid
        ]
        self.grid_size = process_data_v2.grid_size

        # Reset main stitched image
        self.main_original = Image.open(stitched)
        self.current_original = self.main_original
        self.showing_main = True

        # Hide back button if visible
        self.home_btn.pack_forget()

        # Redraw canvas
        self.display_image()


    def load_default(self):
        process_data_v2.main(DEFAULT_DIR)
        self.refresh_from_processed()


    def refresh_from_processed(self):
        self.images = [(Image.open(path), row, col) for (path, row, col) in process_data_v2.img_unann_grid]
        self.grid_size = process_data_v2.grid_size
        self.main_original = Image.open(process_data_v2.img_unann_stitched)
        self.current_original = self.main_original
        self.showing_main = True
        self.home_btn.pack_forget()
        self.display_image()


# root = tk.Tk()
root = ttk.Window(themename="darkly")
root.geometry("1200x900")
app = DynamicImageApp(root)
root.mainloop()