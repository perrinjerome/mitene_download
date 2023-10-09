Download media from https://mitene.us/ & https://family-album.com/ to keep as a local backup.

##Requirements:
Python 3.8.5 | Python 3.10 | Python 3.11

## Usage:

Install with `pip install mitene_download`.

From mitene or family-album app, invite a family member for the web version and copy the URL ( that should be something like `https://mitene.us/f/abcd123456` )

Run the script with `python mitene_download.py https://mitene.us/f/abcd123456`, using the URL from previous step.
 
This will download all photos and video in `Comments & Downloaded` folder. Some text files in .md will be created with the comments.

If the album is password-protected, you can specify the password using `--password` command line argument, similar to this: `python mitene_download.py https://mitene.us/f/abcd123456 --password <password1234>`.
