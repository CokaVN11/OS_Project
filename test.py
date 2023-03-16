import customtkinter

import tkinter as tk

root = tk.Tk()
root.geometry("300x200")

# Tạo menu bar
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# Tạo menu con "File"
file_menu = tk.Menu(menu_bar, tearoff=False)
file_menu.add_command(label="New")
file_menu.add_command(label="Open")
file_menu.add_separator()
file_menu.add_command(label="Save")
file_menu.add_command(label="Save As...")
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)

# Tạo menu con "Edit"
edit_menu = tk.Menu(menu_bar, tearoff=False)
edit_menu.add_command(label="Cut")
edit_menu.add_command(label="Copy")
edit_menu.add_command(label="Paste")

# Thêm menu con vào menu bar
menu_bar.add_cascade(label="File", menu=file_menu)
menu_bar.add_cascade(label="Edit", menu=edit_menu)

root.mainloop()
