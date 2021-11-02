Download medias from https://mitene.us/ or https://family-album.com/ to keep a local backup.

## Usage

Install with `pip install mitene_download`.

From mitene app, invite a family member for the web version and copy the URL ( that should be something like `https://mitene.us/f/abcd123456` )

Run the script with `python -m mitene_download https://mitene.us/f/abcd123456`, using the URL from previous step.
 
This will download all photos and video in `out` folder. Some text files will be created with the comments.

If the album is password-protected, you can specify the password using `--password` command line argument, similar to this: `python -m mitene_download https://mitene.us/f/abcd123456 --password the_password`.
