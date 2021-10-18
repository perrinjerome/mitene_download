"""Download medias from https://mitene.us/ or https://family-album.com/
"""
__version__ = '0.0.1'

import argparse
import glob
import json
import os
import sys
import urllib.parse

import requests


def main() -> None:
  parser = argparse.ArgumentParser(__doc__)
  parser.add_argument(
      "album_url",
      help="""
  URL of the album.

  This is the URL obtained by inviting a family member for the web version.
  """,
  )

  parser.add_argument("--destination-directory", default="out")

  args = parser.parse_args()

  os.makedirs(args.destination_directory, exist_ok=True)
  # cleanup temp files from previous run, if interrupted
  for tmp_file in glob.glob(os.path.join(args.destination_directory, "*.tmp")):
    os.unlink(tmp_file)

  with requests.Session() as session:
    page = 0
    while True:
      r = session.get(f"{args.album_url}?page={page}")
      page_text = r.text.split("//<![CDATA[\nwindow.gon={};gon.media=")[1].split(
          ";gon.familyUserIdToColorMap=")[0]
      data = json.loads(page_text)

      page += 1
      if not data["mediaFiles"]:
        break

      for media in data["mediaFiles"]:
        expiringUrl = media.get("expiringVideoUrl", media["expiringUrl"])
        filename = urllib.parse.urlparse(expiringUrl).path.split("/")[-1]
        filename = f'{media["tookAt"]}-{filename}'
        destination_filename = os.path.join(args.destination_directory, filename)

        if not os.path.exists(destination_filename):
          with open(destination_filename + ".tmp", "wb") as f:
            r = session.get(expiringUrl)
            r.raise_for_status()
            for chunk in r:
              f.write(chunk)
          os.rename(destination_filename + ".tmp", destination_filename)

        if media["comments"]:
          comment_filename = os.path.splitext(destination_filename)[0] + ".md"
          with open(comment_filename + ".tmp", "w") as comment_f:
            for comment in media["comments"]:
              if not comment["isDeleted"]:
                comment_f.write(f'**{comment["user"]["nickname"]}**: {comment["body"]}\n\n')
          os.rename(comment_filename + ".tmp", comment_filename)

      print(f'processed page {page}')

if __name__ == '__main__':
  main()
