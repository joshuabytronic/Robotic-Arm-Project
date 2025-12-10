import tkinter as tk
from PIL import Image, ImageTk

class DynamicImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Region Click Demo")

        # Load images
        self.main_original  = Image.open(r'data_output/output_20251203_100902/annotated/image_stitched.png')
        self.sub1_original  = Image.open(r'data_output/output_20251203_100902/annotated/2025-12-02 12.45.17.180-surfaceCONTROL 3D 3510-240-SN00623060004.tiff')
        self.sub2_original  = Image.open(r'data_output/output_20251203_100902/annotated/2025-12-02 12.45.23.241-surfaceCONTROL 3D 3510-240-SN00623060004.tiff')

        # Track current image
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

        if canvas_w < 1 or canvas_h < 1:
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

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        # Example: two dynamic regions (left & right halves)
        if event.x < w // 2:
            self.show_sub(self.sub1_original)
        else:
            self.show_sub(self.sub2_original)

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