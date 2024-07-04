from pydub import AudioSegment
from mutagen.mp4 import MP4, MP4Tags

def create_m4b(chapter_names, file_paths, output_file="book.m4b"):
    # Initialize an empty AudioSegment
    final_audio = AudioSegment.empty()

    # Create a list to store chapter start times
    chapter_start_times = []

    # Concatenate audio files and record start times
    current_time = 0
    for chapter_name, file_path in zip(chapter_names, file_paths):
        chapter_audio = AudioSegment.from_file(file_path)
        final_audio += chapter_audio
        chapter_start_times.append((chapter_name, current_time))
        current_time += len(chapter_audio)

    # Export the final audio to an M4B file
    final_audio.export(output_file, format="mp4")

    # Load the M4B file using mutagen to add chapter metadata
    m4b = MP4(output_file)

    # Create MP4Tags if not exist
    if m4b.tags is None:
        m4b.tags = MP4Tags()

    # Add chapter metadata
    chapter_list = []
    for chapter_name, start_time in chapter_start_times:
        chapter_list.append(
            {
                "title": chapter_name,
                "start_time": start_time / 1000.0,  # Convert to seconds
                "duration": None,  # Duration can be None
            }
        )

    m4b["©chp"] = chapter_list

    # Save the M4B file with chapters
    m4b.save()
