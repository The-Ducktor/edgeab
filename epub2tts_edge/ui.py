import dearpygui.dearpygui as dpg
from tkinter import filedialog
from tkinter import Tk
from epub_convert import export_book_contents as export
from ebooklib import epub
# Initialize the Tkinter root and Dear PyGui context
def initialize_gui():
    root = Tk()
    root.withdraw()  # Hide the root window
    dpg.create_context()

# Open file dialog
def open_file():
    file = filedialog.askopenfilename()
    return file

def create_intermediate(file_path):
    book = epub.read_epub(file_path)
    export(book, file_path)

# Create Dear PyGui window and add UI elements
def setup_dearpygui_window():
    with dpg.window(tag="Demo"):
        dpg.add_checkbox(tag="should_open_file", default_value=False, show=False)
        dpg.add_button(
            label="Open file",
            callback=lambda: dpg.set_value("should_open_file", True)
        )
file = ""
# Main event loop for Dear PyGui
def main_loop():
    dpg.create_viewport(title="Demo", width=600, height=412)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Demo", True)

    while dpg.is_dearpygui_running():
        if dpg.get_value("should_open_file"):
            dpg.set_value("should_open_file", False)
            file = open_file()
            create_intermediate(file)
            # Handle the file here if needed
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

# Run the GUI setup and main loop
if __name__ == "__main__":
    initialize_gui()
    setup_dearpygui_window()
    main_loop()
