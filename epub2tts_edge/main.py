import argparse
import asyncio
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import chaptermake
import edge_tts
from alive_progress import alive_bar
from colorama import Fore, init
from ebooklib import epub
from epub_convert import export
from mutagen import mp4
from PIL import Image
from pydub import AudioSegment

# Initialize colorama
init(autoreset=True)

# Define paths
file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
metadata_opf = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/metadata.opf"

processed_files = {}
final_dir = os.getcwd()
cover_img = os.path.join(final_dir,"cover.jpg")
voice = "en-US-BrianNeural"


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


async def run_tts(sentence, filename, voice="en-US-BrianNeural"):
    communicate = edge_tts.Communicate(sentence, voice)
    await communicate.save(filename)
    return append_silence(filename)


SILENCE_DURATION = 1600


def read_sentence(sentence, tcount, retries=5, voice="en-US-BrianNeural"):
    filename = os.path.join(output_dir, f"pg{tcount}.flac")

    # Check if already processed
    if filename in processed_files:
        print(Fore.YELLOW + "Already exists")
        return filename
    attempt = 0
    while attempt < retries:
        try:
            if any(symbol in sentence for symbol in ["◇", "◆"]):
                print(Fore.YELLOW + "Special symbol found, adding silence")
                silence = AudioSegment.silent(duration=SILENCE_DURATION)
                silence.export(filename, format="flac")
                processed_files[filename] = True
                return filename

            asyncio.run(run_tts(sentence, filename, voice))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                processed_files[filename] = True
                return filename
            else:
                print(Fore.YELLOW + "Audio file is empty, retrying...")
        except Exception as e:
            print(
                Fore.YELLOW
                + f'Retrying sentence "{sentence}" / {tcount + 1} due to error: {e}'
            )
        attempt += 1
        time.sleep(1**attempt)

    print(
        Fore.RED + f"Failed to process sentence {tcount + 1} after {retries} attempts"
    )
    return None


def split_list(lst, parts):
    length = len(lst)
    size = length // parts
    leftovers = length % parts
    start = 0
    result = []
    for i in range(parts):
        end = start + size + (1 if leftovers > 0 else 0)
        result.append(lst[start:end])
        start = end
        leftovers -= 1
    return result


def process_audio_chunk(audio_chunk):
    combined_chunk = AudioSegment.empty()
    for audio_file in audio_chunk:
        try:
            combined_chunk += AudioSegment.from_file(audio_file)
        except Exception as e:
            print(f"Error processing file {audio_file}: {e}")
    return combined_chunk


def combine_audio(audio_list, chapter_number=None, output_dir="."):
    # Define the duration of silence in milliseconds (e.g., 1000 milliseconds = 1 second)
    silence_duration = 2000  # 2 seconds of silence

    # Calculate an appropriate chunk size based on the number of audio files
    num_files = len(audio_list)
    if num_files <= 0:
        print("No audio files to combine.")
        return

    # Use a heuristic to determine chunk size
    chunk_size = min(
        3, num_files
    )  # Example: Minimum chunk size of 3 or number of files

    # Split audio_list into chunks
    audio_chunks = [
        audio_list[i : i + chunk_size] for i in range(0, len(audio_list), chunk_size)
    ]

    # Concurrently process each chunk
    with ThreadPoolExecutor() as executor, alive_bar(
        len(audio_chunks), title=f"Combining Chapter {chapter_number + 1}"
    ) as bar:
        # Submit tasks to executor for concurrent processing
        futures = [
            executor.submit(process_audio_chunk, chunk) for chunk in audio_chunks
        ]

        # Retrieve results and combine chunks into final_audio
        final_audio = AudioSegment.empty()
        for future in futures:
            chunk_audio = future.result()
            final_audio += chunk_audio
            bar()

    # Add silence at the end of the combined audio
    final_audio += AudioSegment.silent(duration=silence_duration)

    # Export the combined audio to a file
    combined_filename = os.path.join(output_dir, f"chapter_{chapter_number + 1}.flac")
    final_audio.export(combined_filename, format="flac")
    print(
        f"Combined audio for Chapter {chapter_number + 1} saved as {combined_filename}"
    )

    # Optionally, clean up individual audio files
    for chunk in audio_chunks:
        for audio_file in chunk:
            os.remove(audio_file)


