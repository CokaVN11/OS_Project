# import psutil

# # Lấy danh sách các ổ đĩa vật lý
# partitions = psutil.disk_partitions()

# # Liệt kê thông tin các ổ đĩa
# for partition in partitions:
#     print(f"Device: {partition.device}")
#     print(f"Mountpoint: {partition.mountpoint}")
#     print(f"Filesystem type: {partition.fstype}")
#     print(f"Options: {partition.opts}")
#     print(f"Usage: {psutil.disk_usage(partition.mountpoint)}")
#     print("---------------------------")
import io
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from math import floor, ceil
from PIL import Image, ImageTk

def browseFiles():
    filename = filedialog.askdirectory(initialdir= "/", title="Select a Disk")
    # if not filename.endswith(":/"):
        # label_file_explorer.configure(text = "File Opened: " + filename)
def convert_size(window, original_size):
    return floor((window.frameWidth * original_size) / 1600)


def convert_image(window, path, original_width, original_height):
    original_image = Image.open(path)
    resized_image = original_image.resize(
        (convert_size(window, original_width), convert_size(window, original_height))
    )
    converted_image = ImageTk.PhotoImage(resized_image)
    return converted_image


def convert_image_from_byte(window, data, original_width, original_height):
    original_image = Image.open(io.BytesIO(data))
    resized_image = original_image.resize(
        (convert_size(window, original_width), convert_size(window, original_height))
    )
    converted_image = ImageTk.PhotoImage(resized_image)
    return converted_image

class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.focus_force()
        self.grab_set()
        self.title("Disk analysis")
        self.geometry("500x500")

        self.canvas = tk.Canvas(
            self,
            bg="#ffffff",
            height=500,
            width=500,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )
        self.canvas.place(x=0, y=0)
if __name__ == "__main__":
    app = App()
    app.mainloop()
