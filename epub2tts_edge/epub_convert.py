import os
import re
import zipfile
from PIL import Image
from bs4 import BeautifulSoup
from lxml import etree
import ebooklib
from ebooklib import epub
import warnings

warnings.filterwarnings("ignore", module="ebooklib.epub")

namespaces = {
    "calibre": "http://calibre.kovidgoyal.net/2009/metadata",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "opf": "http://www.idpf.org/2007/opf",
    "u": "urn:oasis:names:tc:opendocument:xmlns:container",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

auto_chap = False  # Flag for auto-chapter naming


def extract_chapter_content(chap):
    """Extract text and title from the chapter HTML content."""
    blacklist = [
        "[document]",
        "noscript",
        "header",
        "html",
        "meta",
        "head",
        "input",
        "script",
    ]
    soup = BeautifulSoup(chap, "html.parser")

    # Extract chapter title (assuming it's in an <h1> tag)
    chapter_title = soup.find("h1")
    chapter_title_text = chapter_title.text.strip() if chapter_title else None

    # Remove footnotes and extract paragraphs
    for a in soup.find_all("a", href=True):
        if not any(char.isalpha() for char in a.text):
            a.decompose()

    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]

    return chapter_title_text, paragraphs


def get_epub_cover(epub_path):
    """Extract cover image from the EPUB file."""
    try:
        with zipfile.ZipFile(epub_path) as z:
            container = etree.fromstring(z.read("META-INF/container.xml"))
            rootfile_path = container.xpath(
                "/u:container/u:rootfiles/u:rootfile", namespaces=namespaces
            )[0].get("full-path")

            rootfile = etree.fromstring(z.read(rootfile_path))
            cover_meta = rootfile.xpath(
                "//opf:metadata/opf:meta[@name='cover']", namespaces=namespaces
            )
            if not cover_meta:
                print("No cover image found.")
                return None

            cover_id = cover_meta[0].get("content")
            cover_item = rootfile.xpath(
                f"//opf:manifest/opf:item[@id='{cover_id}']", namespaces=namespaces
            )
            if not cover_item:
                print("No cover image found.")
                return None

            cover_href = cover_item[0].get("href")
            cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)

            return z.open(cover_path)
    except FileNotFoundError:
        print(f"Could not get cover image of {epub_path}")
        return None


def save_cover_image(cover_image, sourcefile):
    """Save the cover image to a file."""
    if cover_image:
        image = Image.open(cover_image)
        image_filename = sourcefile.replace(".epub", ".png")
        image_path = os.path.join(image_filename)
        image.save(image_path)
        print(f"Cover image saved to {image_path}")


def extract_chapter_names(epub_file):
    with zipfile.ZipFile(epub_file, "r") as zip_ref:
        for file_name in zip_ref.namelist():
            if "toc.ncx" in file_name:  # Find the NCX file that contains the TOC
                toc_file = zip_ref.read(file_name)
                soup = BeautifulSoup(toc_file, "xml")

                chapters = []
                for nav_point in soup.find_all("navPoint"):
                    chapter = nav_point.text.strip()
                    chapters.append(chapter)

                return chapters


def match_single_chapter(short_title, epub_file):
    long_list = extract_chapter_names(epub_file)
    # Normalize the short title to lowercase
    short_title_lower = short_title.lower()

    # Create a regex pattern to match the short title at the start of each long title
    pattern = rf"^{short_title_lower}\b.*"

    # Iterate through the long list to find a match
    for long_title in long_list:
        if re.match(pattern, long_title.lower()):
            return long_title  # Return the first match found

    return None  # Return None if no match is found


def export_book_contents(book, sourcefile):
    """Export book contents to a text file."""
    book_contents = []

    cover_image = get_epub_cover(sourcefile)
    save_cover_image(cover_image, sourcefile)

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            chapter_title, chapter_paragraphs = extract_chapter_content(
                item.get_content()
            )
            book_contents.append(
                {
                    "title": chapter_title,
                    "paragraphs": chapter_paragraphs,
                }
            )

    outfile = sourcefile.replace(".epub", ".txt")
    check_for_file(outfile)
    print(f"Exporting {sourcefile} to {outfile}")

    author = book.get_metadata("DC", "creator")[0][0]
    booktitle = book.get_metadata("DC", "title")[0][0]

    with open(outfile, "w") as file:
        file.write(f"Title: {booktitle}\n")
        file.write(f"Author: {author}\n\n")

        for i, chapter in enumerate(book_contents, start=1):
            if not chapter["paragraphs"]:
                continue

            # Check if chapter title exists or if auto_chap is enabled
            if chapter["title"] is None:
                if auto_chap:
                    file.write(f"# Part {i}\n")
            else:
                # Attempt to match the chapter title, fallback to the original title if no match
                matched_title = (
                    match_single_chapter(chapter["title"], sourcefile)
                    or chapter["title"]
                )
                file.write(f"# {matched_title}\n\n")

            # Write the paragraphs
            for paragraph in chapter["paragraphs"]:
                clean_text = re.sub(
                    r"[\s\n]+", " ", paragraph
                )  # Clean up extra whitespace and newlines
                file.write(f"{clean_text}\n\n")


def check_for_file(filename):
    """Check if a file exists and prompt for overwrite confirmation."""
    if os.path.isfile(filename):
        print(f"The file '{filename}' already exists.")
        overwrite = input("Do you want to overwrite the file? (y/n): ")
        if overwrite.lower() != "y":
            print("Exiting without overwriting the file.")
            exit()
        else:
            os.remove(filename)
