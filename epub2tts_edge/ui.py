import dearpygui.dearpygui as dpg
from tkinter import filedialog, Tk
from epub_convert import export_book_contents as export
from ebooklib import epub
import subprocess
from main import AudioProcessor, M4BMetadataHandler
import asyncio


# Initialize Tkinter root and Dear PyGui context
def initialize_gui():
    root = Tk()
    root.withdraw()  # Hide the root window
    dpg.create_context()


# Global variables
file = ""
saved_file = ""
cover_img = ""
progress = 0.0


async def update_progress_bar(handler):
    while handler.is_running_book() or handler.get_progress() < 100:
        progress = handler.get_progress()
        dpg.set_value("progress_txt", f"Progress: {progress:.2f}%")
        print(f"Progress: {progress:.2f}%")
        await asyncio.sleep(0.1)  # Update every 100ms


async def audio_backend(handler, file_content, cover_img):
    # Start reading the book in the background
    task = asyncio.create_task(handler.read_book(file_content, cover_img))
    # Update the progress bar asynchronously
    await update_progress_bar(handler)
    await task  # Ensure the background task completes


def audio_processing():
    handler = AudioProcessor(
        output_dir="/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
    )

    # Open the file and create the intermediate file in a separate thread
    global file, saved_file
    file_content = open(saved_file, "r").read()
    asyncio.run(audio_backend(handler, file_content, cover_img))
    handler


# Open file dialog
def open_file():
    global file
    file = filedialog.askopenfilename()
    return file


def create_intermediate(file_path):
    if file_path.endswith(".epub"):
        book = epub.read_epub(file_path)
        export(book, file_path)
        return file_path.replace(".epub", ".txt")
    elif file_path.endswith(".txt"):
        return file_path
    else:
        raise Exception("Unsupported file format")


def open_in_editor():
    print(f"Attempting to open file in editor: {saved_file}")
    CMD = ["zed", saved_file]  # Fixed to use saved_file directly
    subprocess.run(CMD)


def make_audiobook():
    audio_processing()
    


# Create Dear PyGui window and add UI elements
def setup_dearpygui_window():
    with dpg.window(tag="Demo"):
        dpg.add_checkbox(tag="should_open_file", default_value=False, show=False)
        dpg.add_button(
            label="Open file", callback=lambda: dpg.set_value("should_open_file", True)
        )
        dpg.add_text("", tag="status_text")
        dpg.add_button(label="Edit generated file", callback=open_in_editor)
        dpg.add_text("Progress: 0%", tag="progress_txt")
        dpg.add_button(label="Make Audiobook", callback=make_audiobook)


# Main event loop for Dear PyGui
def main_loop():
    dpg.create_viewport(title="Demo", width=600, height=412)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Demo", True)

    global file, saved_file

    while dpg.is_dearpygui_running():
        if dpg.get_value("should_open_file"):
            dpg.set_value("should_open_file", False)
            file = open_file()
            saved_file = create_intermediate(file)
            dpg.set_value("status_text", f"{saved_file} saved")
        dpg.render_dearpygui_frame()
    dpg.destroy_context()


# Run the GUI setup and main loop
if __name__ == "__main__":
    initialize_gui()
    setup_dearpygui_window()
    main_loop()
