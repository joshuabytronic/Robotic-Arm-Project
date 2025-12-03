#!/usr/bin/env python3
import os
import subprocess
import json
import tkinter as tk
from PIL import Image, ImageTk

# ---------- CONFIG ----------
PROCESSING_SCRIPT = "process_data_v2.py"   # script that creates output_dir and grid.json
INPUT_DIR = "data_output/20251202"        # default input directory (override via command line if desired)
# -----------------------------

class StitchedViewer:
    def __init__(self, root, input_dir=INPUT_DIR):
        self.root = root
        self.root.title("Stitched Image Viewer")
        self.input_dir = input_dir
        self.output_dir = None
        self.grid_meta = None
        self.stitched_img_path = None
        self.tk_stitched = None
        self.pil_stitched = None

        # Canvas to display stitched image
        self.canvas = tk.Canvas(root, highlightthickness=0, bg="black")
        self.canvas.pack(fill="both", expand=True)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Configure>", self.on_resize)

        # Run processing and load metadata
        self.run_processing()
        self.load_metadata()
        if self.stitched_img_path:
            self.display_stitched()

    def run_processing(self):
        """Run the external processing script and capture its final printed output_dir."""
        cmd = ["python", PROCESSING_SCRIPT, self.input_dir]
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Processing script failed. stderr:\n", result.stderr)
            raise RuntimeError("Processing script failed. See console output.")

        # Last non-empty line of stdout is the output directory
        stdout_lines = [L for L in result.stdout.splitlines() if L.strip() != ""]
        if not stdout_lines:
            raise RuntimeError("Processing script produced no output.")
        out_dir = stdout_lines[-1].strip()
        if not os.path.isdir(out_dir):
            raise RuntimeError(f"Processing script did not produce a valid output directory: {out_dir}")

        self.output_dir = out_dir
        print("Processing output dir:", self.output_dir)

    def load_metadata(self):
        grid_json_path = os.path.join(self.output_dir, "grid.json")
        if not os.path.exists(grid_json_path):
            raise FileNotFoundError("grid.json not found in output directory: " + grid_json_path)
        with open(grid_json_path, "r", encoding="utf-8") as f:
            self.grid_meta = json.load(f)

        gs = self.grid_meta.get("grid_size", {})
        self.rows = int(gs.get("rows", 1))
        self.cols = int(gs.get("cols", 1))

        # map (r,c) -> entry
        self.grid_map = {}
        for e in self.grid_meta.get("entries", []):
            r = int(e["grid_x"])
            c = int(e["grid_y"])
            self.grid_map[(r, c)] = e

        # stitched image path (annotated dir / image_stitched.png)
        annotated_dir = self.grid_meta.get("annotated_dir")
        stitched_candidate = os.path.join(annotated_dir, "image_stitched.png")
        if os.path.exists(stitched_candidate):
            self.stitched_img_path = stitched_candidate
        else:
            # fallback: try in annotated dir
            self.stitched_img_path = None
            raise FileNotFoundError("Stitched image not found at: " + stitched_candidate)

    def display_stitched(self):
        """Load stitched image (PIL) and draw it scaled to canvas while preserving aspect ratio."""
        pil_img = Image.open(self.stitched_img_path)
        self.pil_stitched = pil_img
        self._draw_scaled_stitched()

    def _draw_scaled_stitched(self):
        if self.pil_stitched is None:
            return
        cw = max(10, self.canvas.winfo_width())
        ch = max(10, self.canvas.winfo_height())

        img_w, img_h = self.pil_stitched.size
        img_ratio = img_w / img_h
        canvas_ratio = cw / ch

        if img_ratio > canvas_ratio:
            new_w = cw
            new_h = int(cw / img_ratio)
        else:
            new_h = ch
            new_w = int(ch * img_ratio)

        resized = self.pil_stitched.resize((new_w, new_h), Image.LANCZOS)
        self.tk_stitched = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        # center the image
        x = (cw - new_w) // 2
        y = (ch - new_h) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self.tk_stitched, tags=("stitched",))
        # store used image geometry for click mapping
        self.display_offset = (x, y)
        self.display_size = (new_w, new_h)

    def on_resize(self, event):
        # redraw stitched image on window resize
        self._draw_scaled_stitched()

    def on_click(self, event):
        # Map click to stitched-image-coordinates
        if self.pil_stitched is None:
            return

        x_click = event.x
        y_click = event.y
        x_off, y_off = self.display_offset
        disp_w, disp_h = self.display_size

        # if click outside displayed image, ignore
        if x_click < x_off or y_click < y_off or x_click > x_off + disp_w or y_click > y_off + disp_h:
            return

        # compute relative coordinates within the displayed (resized) stitched image
        rel_x = x_click - x_off
        rel_y = y_click - y_off

        # map relative coords to grid cell
        cell_w = disp_w / self.cols
        cell_h = disp_h / self.rows

        c_idx = int(rel_x // cell_w)
        r_idx = int(rel_y // cell_h)

        # clamp
        c_idx = max(0, min(self.cols - 1, c_idx))
        r_idx = max(0, min(self.rows - 1, r_idx))

        # find entry and open annotated image
        entry = self.grid_map.get((r_idx, c_idx))
        if entry is None:
            print("No image for cell", r_idx, c_idx)
            return
        ann_path = entry.get("annotated_path")
        if not os.path.exists(ann_path):
            print("Annotated path does not exist:", ann_path)
            return

        print("Opening annotated image:", ann_path)
        self.open_image_popup(ann_path, title=os.path.basename(ann_path))

    def open_image_popup(self, img_path, title="Image"):
        """Open a popup showing the full annotated image (resized to popup window)."""
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("800x600")
        popup.transient(self.root)

        canvas = tk.Canvas(popup, bg="black")
        canvas.pack(fill="both", expand=True)

        pil_img = Image.open(img_path)

        def draw():
            cw = max(10, canvas.winfo_width())
            ch = max(10, canvas.winfo_height())
            img_w, img_h = pil_img.size
            img_ratio = img_w / img_h
            canvas_ratio = cw / ch
            if img_ratio > canvas_ratio:
                new_w = cw
                new_h = int(cw / img_ratio)
            else:
                new_h = ch
                new_w = int(ch * img_ratio)
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(resized)
            canvas.delete("all")
            x = (cw - new_w) // 2
            y = (ch - new_h) // 2
            canvas.create_image(x, y, anchor="nw", image=tkimg)
            # keep a reference so it doesn't get garbage-collected
            canvas.image_ref = tkimg

        popup.bind("<Configure>", lambda e: draw())

        # Close button
        btn = tk.Button(popup, text="Close", command=popup.destroy)
        btn.pack(side="bottom", pady=6)

        # Initial draw after popup is mapped
        popup.after(100, draw)


if __name__ == "__main__":
    root = tk.Tk()
    app = StitchedViewer(root)
    root.mainloop()
