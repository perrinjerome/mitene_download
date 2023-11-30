
# Mitene & Family-Album Downloader 4.0

Download media from [Mitene](https://mitene.us/) & [Family Album](https://family-album.com/). This script allows you to download photos, videos, and comments from the specified album URL and keep them stored locally on your machine.

## Demo

![mitene downloader-min](https://github.com/suasive93/mitene_download_2/assets/20932109/b280a991-3a8b-447b-aa3e-1ae0ab5aa71e)
## Requirements
- Python 3.8.5 and up.

## Installation

- Install python.
- Clone the git repo or download the zip.
- pip install mitene_download in command prompt or terminal.
    
## Usage

To use, invite a family member to the Mitene web version and copy the provided URL (e.g., https://mitene.us/f/abcd123456).
- python mitene_download.py <INSERT_URL>
- python mitene_download.py <INSERT_URL> --password <INSERT_PASSWORD>

## Features

- Saving comments and appending videos. 
- Cross platform
- Organizes files to their corresponding types/folders, comments, photos, and videos. 

## Changelog 4.0

- Initial implementation of the asynchronous media downloader.
- Database integration for storing and retrieving album URLs.
- Command-line interface for user interaction to manage album URLs and initiate downloads.
- Asynchronous download capabilities with progress tracking and error handling.
- Utility functions for checksum calculation and file backup.
- Graceful handling of KeyboardInterrupt (Ctrl+C) for safe script termination.
- A comprehensive logging system for tracking actions and errors.

## Authors

- [@perrinjerome](https://github.com/perrinjerome) Jérome Perrin
- [@suasive93](https://github.com/suasive93) Me


