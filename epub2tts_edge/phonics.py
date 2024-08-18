# sentence.py

import re
import csv

# Function to load phonetic mappings from a CSV file
def load_phonics_from_csv(filename):
    """Load phonetic mappings from a CSV file."""
    phonics = {}
    with open(filename, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            phonics[row['name']] = row['phonetic']
    return phonics

# Function to replace character names with their phonetic counterparts
def phontify(text):
    """Replace character names in the text with their phonic counterparts."""
    phonics = load_phonics_from_csv('phonics.csv')
    for name, phonic in phonics.items():
        # Use regular expression to replace names (case insensitive)
        text = re.sub(r'\b' + re.escape(name) + r'\b', phonic, text, flags=re.IGNORECASE)
    return text

# Example usage
if __name__ == "__main__":
    input_text = """
    Hinata Sakaguchi and Milim Nava arrived at Rimuru's castle. "Karin, could you bring the documents?" asked Rimuru. Gabil was also present.
    """
    
    output_text = phontify(input_text)
    print(output_text)
