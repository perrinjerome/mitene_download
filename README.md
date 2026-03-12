Download medias from https://mitene.us/ or https://family-album.com/ to keep a local backup.

## Usage

Install with `pip install mitene_download`.

From mitene app, invite a family member for the web version and copy the URL ( that should be something like `https://mitene.us/f/abcd123456` )

Run the script with `mitene_download https://mitene.us/f/abcd123456`, using the URL from previous step.
 
This will download all photos and video in `out` folder. Some text files will be created with the comments.

If the album is password-protected, the script will prompt you to enter the password securely (input is hidden). You can also specify the password using `--password` command line argument, similar to this: `mitene_download https://mitene.us/f/abcd123456 --password the_password`; however this is unsafe and should be avoided, as the password may be visible in shell history, process lists, or logs.

To exclude comments (MD files) use the `--nocomments` command line argument, similar to this: `mitene_download https://mitene.us/f/abcd123456 --nocomments`