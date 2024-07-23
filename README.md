> epub2tts-edge is a free and open source python app to easily create a full-featured audiobook from an epub or text file using realistic text-to-speech from [Microsoft Edge TTS](https://github.com/rany2/edge-tts/).

## 🚀 Features

- [x] Creates standard format M4B audiobook file
- [x] Automatic chapter break detection
- [x] Embeds cover art if specified
- [x] Uses MS Edge for free cloud-based TTS
- [x] Reads sentences in parallel for very fast audiobook creation
- [x] Resumes where it left off if interrupted
- [x] NOTE: epub file must be DRM-free

## 📖 Usage

<details>
<summary> Usage instructions</summary>

convert epub to formatted txt file

```bash
edgeab -f "epubfile"
```
alteratively use [epub2tts-edge](https://github.com/aedocw/epub2tts-edge)
```bash
edgeab -f "filedir" -m "opfmetafile" -c "coverimage" -v "voice"
```

## Updating

<details>
<summary>UPDATING YOUR INSTALLATION</summary>

1. cd to repo directory
2. `git pull`
3. Activate virtual environment you installed epub2tts in if you installed in a virtual environment
4. `pip install . --upgrade`
</details>

## Author

👤 **The Ducktor**

- GitHub: [@aedocw](https://github.com/The-Ducktor)
