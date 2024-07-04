import os
from alive_progress.core.hook_manager import logging
import edge_tts
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from alive_progress import alive_bar
import time
import re
from colorama import init, Fore, Style
import chapterfile
import m4b_tool
import xml.etree.ElementTree as ET
import subprocess
import argparse
import shutil
from mutagen import mp4
import sys
from PIL import Image
# Initialize colorama
init(autoreset=True)

# Define paths
file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
metadata_opf = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/metadata.opf"
cover_img = "/Users/jacks/Documents/Git/devstuff/smartphone.jpg"
processed_files = {}
final_dir = os.getcwd()



def remove_special_characters(input_string):
    return re.sub("[◇]+", "", input_string)

def append_silence(tempfile, duration=1200):
    if not os.path.exists(tempfile) or os.path.getsize(tempfile) == 0:
        if os.path.exists(tempfile):
            os.remove(tempfile)
        return False
    audio = AudioSegment.from_file(tempfile)
    combined = audio + AudioSegment.silent(duration)
    combined.export(tempfile, format="flac")
    return True

async def run_tts(sentence, filename):
    communicate = edge_tts.Communicate(sentence, "en-US-BrianNeural")
    await communicate.save(filename)
    return append_silence(filename)

def read_sentence(sentence, tcount, retries=3):
    filename = os.path.join(output_dir, f"pg{tcount}.flac")
    
    # Check if already processed
    if filename in processed_files:
        print(Fore.YELLOW + "Already exits")
        return filename
    
    attempt = 0
    while attempt < retries:
        try:
            if "◇" in sentence:
                print(Fore.YELLOW + "Ignore not possible")
            asyncio.run(run_tts(sentence, filename))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                processed_files[filename] = True
                return filename
            else:
                print(Fore.YELLOW + "Audio file is empty, retrying...")
        except Exception as e:
            print(Fore.YELLOW + f'Retrying sentence "{sentence}" / {tcount + 1} due to error: {e}')
        attempt += 1
        time.sleep(1 ** attempt)
    
    print(Fore.RED + f"Failed to process sentence {tcount + 1} after {retries} attempts")
    return None

def process_chapter(chapter, chapter_number, total_chapters):
    sentences = [sentence for sentence in chapter.split("\n") if sentence.strip()]
    tcount = sum(len([s for s in total_chapters[i].split("\n") if s.strip()]) for i in range(chapter_number))

    print(Fore.GREEN + f"Starting Chapter {chapter_number + 1}: {sentences[0][:50]}..." if sentences else f"Starting Chapter {chapter_number + 1}: Empty Chapter")

    # Check for existing files in output directory and mark them as processed
    for file in os.listdir(output_dir):
        if file.endswith(".flac"):
            processed_files[os.path.join(output_dir, file)] = True

    sentence_dict = {i: {"text": sentence, "filename": os.path.join(output_dir, f"pg{tcount + i}.flac"), "processed": False} for i, sentence in enumerate(sentences)}

    with ThreadPoolExecutor() as executor, alive_bar(len(sentences), title=f"Processing Chapter {chapter_number + 1}") as bar:
        futures = {executor.submit(read_sentence, sentence_dict[i]["text"], tcount + i): i for i in sentence_dict}
        for future in as_completed(futures):
            try:
                result = future.result()
                index = futures[future]
                if result:
                    sentence_dict[index]["processed"] = True
                    sentence_dict[index]["filename"] = result
            except Exception as e:
                print(Fore.RED + f"Generated an exception: {e}")
            bar()

    audio_files = [sentence_dict[i]["filename"] for i in sentence_dict if sentence_dict[i]["processed"]]

    combined_audio = AudioSegment.empty()
    with alive_bar(len(audio_files), title=f"Combining Chapter {chapter_number + 1}") as bar:
        for audio_file in audio_files:
            try:
                combined_audio += AudioSegment.from_file(audio_file)
            except Exception as e:
                print(Fore.RED + f"Error processing file {audio_file}: {e}")
            bar()

    combined_filename = os.path.join(output_dir, f"chapter_{chapter_number + 1}.flac")
    combined_audio.export(combined_filename, format="flac")
    print(Fore.CYAN + f"Combined audio for Chapter {chapter_number + 1} saved as {combined_filename}")

    for audio_file in audio_files:
        os.remove(audio_file)

def clean_up():
    for file in os.listdir(output_dir):
        if file.startswith("pg"):
            os.remove(os.path.join(output_dir, file))

def chapter_data(content):
    data = []
    temp_sent = content.split("\n")
    for line in temp_sent:
        if line.startswith("# "):
            data.append(line.replace("# ",""))
        elif line.startswith("Title:"):
            book_title = line.replace("Title:","").strip()
    return data

