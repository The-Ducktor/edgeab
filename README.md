

> edgeab is a free and open-source Python app that easily creates a full-featured audiobook from an EPUB or text file using realistic text-to-speech from [Edge-TTS](https://github.com/rany2/edge-tts/).

> Note: This project is a semi-remake of [epub2tts-edge](https://github.com/aedocw/epub2tts-edge), but it's optimized for my use case, running approximately 8x faster (or at a minimum 4-5x) and using calibre for metadata.

* Generally takes about 10 minutes for the light novels I've tested this on from start to finished file.

## 🚀 Features

- [x] Creates standard format M4B audiobook file
- [x] Automatic chapter break detection
- [x] Embeds cover art if specified (crops image to square)
- [x] Utilizes Microsoft Edge for free cloud-based TTS
- [x] Reads sentences in parallel for extremely fast audiobook creation (approximately 10x faster than [epub2tts-edge](https://github.com/aedocw/epub2tts-edge))
- [x] Resumes from the last point if interrupted (kind of)
- [x] Embeds all the fun metadata pulled from a calibre opf file

**Note:** EPUB file must be DRM-free

## 📖 Usage

Convert EPUB to formatted TXT file:

```bash
edgeab -f "epubfile"
```

Alternatively, use [epub2tts-edge](https://github.com/aedocw/epub2tts-edge):

```bash
edgeab -f "gen-file" -m "opfmetafile" -c "coverimage" -v "voice"
```

## Updating

1. Navigate to the repository directory:

```bash
cd /path/to/repo
```

2. Pull the latest changes:

```bash
git pull
```

3. If you installed in a virtual environment, activate it:

```bash
source /path/to/venv/bin/activate
```

4. Upgrade the installation:

```bash
pip install . --upgrade
```

## Thanks

A special thanks to the following projects that made edgeab possible:

- [Edge-TTS](https://github.com/rany2/edge-tts)
- [epub2tts-edge](https://github.com/aedocw/epub2tts-edge)

## Author

**The Ducktor**

- GitHub: [@The-Ducktor](https://github.com/The-Ducktor)

---
