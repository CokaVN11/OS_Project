import io
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from tkinter import messagebox
from math import floor, ceil
from PIL import Image, ImageTk


def browseFiles():
    filename = filedialog.askdirectory(initialdir="/", title="Select a Disk")
    # if not filename.endswith(":/"):
    # label_file_explorer.configure(text = "File Opened: " + filename)


def convert_size(window, original_size):
    return floor((window.frameWidth * original_size) / 1600)


def convert_image(window, path, original_width, original_height):
    original_image = Image.open(path)
    resized_image = original_image.resize(
        (convert_size(window, original_width),
         convert_size(window, original_height))
    )
    converted_image = ImageTk.PhotoImage(resized_image)
    return converted_image


def convert_image_from_byte(window, data, original_width, original_height):
    original_image = Image.open(io.BytesIO(data))
    resized_image = original_image.resize(
        (convert_size(window, original_width),
         convert_size(window, original_height))
    )
    converted_image = ImageTk.PhotoImage(resized_image)
    return converted_image

class App(ctk.CTk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