debug_dont_tts = True
def read_book(content,cover_img=None,is_debug=False):
    if not is_debug:
        chapter_data(content)
        print(Fore.BLUE + "Content before splitting into chapters:\n", content[:500], "...")
        chapters = content.split("# ", 1)[-1].split("# ")
        print(Fore.BLUE + f"Number of chapters found: {len(chapters)}")
        for chapter_number, chapter in enumerate(chapters):
            print(Fore.BLUE + f"Chapter {chapter_number + 1} content preview:\n", chapter[:200], "...")
            process_chapter(chapter, chapter_number, chapters)
        clean_up()
    # Make into m4b audiobook and merge files
    file_list = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if (f.endswith(".flac") and f.startswith("chapter"))]
    print(Fore.GREEN+"Merging Files")
    time.sleep(2)
    chapterfile.create_m4b(chapter_data(content),file_list)

def add_metadata(xml_file, input_m4b=None, output_m4b=None,book_img=None):
    if input_m4b is None:
            input_m4b = os.path.join(output_dir, "book.m4b")
    if output_m4b is None:
        output_m4b = os.path.join(output_dir, "out.m4b")
    if book_img is None:
        book_img = "/Users/jacks/Documents/Git/devstuff/smartphone.jpg"
    def extract_metadata_from_opf(xml_file):
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Namespace dictionary for ElementTree
        ns = {
            'dc': 'http://purl.org/dc/elements/1.1/',
            'opf': 'http://www.idpf.org/2007/opf'
        }
        
        # Extract metadata
        title = root.findtext('.//dc:title', namespaces=ns)
        author = root.findtext('.//dc:creator', namespaces=ns)
        description = root.findtext('.//dc:description', namespaces=ns)
        cover_image_href = None
        cover_reference = root.find('.//guide/reference[@type="cover"]', ns)
        if cover_reference is not None:
            cover_image_href = cover_reference.attrib.get('href')
        
        return title, author, description, cover_image_href
    
    def add_metadata_to_m4b(input_file, output_file, title, author, description):
        # Constructing the ffmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-i", input_file,
            "-metadata", f"title={title}",
            "-metadata", f"author={author}",
            "-metadata", f"description={description}",
            "-metadata", f"album={title}",
            "-metadata", f"artist={author}",
        ]
        
        ffmpeg_command.extend([
            "-c", "copy",
            "-map_metadata", "0",
            output_file
        ])
        
        # Running the command
        subprocess.run(ffmpeg_command, check=True)
    
    # Extract metadata from OPF XML file
    title, author, description, cover_image_href = extract_metadata_from_opf(xml_file)

    output_file = (os.path.join(final_dir,(title+".m4b")))
    # Add metadata to M4B file
    add_metadata_to_m4b(input_m4b, output_file, title, author, description)
    add_cover(book_img,output_file)


def resize_image_to_square_top(image_path, size):
    # Open the image file
    img = Image.open(image_path)

    # Get original dimensions
    width, height = img.size

    # Calculate coordinates for cropping
    left = 0
    top = 0
    right = width
    bottom = min(height, width)  # Ensure we crop square from the top

    # Crop the image from the calculated coordinates
    img = img.crop((left, top, right, bottom))

    # Resize the cropped image to the desired square size
    img = img.resize((size, size))

    return img

def add_cover(cover_img, filename):
    try:
        if os.path.isfile(cover_img):
            # Resize cover image to a square with content aligned to top
            resized_img = resize_image_to_square_top(cover_img, 1400)  # Adjust square size as needed

            # Save resized image to a temporary file
            temp_path = "temp_cover.jpg"
            resized_img.save(temp_path)

            # Now add the resized cover image to the mp4 file
            m4b = mp4.MP4(filename)
            cover_image = open(temp_path, "rb").read()
            m4b["covr"] = [mp4.MP4Cover(cover_image)]
            m4b.save()

            # Clean up temporary file
            os.remove(temp_path)

        else:
            print(f"Cover image {cover_img} not found")
    except Exception as e:
        print(f"Error adding cover image: {str(e)}")



def main():
    file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
    output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
    metadata_opf = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/metadata.opf"
    cover_img = "/Users/jacks/Documents/Git/devstuff/smartphone.jpg"
    print("started")
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Argument parsing
    parser = argparse.ArgumentParser(description='Process some files.')
    parser.add_argument('-f', '--file-path', type=str, default=file_path,
                        help='Path to the input text file')
    parser.add_argument('-m', '--metadata-opf', type=str, default=metadata_opf,
                        help='Path to the metadata OPF file')
    parser.add_argument('-c', '--cover-img', type=str, default=cover_img,
                        help='Path to the cover image')
    
    args = parser.parse_args()
    
    # Use the parsed arguments or defaults
    file_path = args.file_path
    metadata_opf = args.metadata_opf
    cover_img = args.cover_img
    
    # Read text file content
    with open(file_path, "r") as file_txt:
        file_content = file_txt.read()
    # Process your file content and metadata
    if file_path.endswith(".txt"):
        read_book(file_content,cover_img,True)
        #add_metadata(metadata_opf, None, None, cover_img)
    elif file_path.endswith(".epub"):
        pass
    # Remove outdir
    shutil.rmtree(output_dir, ignore_errors=True)
    
main()