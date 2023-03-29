import os
import customtkinter as ctk
import tkinter as tk
from tkextrafont import Font
from PIL import Image, ImageTk
from tkinter import ttk
from util import *

ctk.set_default_color_theme("green")
class TreeFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width, height, folders):

        self.font = Font(file="assets/SourceSansPro-Regular.ttf", size=10, family="Source Sans Pro")
        self.style = ttk.Style()
        ttk.Style().theme_use('default')
        ttk.Style().configure('.', borderwidth=0, highlightthickness=0, relief='flat')
        self.style.configure('Treeview', rowheight = 40, font=self.font, borderwidth=0, highlightthickness=0, relief='ridge')
        # self.style.layout('Treeview.Item', [('Treeitem.image', {'side': 'left', 'sticky': ''}), ('Treeitem.text', {'side': 'left', 'sticky': ''})])
        # self.style.map('Treeview.Item', {'open': [('!disabled', '')], 'close': [('!disabled', '')]})
        super().__init__(master,width=width, height=height, fg_color='white')
        self.master = master
        self.tree = ttk.Treeview(self, height=height, show='tree')
        self.tree.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=10)

        self.image_list = {
            'folder': self.render_picture("./assets/folder.png"),
            'document': self.render_picture("./assets/document.png"),
            'disk': self.render_picture("./assets/hard-drive.png")
        }

        self.tree.tag_configure('folder', image=self.image_list['folder'])
        self.tree.tag_configure('document', image=self.image_list['document'])
        self.tree.tag_configure('disk', image=self.image_list['disk'])
        self.tree.tag_bind('folder', '<Double-1>', self.open_node)
        self.tree.tag_bind('disk', '<Double-1>', self.open_node)
        self.tree.tag_bind('document', '<Double-1>', self.open_node)
        self.configure_folders(folders)

    @staticmethod
    def render_picture(path):
        width = 16
        img = Image.open(path)
        wpersent=(width/float(img.size[0]))
        height = int(float(img.size[1])*float(wpersent))
        img = img.resize((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def configure_folders(self, folders):
        self.folders = folders
        self.tree.delete(*self.tree.get_children())
        for folder in self.folders:
            self.fill_tree('', folder)

    def fill_tree(self, parent, entry):
        stack = [(parent, entry)]
        while stack:
            parent, entry = stack.pop()
            if entry.is_skip():
                continue
            is_volume = False
            if isinstance(entry, FAT32.FAT32) or isinstance(entry, NTFS.NTFS):
                is_volume = True
            tag = 'disk'
            if not is_volume:
                tag = 'folder' if entry.is_dir else 'document'
            node = self.tree.insert(parent=parent,index='end', text=entry.get_name(), open=False, tags=(tag,))
            # self.tree.item(node, image = img)
            # print(f"{parent}: {entry.get_name()}")
            if is_volume or entry.is_dir :
                for child in reversed(entry.get_entry_list()):
                    stack.append((node, child))


    def open_node(self, event):
        node = event.widget.focus()
        # if not self.tree.parent(node):
        #   return
        path = self.get_path(node)
        if path is None:
            return
        info = self.fill_information(path)
        # print(info)
        self.master.insert_text(info)

    def fill_information(self, path):
        # if path[0] not in self.folders:
        #     return 'not supported'
        partition = None
        for folder in self.folders:
            if folder.get_name() == path[0]:
                partition = folder
        if len(path) == 1:
            return partition.get_info()
        file = None
        file = partition.get_entry(path[-1])
        if file is not None:
            return file.get_info()
        if file is None:
            return 'not found'
        pass

    def get_path(self, node):
        if not node:
            return node

        # if not self.tree.parent(node):
        #     return None
        path = [self.tree.item(node)['text']]
        while True:
            node = self.tree.parent(node)
            if not node:
                break
            text = self.tree.item(node)['text']
            if text == '':
                break
            path.append(text)
        path.reverse()
        return path


class InfoFrame(ctk.CTkFrame):
    def __init__(self, master, width, height, bg_colour):
        super().__init__(master)
        self.configure(width=width, height=height, fg_color=bg_colour)
        self.textbox = ctk.CTkTextbox(self, width=width - 10, height=height - 10,
                                       wrap=ctk.WORD, fg_color='transparent',
                                       text_color='black', font=('Source Sans Pro', 20)
                                    )

        self.insert_text('Hello world\n')
        self.insert_text('Hello world')
        self.clear_text()
        self.textbox.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, padx=10, pady=10)

    def clear_text(self):
        self.textbox.configure(state='normal')
        self.textbox.delete('1.0', 'end')
        self.textbox.configure(state='disabled')

    def insert_text(self, text):
        self.textbox.configure(state='normal')
        self.textbox.insert(index='end' ,text=text)
        self.textbox.configure(state='disabled')

# class TabView(ctk.CTkTabview):
#     def __init__(self, master, width, height, bg_colour):
#         super().__init__(master)
#
#         # create tabs
#         self.add("Home")
#         self.add("Menu")
#
#         # add widgets on tabs
#         # self.label = ctk.CTkLabel(master=self.tab("Home"))
#         self.configure(width=width,
#                        height=height,
#                        fg_color=bg_colour)
#         # self.pack(side=ctk.TOP)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1080x720")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.title("DiskReader")

        self.devices = get_usb()
        self.current_choice = None
        self.usb_list = ['Please choose a usb']
        if self.devices == None:
            self.usb_list = ['No usb found']
        else: self.usb_list = self.usb_list + [device.name for device in self.devices]

        self.tree_geometry = {
            "width": 500,
            "height": 720 - 40
        }
        self.container = ctk.CTkFrame(self)
        self.combox = ctk.CTkOptionMenu(master=self.container,
                                        values=self.usb_list[1:],
                                        width=self.tree_geometry['width'],
                                        dynamic_resizing=True,
                                        hover=True,
                                        anchor='center',
                                        command=self.optionmenu_callback)
        self.combox.pack(side = ctk.LEFT, fill = ctk.BOTH, expand=True, anchor='nw')
        self.combox.set(self.usb_list[0])

        self.info_label = ctk.CTkLabel(master=self.container, text='Information', width=self.tree_geometry['width'] + 20)
        self.info_label.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, anchor='ne')
        self.container.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, anchor='nw')

        self.folders = []

        self.tree = TreeFrame(master=self,
                              width=self.tree_geometry['width'],
                              height=self.tree_geometry['height'],
                              folders = self.folders)
        self.tree.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, anchor='w')

        # self.tab = DiskChoosingButton(master=self)
        # # place the tab in the middle of the window
        # self.tab.place(x=300 - 20 + (1080-(300 + 20))/2, y=1)

        self.info_geometry = {
            "width": 1080 - self.tree_geometry['width'] - 40,
            "height": 720 - 40
        }

        self.info = InfoFrame(master=self,
                              width=self.info_geometry['width'],
                              height=self.info_geometry['height'],
                              bg_colour="pink")
        self.info.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True)

    def optionmenu_callback(self, choice):
        if self.devices == None:
            self.devices = get_usb()
            if self.devices == None:
                return
            self.usb_list = ['Please choose a usb']
            self.usb_list = self.usb_list + [device.name for device in self.devices]
            self.combox.configure(values=self.usb_list[1:])
            self.combox.set(self.usb_list[0])
            return
        print("Option menu drop down clicked:", choice)
        if self.current_choice != None and choice == self.current_choice:
            return
        self.current_choice = choice
        self.usb_chosen = self.devices[self.usb_list.index(choice) - 1]
        self.partitions = self.usb_chosen.partitions
        # self.folders = [partition.get_entry_list() for partition in self.partitions]
        self.tree.configure_folders(self.partitions)
        print(self.partitions)

    def insert_text(self, text):
        self.info.clear_text()
        self.info.insert_text(text)

app = App()
app.mainloop()
