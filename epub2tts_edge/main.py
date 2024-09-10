import os
import edge_tts
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from alive_progress import alive_bar
import time
import re
from colorama import init, Fore
import xml.etree.ElementTree as ET
import subprocess
import argparse
import shutil
from mutagen import mp4
from PIL import Image
import chaptermake
from epub_convert import export_book_contents as export
from ebooklib import epub
from phonics import phontify

# Initialize colorama
init(autoreset=True)

# Define paths
file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output"
metadata_opf = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/metadata.opf"
cover_img = "/Users/jacks/Documents/Git/devstuff/smartphone.jpg"
processed_files = {}
final_dir = os.getcwd()
voice = "en-US-BrianNeural"


class AudioProcessor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.processed_files = {}
        self.progress = 0.0
        self.running_book = False
        self.running_chapter = False
        os.makedirs(output_dir, exist_ok=True)

    def update_progress(self, progress, total=0):
        print(progress / total)
        self.progress = progress / total

    def is_running_book(self):
        return self.running_book

    @staticmethod
    def remove_special_characters(input_string):
        return re.sub(r"[◇]+", "", input_string)

    @staticmethod
    def append_silence(tempfile, duration=1200):
        if not os.path.exists(tempfile) or os.path.getsize(tempfile) == 0:
            if os.path.exists(tempfile):
                os.remove(tempfile)
            return False
        audio = AudioSegment.from_file(tempfile)
        combined = audio + AudioSegment.silent(duration)
        combined.export(tempfile, format="flac")
        return True

    async def run_tts(self, sentence, filename, voice="en-US-BrianNeural"):
        communicate = edge_tts.Communicate(
            self.remove_special_characters(phontify(sentence)), voice
        )
        await communicate.save(filename)
        return self.append_silence(filename)

    def get_progress(self):
        return self.progress

    def read_sentence(self, sentence, tcount, retries=3, voice="en-US-BrianNeural"):
        filename = os.path.join(self.output_dir, f"pg{tcount}.flac")
        if filename in self.processed_files:
            print(Fore.YELLOW + "Already exists")
            return filename

        attempt = 0
        while attempt < retries:
            try:
                if any(symbol in sentence for symbol in ["◇", "◆"]):
                    print(Fore.YELLOW + "Special symbol found, adding silence")
                    silence = AudioSegment.silent(duration=1600)
                    silence.export(filename, format="flac")
                    self.processed_files[filename] = True
                    return filename

                asyncio.run(self.run_tts(sentence, filename, voice))
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    self.processed_files[filename] = True
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
            Fore.RED
            + f"Failed to process sentence {tcount + 1} after {retries} attempts"
        )
        return None

    def process_audio_chunk(self, audio_chunk):
        combined_chunk = AudioSegment.empty()
        for audio_file in audio_chunk:
            try:
                combined_chunk += AudioSegment.from_file(audio_file)
            except Exception as e:
                print(f"Error processing file {audio_file}: {e}")
        return combined_chunk

    def combine_audio(self, audio_list, chapter_number=0):
        silence_duration = 2000
        num_files = len(audio_list)
        if num_files <= 0:
            print("No audio files to combine.")
            return

        chunk_size = min(3, num_files)
        audio_chunks = [
            audio_list[i : i + chunk_size]
            for i in range(0, len(audio_list), chunk_size)
        ]

        with ThreadPoolExecutor() as executor, alive_bar(
            len(audio_chunks), title=f"Combining Chapter {chapter_number + 1}"
        ) as bar:
            futures = [
                executor.submit(self.process_audio_chunk, chunk)
                for chunk in audio_chunks
            ]
            final_audio = AudioSegment.empty()
            for future in futures:
                chunk_audio = future.result()
                final_audio += chunk_audio
                bar()

        final_audio += AudioSegment.silent(duration=silence_duration)
        combined_filename = os.path.join(
            self.output_dir, f"chapter_{chapter_number + 1}.flac"
        )
        final_audio.export(combined_filename, format="flac")
        print(
            f"Combined audio for Chapter {chapter_number + 1} saved as {combined_filename}"
        )

        for chunk in audio_chunks:
            for audio_file in chunk:
                os.remove(audio_file)

    def process_chapter(
        self, chapter, chapter_number, total_chapters, voice="en-US-BrianNeural"
    ):
        chapter_output_file = os.path.join(
            self.output_dir, f"chapter_{chapter_number + 1}.flac"
        )
        if os.path.exists(chapter_output_file):
            print(
                Fore.YELLOW
                + f"Chapter {chapter_number + 1} already processed, skipping..."
            )
            return chapter_output_file

        sentences = [sentence for sentence in chapter.split("\n") if sentence.strip()]
        tcount = sum(
            len([s for s in total_chapters[i].split("\n") if s.strip()])
            for i in range(chapter_number)
        )

        print(
            Fore.GREEN
            + f"Starting Chapter {chapter_number + 1}: {sentences[0][:50]}..."
            if sentences
            else f"Starting Chapter {chapter_number + 1}: Empty Chapter"
        )

        sentence_dict = {
            i: {
                "text": sentence,
                "filename": os.path.join(self.output_dir, f"pg{tcount + i}.flac"),
                "processed": False,
                "voice": voice,
            }
            for i, sentence in enumerate(sentences)
        }

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    self.read_sentence,
                    sentence_dict[i]["text"],
                    tcount + i,
                    3,
                    sentence_dict[i]["voice"],
                ): i
                for i in sentence_dict
            }
            numbered = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    index = futures[future]
                    if result:
                        sentence_dict[index]["processed"] = True
                        sentence_dict[index]["filename"] = result
                except Exception as e:
                    print(f"Generated an exception: {e}")
                numbered += 1
                self.update_progress(numbered, len(sentences))

        audio_files = [
            sentence_dict[i]["filename"]
            for i in sentence_dict
            if sentence_dict[i]["processed"]
        ]
        self.combine_audio(audio_files, chapter_number)

        return chapter_output_file

    def clean_up(self):
        for file in os.listdir(self.output_dir):
            if file.startswith("pg"):
                os.remove(os.path.join(self.output_dir, file))

    def chapter_data(self, content):
        data = []
        temp_sent = content.split("\n")
        for line in temp_sent:
            if line.startswith("# "):
                data.append(line.replace("# ", ""))
            elif line.startswith("Title:"):
                book_title = line.replace("Title:", "").strip()
        return data

    async def read_book(self, content, cover_img=None, voice="en-US-BrianNeural"):
        
        print(
            Fore.BLUE + "Content before splitting into chapters:\n",
            content[:500],
            "...",
        )

        chapters = content.split("# ", 1)[-1].split("# ")
        print(Fore.BLUE + f"Number of chapters parts found: {len(chapters)}")

        total_chapters = len(chapters)

        for chapter_number, chapter in enumerate(chapters):
            self.running_book = True
            print(
                Fore.BLUE + f"Chapter {chapter_number + 1} content preview:\n",
                Fore.LIGHTBLACK_EX + chapter[:200],
            )

            self.process_chapter(chapter, chapter_number, chapters, voice)
            self.update_progress(chapter_number, total_chapters)
            # Update progress after processing each chapter

        self.clean_up()

        file_list = [
            os.path.join(self.output_dir, f)
            for f in os.listdir(self.output_dir)
            if f.endswith(".flac") and f.startswith("chapter")
        ]

        print(Fore.GREEN + "Merging Files")

        # Update progress for the merging step

        time.sleep(2)
        chaptermake.create(
            self.chapter_data(content),
            file_list,
            os.path.join(self.output_dir, "book.m4b"),
            self.output_dir,
        )
        self.running_book = False


