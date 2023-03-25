import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

ctk.set_default_color_theme("green")


class TreeView(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master)

        self["columns"] = "one"
        self.column("#0", width=200, minwidth=150, stretch=tk.NO)
        self.column("one", width=100, minwidth=50)

        self.heading("#0", text="Name", anchor=tk.W)
        self.heading("one", text="Type", anchor=tk.W)

        def main_query():
            """
            iid, parent_iid, text, values (type)
            """
            files = [(1, '', 'Image', []), (2, '', 'Music', [])]
            for file in files:
                self.insert(parent=file[1],
                            iid=str(file[0]),
                            text=file[2],
                            values=file[3],
                            index=tk.END)

        def sub_query():
            files = [(1, 1, 'Ghe iu dau cua em', ['PNG file']), (1, 2, 'Con buom xinh', ['MP3 file'])]
            for file in files:
                self.insert(parent=str(file[1]),
                            index=tk.END,
                            iid=f"{file[1]}.{file[0]}",
                            text=file[2],
                            values=file[3])

        def query():
            main_query()
            sub_query()

        query()

        # self.insert('', tk.END, text='Image', iid=0, tags=1)
        # self.insert('', tk.END, text='Music', iid=1, tags=2)
        # self.insert('', tk.END, text='Data', iid=2, tags=3)
        #
        # self.insert('', tk.END, text='Ghe iu dau cua em oi', iid=5, open=False)
        # self.insert('', tk.END, text='Con buom xinh', iid=6, open=False)
        # self.move(5, 0, 0)
        # self.move(6, 0, 1)


class TreeFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width, height):
        super().__init__(master)
        self.configure(width=width,
                       height=height)
        self.tree = TreeView(master=self)
        self.tree.pack(side=ctk.LEFT)


class InfoFrame(ctk.CTkFrame):
    def __init__(self, master, width, height, bg_colour):
        super().__init__(master)
        self.configure(width=width,
                       height=height,
                       fg_color=bg_colour)


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

class SegmentedButton(ctk.CTkSegmentedButton):
    def __init__(self, master):
        super().__init__(master)
        # def segmented_button_callback(value):
        #     print("segmented button clicked:", value)

        self.set("Home")
        self.configure(values=["Home", "Menu"])
        self.pack(side=ctk.TOP)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("____")
        self.geometry("1080x720")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.title("DiskReader")

        self.combox = ctk.CTkOptionMenu(master=self,
                                        values=["option1", "option 2"],
                                        width=320,
                                        command=self.optionmenu_callback)
        # self.combox.pack(side=ctk.TOP, anchor=ctk.NW)
        self.combox.place(x=0, y=0)
        self.combox.set("option1")

        self.left = TreeFrame(master=self,
                              width=300,
                              height=720)
        # self.left.pack(side=ctk.LEFT, pady=(20, 0))
        # default height of CTkOptionsMenu = 28
        self.left.place(x=0, y=28)

        self.tab = SegmentedButton(master=self)
        # self.tab.pack(side=ctk.TOP)
        self.tab.place(x=300 - 20 + (1080-(300 + 20))/2, y=1)

        # self.tabview = TabView(master=self,width=1080-300-20,
        #                       height=720
        #                       ,bg_colour="pink")
        # self.tabview.pack(side=ctk.TOP, ipadx=300)

        self.info = InfoFrame(master=self,
                              width=1080 - 300 - 20,
                              height=720,
                              bg_colour="pink")
        # self.info.pack(side=ctk.RIGHT)
        self.info.place(x= 300 + 20, y=28)
    def optionmenu_callback(self, choice):
        print("Optin menu drop down clicked:", choice)


app = App()
app.mainloop()
