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
from tkinter import *
from tkinter import filedialog

def browseFiles():
    filename = filedialog.askdirectory(initialdir= "/", title="Select a Disk")
    label_file_explorer.configure(text = "File Opened: " + filename)

window = Tk()
window.title('File Explorer')
window.geometry('500x500')
window.config(background='white')
label_file_explorer = Label(window, text = 'File Explorer', width= 100, height=4, fg='blue')
button_explore = Button(window,
                        text = "Browse Files",
                        command = lambda: browseFiles())

button_exit = Button(window,
                     text = "Exit",
                     command = exit)

label_file_explorer.grid(column = 0, row = 1)
button_explore.grid(column = 0, row = 2)
button_exit.grid(column = 0, row = 3)

window.mainloop()