class M4BMetadataHandler:
    def __init__(
        self,
        xml_file: str,
        input_m4b: str = "",
        output_m4b: str = "",
        book_img=None,
        output_dir="/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output",
        final_dir=os.getcwd(),
    ):
        self.xml_file = xml_file
        self.input_m4b = input_m4b or os.path.join(output_dir, "book.m4b")
        self.output_m4b = output_m4b or os.path.join(output_dir, "out.m4b")
        self.book_img = book_img or os.path.join(final_dir, "cover.jpg")
        self.output_dir = output_dir
        self.final_dir = final_dir

    def extract_metadata_from_opf(self):
        # Parse the XML file
        tree = ET.parse(self.xml_file)
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

    def add_metadata_to_m4b(self, title: str, author: str, description: str):
        # Constructing the ffmpeg command
        output_file = os.path.join(self.final_dir, f"{title}.m4b")
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            self.input_m4b,
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

        subprocess.check_output(ffprobe_command, universal_newlines=True)

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
        duration, bitrate = stats_output.strip().split("\n")
        print(f"\nBasic stats:\nDuration: {duration} seconds\nBitrate: {bitrate} bps")

        return output_file

    def process(self):
        title, author, description, cover_image_href = self.extract_metadata_from_opf()
        output_file = self.add_metadata_to_m4b(title, author, description)
        print(self.book_img)
        add_cover(self.book_img, output_file)


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
    default_metadata_opf = f"{
            os.path.join(
            final_dir, 'metadata.opf'
        )
        }"
    default_cover_img = "/Users/jacks/Documents/Git/devstuff/smartphone.jpg"
    print("started")
    is_debug = False
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
            book_reader = AudioProcessor(output_dir)
            book_reader.read_book(file_content, cover_img, voice)
        handler = M4BMetadataHandler(metadata_opf, "", "", cover_img)
        handler.process()
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
