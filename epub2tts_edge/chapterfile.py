import os
from pydub import AudioSegment

def create(chapter_names):
    # Directory containing audio files
    audio_directory = '/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output/'
    
    # List all files in the directory
    file_list = sorted([f for f in os.listdir(audio_directory) 
                        if os.path.isfile(os.path.join(audio_directory, f)) 
                        and f.startswith('chapter_') 
                        and f.endswith('.flac')])
    
    # Ensure the number of chapter names matches the number of files
    if len(chapter_names) != len(file_list):
        print("The number of chapter names does not match the number of audio files.")
        return
    
    # Initialize cumulative milliseconds
    cumulative_milliseconds = 0
    
    # Open file for writing
    output_file_path = os.path.join(audio_directory, 'chapters.txt')
    with open(output_file_path, 'w') as output_file:
        # Iterate over each file and corresponding chapter name
        for i, (chap_name, file) in enumerate(zip(chapter_names, file_list), start=1):
            file_path = os.path.join(audio_directory, file)
            try:
                # Load audio file
                audio = AudioSegment.from_file(file_path)
                
                # Get duration in milliseconds
                duration_milliseconds = len(audio)
                
                # Format cumulative milliseconds into hours, minutes, seconds
                hours = int(cumulative_milliseconds // 3600000)
                minutes = int((cumulative_milliseconds % 3600000) // 60000)
                seconds = (cumulative_milliseconds % 60000) / 1000
                formatted_start_time = f"{hours}:{minutes:02}:{seconds:.3f}"
                
                # Update cumulative milliseconds with current chapter's duration
                cumulative_milliseconds += duration_milliseconds
                
                # Write to file
                output_line = f"{formatted_start_time} {chap_name}\n"
                output_file.write(output_line)
                
            except Exception as e:
                print(f"Error processing {file}: {e}")

# Example usage
chapter_names = ["Chapter 1", "Chapter 2", "Chapter 3"]  # Replace with actual chapter names
create(chapter_names)
