import os
import edge_tts
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from alive_progress import alive_bar
import time
import re
from colorama import init, Fore, Style
import subprocess

# Initialize colorama
init(autoreset=True)

# Define paths
file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output/"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Read text file content
with open(file_path, "r") as file_txt:
    file_content = file_txt.read()

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
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return filename
    attempt = 0
    while attempt < retries:
        try:
            asyncio.run(run_tts(sentence, filename))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
            else:
                print(Fore.YELLOW + "Audio file is empty, retrying...")
        except Exception as e:
            print(Fore.YELLOW + f"Retrying sentence {sentence} / {tcount + 1} due to error: {e}")
        attempt += 1
        time.sleep(1 ** attempt)
    print(Fore.RED + f"Failed to process sentence {tcount + 1} after {retries} attempts")
    return None

def process_chapter(chapter, chapter_number, total_chapters):
    sentences = [sentence for sentence in chapter.split("\n") if sentence.strip()]
    tcount = sum(len([s for s in total_chapters[i].split("\n") if s.strip()]) for i in range(chapter_number))

    print(Fore.GREEN + f"Starting Chapter {chapter_number + 1}: {sentences[0][:50]}..." if sentences else f"Starting Chapter {chapter_number + 1}: Empty Chapter")

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

    combined_filename = os.path.join(output_dir, f"chapter_{chapter_number + 1}.wav")
    combined_audio.export(combined_filename, format="wav")
    print(Fore.CYAN + f"Combined audio for Chapter {chapter_number + 1} saved as {combined_filename}")

    for audio_file in audio_files:
        os.remove(audio_file)
        
    return combined_filename

def read_book(content):
    print(Fore.BLUE + "Content before splitting into chapters:\n", content[:500], "...")
    chapters = content.split("# ")
    print(Fore.BLUE + f"Number of chapters found: {len(chapters)}")
    chapter_audio_files = []
    for chapter_number, chapter in enumerate(chapters):
        print(Fore.BLUE + f"Chapter {chapter_number + 1} content preview:\n", chapter[:200], "...")
        combined_filename = process_chapter(chapter, chapter_number, chapters)
        chapter_audio_files.append(combined_filename)
    
    speaker = "BrianNeural"
    make_m4b(chapter_audio_files, file_path, speaker)

def make_m4b(files, sourcefile, speaker):
    filelist = "filelist.txt"
    basefile = sourcefile.replace(".txt", "")
    outputm4a = f"{basefile}-{speaker}.m4a"
    outputm4b = f"{basefile}-{speaker}.m4b"
    with open(filelist, "w") as f:
        for filename in files:
            filename = filename.replace("'", "'\\''")
            f.write(f"file '{filename}'\n")
    ffmpeg_command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        filelist,
        "-codec:a",
        "flac",
        "-f",
        "mp4",
        "-strict",
        "-2",
        outputm4a,
    ]
    subprocess.run(ffmpeg_command)
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        outputm4a,
        "-i",
        "FFMETADATAFILE",
        "-map_metadata",
        "1",
        "-codec",
        "aac",
        outputm4b,
    ]
    subprocess.run(ffmpeg_command)
    os.remove(filelist)
    os.remove("FFMETADATAFILE")
    os.remove(outputm4a)
    for f in files:
        os.remove(f)
    return outputm4b

if __name__ == "__main__":
    read_book(file_content)
