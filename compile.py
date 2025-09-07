"""
Cross platform Kristal compilation script out there
PREREQUISITES:
git is installed
pip install pathspec
for certain optimizations, ffmpeg must be installed
This command has ran:
    npm i love.js

No other python packages necessrary
Works on Python 3.9 and later
"""

from collections.abc import Sequence
from dataclasses import dataclass
import io
import os
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional, Union
import pathspec
import shutil
import platform


def load_gitignore_patterns(root: Path) -> pathspec.PathSpec:
    """
    Recursively searches for `.gitignore` files within the given directory tree
    and loads all ignore patterns using `pathspec`.

    Patterns are scoped relative to the location of each `.gitignore` file.

    Args:
        root (Path): The root directory to start the search.

    Returns:
        pathspec.PathSpec: A compiled pathspec object with all ignore rules.
    """
    patterns: List[str] = []

    for gitignore in root.rglob(".gitignore"):
        rel_dir = gitignore.parent.relative_to(root)

        with gitignore.open("r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and comments

                # Prepend relative directory to scope the pattern correctly
                scoped_pattern = str(rel_dir / line) if rel_dir != Path(".") else line
                patterns.append(scoped_pattern)

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


@dataclass
class ZipOptions:
    # where the kristal source is (must have main.lua)
    kristal_folder: str

    # where npx http-server should be called
    html_folder_output: str

    # base href
    base_href: str = ""

    # tab name
    game_name: str = "Kristal"

    # converts all wav files to ogg files
    wav_to_ogg: bool = True

    # existing ogg files (unconverted by the above)
    # are compressed with this compression level (-1 to 6, default 3)
    # omit to not compress
    ogg_compression_level: Union[int, None] = 1
    
    # remove all files in assets/sprites/borders (this pattern)
    remove_borders: bool = True

    # remove all files in lib
    remove_builtin_libs: bool = True
    also_compress_converted_ogg: bool = True
    memory: Optional[int] = None


def zip_folder_respecting_gitignore(folder_path: str, zip_path_: str, options: ZipOptions) -> None:
    """
    Zips the contents of a folder while excluding:
    - Any paths matched by `.gitignore` files (including nested ones)
    - The `.git/` directory itself

    This function works even if the folder is not part of a Git repository.

    Args:
        folder_path (str): Path to the root folder to zip.
        zip_path (str): Destination path for the output ZIP file.

    Returns:
        None
    """
    folder = Path(folder_path).resolve()
    zip_path = Path(zip_path_).resolve()

    ignore_spec = load_gitignore_patterns(folder)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for path in folder.rglob("*"):
            relative_path = path.relative_to(folder)

            if (
                path.is_file()
                and not ignore_spec.match_file(os.fspath(relative_path))

                and ".git" not in relative_path.parts
            ):
                # print("Writing ", str(relative_path))
                # print(relative_path.parts)
                if options.remove_builtin_libs and relative_path.parts[0] == "lib":
                    pass
                    # print(f"Skipping adding the lib", relative_path)
                elif options.ogg_compression_level is not None and path.suffix == ".ogg":
                    # print("Compressing", path)
                    with open(path, "rb") as ab:
                        audio_bytes = ab.read()
                        compressed = compress_ogg_file(audio_bytes, options.ogg_compression_level)
                        zipf.writestr(os.fspath(relative_path), compressed)
                elif options.remove_borders and is_border_file(relative_path.parts):
                    # print("Skipping adding the border", relative_path)
                    # don't add this one
                    pass
                elif path.suffix == ".wav":
                    # print("Compressing ", path)
                    ogg_contents = wav_to_ogg(path, options.ogg_compression_level if options.also_compress_converted_ogg else None)
                    relative_path_2 = relative_path.with_suffix(".ogg")
                    zipf.writestr(os.fspath(relative_path_2), ogg_contents)
                else:
                    zipf.write(path, arcname=os.fspath(relative_path))



def is_border_file(iterable: Sequence[str]) -> bool:
    return any(a == "assets" and b == "sprites" and c == "borders" for a, b, c in zip(iterable, iterable[1:], iterable[2:]))

def compress_ogg_file(ogg_contents: bytes, compression_level: int) -> bytes:
    from pydub import AudioSegment
    audio_bytes_io = io.BytesIO(ogg_contents)
    audio = AudioSegment.from_ogg(audio_bytes_io)
    ogg_buffer = io.BytesIO()
    audio.export(ogg_buffer, 
                 format="ogg",
                 codec="libvorbis", 
                 parameters=["-q:a", str(compression_level)])
    return ogg_buffer.getvalue()

def wav_to_ogg(wav_path: Path, compression_level: Optional[int]) -> bytes:
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(os.fspath(wav_path))
    ogg_buffer = io.BytesIO()
    if compression_level is None:
        audio.export(ogg_buffer, format="ogg")
    else:
        audio.export(ogg_buffer, format="ogg", codec="libvorbis", parameters=["-q:a", str(compression_level)])
    return ogg_buffer.getvalue()

def parse_args() -> ZipOptions:
    import argparse
    parser = argparse.ArgumentParser(description="Kristal WASM compiler - compiles the kristal engine to be playable on browser",)
    parser.add_argument('kristal_folder', type=str, help="Path to the main Kristal repository (must have main.lua), since this is the one that gets zipped")
    parser.add_argument('html_folder_output', type=str, help="Place the folder containing the HTML and where the HTTP server should be set up in this (new) directory.")
    parser.add_argument('--game-name', type=str, help="Name of the tab")
    parser.add_argument('--compress', action="store_true", help="Compress the .love file as much as possible")
    parser.add_argument('--base-href',type=str,help="in the head, add this: <base href=\"GOES HERE\"> to the output HTML")
    args = parser.parse_args()
    
    kristal_folder: str = args.kristal_folder
    html_folder_output: str = args.html_folder_output
    game_name: str = args.game_name
    base_href: str = args.base_href
    compress: bool = args.compress

    options_obj = ZipOptions(
        kristal_folder=kristal_folder,html_folder_output=html_folder_output,
        game_name=game_name,
        base_href=base_href,
    ) if compress else ZipOptions(
        kristal_folder=kristal_folder,html_folder_output=html_folder_output,
        game_name=game_name,
        base_href=base_href,
        wav_to_ogg=False,
        ogg_compression_level=None,
        remove_borders=False,
        remove_builtin_libs=False,
        also_compress_converted_ogg=False,
        memory=None
    )

    return options_obj

import time

def recipe() -> None:
    
    kristal_output = f"kristal_temp_written_{int(time.time())}.love"
    options = parse_args()
    print("Zipping stuff...")
    zip_folder_respecting_gitignore(os.fspath(options.kristal_folder), kristal_output,
                                    options)
    # npx love.js.cmd kristal.love kristal_rel -c -m 1500000000 -t kristal
    
    npx_command = shutil.which("npx")
    if not npx_command:
        raise RuntimeError("npx cannot run. is node installed and in your path?")
    print("Creating ")
    compatibility_mode = True

    love_js_command = 'love.js.cmd'
    if platform.system() == 'Linux' or platform.system() == 'Darwin':
        love_js_command = 'love.js'

    sub_cmd = [npx_command, love_js_command, kristal_output, options.html_folder_output,
               '-c' if compatibility_mode else None,
                '-m', str(options.memory) if options.memory else '700000000',
                '-t', (options.game_name or 'kristal')
               ]
    
    subprocess.run([t for t in sub_cmd if t is not None])
    modify_output(options)
    

def modify_output(options: ZipOptions) -> None:
    """Current changes:
    
    Ensure CTRL+R always reloads the page (TODO: have ctrl)
    """

    index_html_file = Path(options.html_folder_output) / Path("index.html")
    theme_css_file = Path(options.html_folder_output) / Path("theme/love.css")
    
    template_rep = "function goFullScreen()"
    liners = [
        "document.addEventListener('keydown', function(e) { if ((e.ctrlKey || e.metaKey) && (e.key === 'r' || e.key === 'F5')) {window.location.replace(window.location.href);return; } });"
    ]
    template_res = "    \n".join(liners) + "\nfunction goFullScreen()"
    new_index = index_html_file.read_text(encoding="UTF-8").replace(template_rep, template_res)
    if options.base_href:
        new_index = new_index.replace("<head>", f"<head> <base href=\"{options.base_href}\">")
    index_html_file.write_text(new_index, encoding="UTF-8")
    
    template_rep_2 = "#canvas {"
    template_rep_res = "#canvas {\n   image-rendering: pixelated;\n     image-rendering: crisp-edges;"
    updated = theme_css_file.read_text(encoding="UTF-8").replace(template_rep_2, template_rep_res)
    theme_css_file.write_text(updated, encoding="UTF-8")

if __name__ == "__main__":
    recipe()