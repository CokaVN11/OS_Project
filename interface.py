
import customtkinter as ctk

class Frame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.label = ctk.CTkLabel(self,text = "Disk",fg_color=("light blue"), corner_radius=5)
        self.label.grid(row=0, column=0)


class Frame2(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.label = ctk.CTkLabel(self,text="File",width=350, height=400, fg_color=( "light green"), corner_radius=5)
        self.label.grid(row=0, column=0)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("____")
        self.geometry("400x200")

        self.frame1 = Frame(master=self)
        self.frame1.grid(row=0, column=0,padx=10, sticky="nsew")

        self.frame2 = Frame2(master=self)
        self.frame2.grid(row=0, column=0,padx=(120,0), sticky="nsew")


app = App()
app.mainloop()