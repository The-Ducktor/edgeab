from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="edgeab",
    description="Tool to read an epub to audiobook using MS Edge TTS",
    author="The Ducktor",
    author_email="ninjastealth99@proton.me",
    url="https://github.com/TheDucktor/abedge",
    license="GPL 3.0",
    version="0.1",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'edgeab = :main'
        ]
    },
)
