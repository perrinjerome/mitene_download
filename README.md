
# Mitene & Family-Album Downloader 2

Download media from [Mitene](https://mitene.us/) & [Family Album](https://family-album.com/) to keep as a local backup. This script allows you to download photos, videos, and comments from the specified album URL and keep them stored locally on your machine.


## Demo


![mitene downloader-min](https://github.com/suasive93/mitene_download_2/assets/20932109/b280a991-3a8b-447b-aa3e-1ae0ab5aa71e)
## Requirements
- Python 3.8.5

## Installation

- Install python.
- Clone the git repo or download the zip.
- pip install mitene_download in command prompt or terminal.
    
## Usage

From mitene app, invite a family member for the web version and copy the URL 
( that should be something like https://mitene.us/f/abcd123456 )
- python mitene_download.py <INSERT_URL>
- python mitene_download.py <INSERT_URL> --password <INSERT_PASSWORD>



## Features

- Saving comments
- Cross platform
- Organizes comments into the comments folder, and the media into downloads.


## Changelog

- Added a timeout option.
- Changed the layout of the code to display cleaner such as, "Comments being saved" and "progress bar for downloads".
- Optimized the code for cleaner operation, easier to read.
- Removed the .tmp file writing, and made it to write files directly. 
- Added the ability to write video media files extension (.mp4) previously not able in version 1.
- Better network handling if lost connection.
- Better exiting the program without causing errors. 


## Authors

- [@perrinjerome](https://github.com/perrinjerome) Jérome Perrin
- [@suasive93](https://github.com/suasive93) Me