def process_chapter(
    chapter, chapter_number, total_chapters, output_dir, voice="en-US-BrianNeural"
):
    # Define the output file for the chapter
    chapter_output_file = os.path.join(output_dir, f"chapter_{chapter_number + 1}.flac")

    # Check if the chapter output file already exists
    if os.path.exists(chapter_output_file):
        print(
            Fore.YELLOW + f"Chapter {chapter_number + 1} already processed, skipping..."
        )
        return chapter_output_file  # Return the existing file

    sentences = [sentence for sentence in chapter.split("\n") if sentence.strip()]
    tcount = sum(
        len([s for s in total_chapters[i].split("\n") if s.strip()])
        for i in range(chapter_number)
    )

    print(
        Fore.GREEN + f"Starting Chapter {chapter_number + 1}: {sentences[0][:50]}..."
        if sentences
        else f"Starting Chapter {chapter_number + 1}: Empty Chapter"
    )

    # Check for existing files in output directory and mark them as processed
    processed_files = {}
    for file in os.listdir(output_dir):
        if file.endswith(".flac"):
            processed_files[os.path.join(output_dir, file)] = True

    sentence_dict = {
        i: {
            "text": sentence,
            "filename": os.path.join(output_dir, f"pg{tcount + i}.flac"),
            "processed": False,
            "voice": voice,
        }
        for i, sentence in enumerate(sentences)
    }

    with ThreadPoolExecutor() as executor, alive_bar(
        len(sentences), title=f"Processing Chapter {chapter_number + 1}"
    ) as bar:
        futures = {
            executor.submit(
                read_sentence,
                sentence_dict[i]["text"],
                tcount + i,
                3,  # retries
                sentence_dict[i]["voice"],
            ): i
            for i in sentence_dict
        }
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

    # List of audio files to be combined
    audio_files = [
        sentence_dict[i]["filename"]
        for i in sentence_dict
        if sentence_dict[i]["processed"]
    ]

    # Combine the audio files into the chapter output file
    combine_audio(audio_files, chapter_number, output_dir)

    # Return the output file for the chapter
    return chapter_output_file


def clean_up():
    for file in os.listdir(output_dir):
        if file.startswith("pg"):
            os.remove(os.path.join(output_dir, file))


def chapter_data(content):
    data = []
    temp_sent = content.split("\n")
    for line in temp_sent:
        if line.startswith("# "):
            data.append(line.replace("# ", ""))
        elif line.startswith("Title:"):
            book_title = line.replace("Title:", "").strip()
    return data


def read_book(content, cover_img=None, voice="en-US-BrianNeural"):
    print(Fore.BLUE + "Content before splitting into chapters:\n", content[:500], "...")
    chapters = content.split("# ", 1)[-1].split("# ")
    print(Fore.BLUE + f"Number of chapters parts found: {len(chapters)}")
    for chapter_number, chapter in enumerate(chapters):
        print(
            Fore.BLUE + f"Chapter {chapter_number + 1} content preview:\n",
            chapter[:200],
            "...",
        )
        process_chapter(chapter, chapter_number, chapters, output_dir, voice)
    clean_up()
    # Make into m4b audiobook and merge files
    file_list = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if (f.endswith(".flac") and f.startswith("chapter"))
    ]
    print(Fore.GREEN + "Merging Files")
    time.sleep(2)
    chaptermake.create(
        chapter_data(content),
        file_list,
        os.path.join(output_dir, "book.m4b"),
        output_dir,
    )


