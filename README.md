# Kristal WASM builder

Builds Kristal to be playable in your browser.

You should have the original Kristal repo (if it was updated to work with this) cloned. If they didn't update this to work on WASM please use my fork.

LOVE projects are bundled up by
zipping the entire project and then 
changing the extension to `.love`. This repo
has scripts that do it, with some additional steps.

## Setup

Works on Windows, macOS, and Linux although only test for Windows so far.

Have these installed:

- FFMPEG
- Install node.js (tested with version 22)
- Python 3.9 or later (tested with python 3.12) with the dependencies listed in `requirements.txt`. You should make a virtual environment if you wish to utilize packages, which Linux users know to do 100% of the time

And then run at least once here:

- `npm i`

After then, you may run `compile.py` with the correct arguments.
As a refresher, you use `py file.py` on windows to run a python file.
For which, the arguments are:

**FILES TARGETED BY `.gitignore` IN THE KRISTAL FOLDER WILL NOT BE ZIPPED, and so is the `.git` folder there**

```
usage: compile.py [-h] [--game-name GAME_NAME] [--compress] [--base-href BASE_HREF] [--favicon FAVICON]
                  [--keywords KEYWORDS] [--description DESCRIPTION] [--author AUTHOR]
                  kristal_folder html_folder_output

Kristal WASM compiler - compiles the kristal engine to be playable on browser

positional arguments:
  kristal_folder        Path to the main Kristal repository (must have main.lua), since this is the one that    
                        gets zipped
  html_folder_output    Place the folder containing the HTML and where the HTTP server should be set up in      
                        this (new) directory.

options:
                        Name of the tab
  --compress            Compress the .love file as much as possible
  --base-href BASE_HREF
                        in the head, add this: <base href="GOES HERE"> to the output HTML
  --favicon FAVICON     Path to favicon (must be an ico file)
  --keywords KEYWORDS   Add this as a meta tag to the HTML
  --description DESCRIPTION
                        Add this as a meta tag to the HTML
  --author AUTHOR       Add this as a meta tag to the HTML
```

**ALWAYS PASS IN THE COMPRESS ARGUMENT IF YOU DON'T WANT TO RUN OUT OF BANDWIDTH!!!!**

Once you are finished, `cd` to the new folder created (which is what you passed to `html-folder-output`)
and start a http server there. Best way to do it is by running `npx http-server`.

This takes *about* a minute to run.

If you're unsure of the steps look at the github actions used to build a playable prototype of this.

## Limitations

- **NO** ffi
- No opening more threads that run in parallel. They will not open. Have failsafes if that occurs.
- Any API that does stuff to your computer (e.g. those that are exclusive on windows, etc) needs a failsafe otherwise it's an error
- Using the debug menu may lead to crashes (so far: only "reloading")

## Optimizations

These are the optimizations done if you pass in the optimization flag:
- Remove all precompiled binaries that would otherwise require FFI because that doesn't work
- Remove all wallpapers (they take too much space)
- Convert all wav files to ogg files, and compress every audio file

## Hosting

Any static website host does its job well.

GitHub pages:

- Drag the output into its own repository and enable Github pages for it. It should work.
    - In `compile.py`, you **must** pass in `--base-href /name-of-your-repo/` or it will not work!
    - Optimizations are very much recommended since the larger the file, the less visits it can get. You have a 100GB / mo limit per repository, and your game will probably be around the size of 20MB (hence, **remove** existing libraries), so you're capped at 5,000 views per month.

Cloudflare pages:

- At least you get infinite bandwidth. Just keep your game under 25MB. Remove unused mods. Don't make songs too long. You can do this. Look up a guide for how to use cloudflare pages, knowing that if your game is on `example.com/blahblah` you must pass in `--base-href /blahblah/` as an argument to `compile.py`.