from pydub import AudioSegment
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from ffmpeg_progress_yield import FfmpegProgress
from alive_progress import alive_bar


def create(chapter_titles, file_list, output_file, output_dir):
    try:
        # Function to get the duration of an audio file in milliseconds
        def get_duration(file_path):
            try:
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "json",
                        file_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                duration_json = json.loads(result.stdout)
                duration_seconds = float(duration_json["format"]["duration"])
                duration_ms = int(duration_seconds * 1000)
                return duration_ms
            except subprocess.CalledProcessError as e:
                print(f"Error occurred while getting duration of {file_path}: {e}")
                return 0
            except (KeyError, ValueError) as e:
                print(f"Error parsing duration data for {file_path}: {e}")
                return 0

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Convert FLAC files to M4A files encoded with AAC
        m4a_files = []

        def convert_to_m4a(file_path):
            try:
                m4a_file_path = os.path.join(
                    output_dir, os.path.basename(file_path).replace(".flac", ".m4a")
                )

                # Check if the output M4A file already exists
                if os.path.exists(m4a_file_path):
                    print(f"{m4a_file_path} already exists. Skipping conversion.")
                    return m4a_file_path

                # Run ffmpeg command to convert FLAC to M4A with progress tracking
                command = ["ffmpeg", "-i", file_path, "-c:a", "aac", m4a_file_path]
                ff = FfmpegProgress(command)
                for progress in ff.run_command_with_progress():
                    pass

                print(f"Converted {file_path} to {m4a_file_path}")
                return m4a_file_path

            except subprocess.CalledProcessError as e:
                print(f"Error occurred during conversion of {file_path}: {e}")
                return None

        # Using ThreadPoolExecutor to convert files concurrently with a progress bar tracking the number of files completed
        with ThreadPoolExecutor(max_workers=4) as executor, alive_bar(len(file_list), title="Converting files") as bar:
            futures = [
                executor.submit(convert_to_m4a, file_path) for file_path in file_list
            ]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    m4a_files.append(result)
                bar()

        # Generate chapter metadata
        metadata = ";FFMETADATA1\n"
        start_time = 0
        m4a_files.sort(
            key=lambda x: int(os.path.splitext(os.path.basename(x))[0].split("_")[1])
        )
        for title, file_path in zip(chapter_titles, m4a_files):
            duration = get_duration(file_path)
            end_time = start_time + duration
            metadata += f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_time}\nEND={end_time}\ntitle={title}\n\n"
            start_time = end_time

        # Write metadata to file
        metadata_file = os.path.join(output_dir, "chapters.txt")
        with open(metadata_file, "w") as f:
            f.write(metadata)

        # Generate input.txt for concatenation
        input_file = os.path.join(output_dir, "input.txt")
        with open(input_file, "w") as f:
            for file_path in m4a_files:
                f.write(f"file '{os.path.abspath(file_path)}'\n")

        # Combine audio files and apply chapter metadata to create an M4B file with progress tracking
        try:
            command = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                input_file,
                "-i",
                metadata_file,
                "-map_metadata",
                "1",
                "-c",
                "copy",
                output_file,
            ]
            ff = FfmpegProgress(command)
            for progress in ff.run_command_with_progress():
                pass

            print(f"Output file created successfully: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error occurred during M4B file creation: {e}")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