def add_metadata(xml_file, input_m4b=None, output_m4b=None, book_img=cover_img):
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
            "dc": "http://purl.org/dc/elements/1.1/",
            "opf": "http://www.idpf.org/2007/opf",
        }

        # Extract metadata
        title = root.findtext(".//dc:title", namespaces=ns)
        author = root.findtext(".//dc:creator", namespaces=ns)
        description = root.findtext(".//dc:description", namespaces=ns)
        cover_image_href = None
        cover_reference = root.find('.//guide/reference[@type="cover"]', ns)
        if cover_reference is not None:
            cover_image_href = cover_reference.attrib.get("href")

        return title, author, description, cover_image_href

    title, author, description, cover_image_href = extract_metadata_from_opf(xml_file)

    def add_metadata_to_m4b(input_file, output_file, title, author, description):
        # Constructing the ffmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            input_file,
            "-metadata",
            f"title={title}",
            "-metadata",
            f"author={author}",
            "-metadata",
            f"description={description}",
            "-metadata",
            f"album={title}",
            "-metadata",
            f"artist={author}",
            "-c",
            "copy",
            "-map_metadata",
            "0",
            output_file,
        ]

        # Running the command
        subprocess.run(ffmpeg_command, check=True)

        # Retrieve and print metadata using ffprobe
        ffprobe_command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            output_file,
        ]

        metadata_output = subprocess.check_output(ffprobe_command, universal_newlines=True)


        # To get basic stats like duration and bitrate
        ffprobe_stats_command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            output_file,
        ]

        stats_output = subprocess.check_output(
            ffprobe_stats_command, universal_newlines=True
        )

        print("\nBasic stats:")
        duration, bitrate = stats_output.strip().split("\n")
        print(f"Duration: {duration} seconds")
        print(f"Bitrate: {bitrate} bps")

    output_file = os.path.join(final_dir, (title + ".m4b"))
    add_metadata_to_m4b(input_m4b, output_file, title, author, description)
    print(cover_img)
    add_cover(cover_img, output_file)


def resize_image_to_square_top(image_path, size=None):
    # Open the image file
    img = Image.open(image_path)
    # Get original dimensions
    width, height = img.size
    if size is None:
        size = width

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
            resized_img = resize_image_to_square_top(
                cover_img
            )  # Adjust square size as needed

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
    start_time = time.time()
    default_file_path = (
        "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
    )
    output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
    default_metadata_opf = (
        f"{
            os.path.join(
            final_dir, 'metadata.opf'
        )
        }"
    )
    default_cover_img = (
        f"{
            os.path.join(
            final_dir, 'cover.jpg'
        )
        }"
    )
    print("started")
    is_debug = True
    os.makedirs(output_dir, exist_ok=True)

    parser = argparse.ArgumentParser(description="Process some files.")
    parser.add_argument(
        "-f",
        "--file-path",
        type=str,
        default=default_file_path,
        help="Path to the input text file",
    )
    parser.add_argument(
        "-m",
        "--metadata-opf",
        type=str,
        default=default_metadata_opf,
        help="Path to the metadata OPF file",
    )
    parser.add_argument(
        "-c",
        "--cover-img",
        type=str,
        default=default_cover_img,
        help="Path to the cover image",
    )
    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default="en-US-BrianNeural",
        help="Voice to use for text-to-speech (default: en-US-BrianNeural)",
    )

    args = parser.parse_args()
    print(args)
    file_path = args.file_path
    metadata_opf = args.metadata_opf
    cover_img = args.cover_img
    voice = args.voice
    print(f"{file_path}")

    if file_path.endswith(".txt"):
        with open(file_path, "r") as file_txt:
            file_content = file_txt.read()
        read_book(file_content, cover_img, voice)
        add_metadata(metadata_opf, None, None, cover_img)
    elif file_path.endswith(".epub"):
        book = epub.read_epub(file_path)
        export(book, file_path)
        exit()

    if not is_debug:
        shutil.rmtree(output_dir, ignore_errors=True)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total time taken: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
