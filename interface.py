import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from util import *

ctk.set_default_color_theme("green")

class TreeFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width, height, folders):
        super().__init__(master)
        self.configure(width=width, height=height, fg_color = 'transparent')
        self.tree = ttk.Treeview(self)
        self.tree.configure(height=height, show='tree')
        self.tree.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True)
        # self.tree.bind('<<TreeviewOpen>>', self.open_node)
        self.configure_folders(folders)

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
            node = self.tree.insert(parent, 'end', text=entry.get_name(), open=False)
            print(f"{parent}: {entry.get_name()}")
            if is_volume or entry.is_dir :
                for child in reversed(entry.get_entry_list()):
                    stack.append((node, child))


    # def open_node(self, event):
    #     node = event.widget.focus()
    #     if not self.tree.parent(node):
    #         return
    #     path = self.get_path(node)
    #     if path is None:
    #         return
    #     for filename in os.listdir(path):
    #         self.fill_node(node, os.path.join(path, filename))

    # def fill_node(self, node, path):
    #     node = self.tree.insert(node, 'end', text=os.path.basename(path), open=False)
    #     if os.path.isdir(path):
    #         self.tree.insert(node, 'end', text='dummy')
    #         for filename in os.listdir(path):
    #             self.fill_node(node, os.path.join(path, filename))

    def get_path(self, node):
        if not node:
            return node

        if not self.tree.parent(node):
            return None
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
        return os.path.abspath(os.path.join(*path))


class InfoFrame(ctk.CTkFrame):
    def __init__(self, master, width, height, bg_colour):
        super().__init__(master)
        self.configure(width=width, height=height, fg_color=bg_colour)


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

class DiskChoosingButton(ctk.CTkSegmentedButton):
    def __init__(self, master):
        super().__init__(master)
        self.set("Home")
        self.configure(values=["Home", "Menu"])
        self.pack(side=ctk.TOP)

        self._command = self.segmented_button_callback

    def segmented_button_callback(self, value):
        print("segmented button clicked:", value)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1080x720")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.title("DiskReader")

        self.devices = get_usb()
        self.usb_list = ['Please choose a usb']
        self.usb_list = self.usb_list + [device.name for device in self.devices]

        self.tree_geometry = {
            "width": 500,
            "height": 720
        }

        self.combox = ctk.CTkOptionMenu(master=self,
                                        values=self.usb_list[1:],
                                        width=self.tree_geometry['width'],
                                        dynamic_resizing=True,
                                        hover=True,
                                        anchor='center',
                                        command=self.optionmenu_callback)
        self.combox.place(x=0, y=0)
        self.combox.set(self.usb_list[0])

        self.folders = []



        self.left = TreeFrame(master=self,
                              width=self.tree_geometry['width'],
                              height=self.tree_geometry['height'],
                              folders = self.folders)

        # default height of CTkOptionsMenu = 28
        self.left.place(x=0, y=28)

        # self.tab = DiskChoosingButton(master=self)
        # # place the tab in the middle of the window
        # self.tab.place(x=300 - 20 + (1080-(300 + 20))/2, y=1)

        self.info = InfoFrame(master=self,
                              width=1080 - self.tree_geometry['width'] - 20,
                              height=720,
                              bg_colour="pink")
        self.info.place(x= self.tree_geometry['width'] + 20, y=28)

    def __normalize_folder_list(self):
        """Norm form:
        Dict = [
            {
                'name': ...,
                'children': [
                    {'name': ...},
                    {'name': ...},
                    ...
                ]
            },
            {
                ...
            }
        ]
        """
        folder_list = []
        for partition in self.partitions:
            folder_list.append(
                {
                    'name': partition.volume_name,
                    'children': []
                }
            )
            stack = [(partition.get_entry_list(), [])]
            while stack:
                entry_list, entry_sub_list = stack.pop()
                for entry in entry_list:
                    if entry.is_dir:
                        entry_sub_list.append(entry_sub_list)
                        stack.append(entry.sub_list)
                    else:
                        entry_sub_list.append(entry)

    def optionmenu_callback(self, choice):
        print("Optin menu drop down clicked:", choice)
        self.usb_chosen = self.devices[self.usb_list.index(choice) - 1]
        self.partitions = self.usb_chosen.partitions
        # self.folders = [partition.get_entry_list() for partition in self.partitions]
        self.left.configure_folders(self.partitions)
        print(self.partitions)


app = App()
app.mainloop()
