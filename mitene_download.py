import argparse
import asyncio
import glob
import json
import os
import sys
import urllib.parse
import mimetypes
from typing import Awaitable

import aiohttp
from tqdm import tqdm

class TqdmUpTo(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

async def gather_with_concurrency(n: int, *tasks: Awaitable[None]) -> None:
    semaphore = asyncio.Semaphore(n)
    async def sem_task(task: Awaitable[None]) -> None:
        async with semaphore:
            await task
    await asyncio.gather(*(sem_task(task) for task in tasks))

def handle_retry_attempt(attempt, max_retries, media_name):
    if attempt < max_retries - 1:
        print(f"Retry {attempt + 1} for {media_name} due to ClientPayloadError")
    else:
        print(f"Failed to download {media_name} after {max_retries} attempts due to ClientPayloadError")

async def download_media(session: aiohttp.ClientSession, url: str, destination_filename: str, media_name: str, verbose: bool, current_index: int, total_media: int, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        try:
            if not os.path.exists(destination_filename):
                r = await session.get(url, timeout=600)
                r.raise_for_status()
                content_type = r.headers.get('Content-Type', '')
                file_extension = mimetypes.guess_extension(content_type)
                if file_extension and not destination_filename.endswith(file_extension):
                    destination_filename += file_extension
                with open(destination_filename, "wb") as f:
                    total_size = int(r.headers.get('content-length', 0))
                    with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, total=total_size,
                                  desc=f"Downloading {current_index} of {total_media}",
                                  leave=False, mininterval=0.1, ncols=100, 
                                  bar_format='{desc}: [{bar}] {percentage:3.0f}% - {n_fmt}/{total_fmt}') as pbar:
                        async for chunk in r.content.iter_chunked(1024):
                            f.write(chunk)
                            pbar.update(len(chunk))
            elif verbose:
                print(f"{media_name} already downloaded.")
            break  
        except aiohttp.ClientPayloadError:
            handle_retry_attempt(attempt, max_retries, media_name)

async def async_main(concurrency: int = 4) -> int:
    comments_saved_counter = 0

    parser = argparse.ArgumentParser(prog='mitene_download')
    parser.add_argument("album_url")
    parser.add_argument("--destination-directory", default="out")
    parser.add_argument("-p", "--password")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    os.makedirs("comments", exist_ok=True)
    os.makedirs("downloaded", exist_ok=True)

    for tmp_file in glob.glob(os.path.join("comments", "*.tmp")):
        os.unlink(tmp_file)

    download_coroutines = []
    async with aiohttp.ClientSession() as session:
        page = 1
        while True:
            r = await session.get(f"{args.album_url}?page={page}")
            response_text = await r.text()

            if page == 1 and 'Please enter your password' in response_text:
                if not args.password:
                    print('Album is password protected, please specify password with --password', file=sys.stderr)
                    sys.exit(1)
                authenticity_token = response_text.split('name="authenticity_token" value="')[1].split('"')[0]
                r = await session.post(f"{args.album_url}/login", data={'session[password]': args.password, 'authenticity_token': authenticity_token})
                if r.url.path.endswith('/login'):
                    print('Could not authenticate, maybe password is incorrect', file=sys.stderr)
                    sys.exit(1)
                continue

            page_text = response_text.split("//<![CDATA[\nwindow.gon={};gon.media=")[1].split(";gon.familyUserIdToColorMap=")[0]
            data = json.loads(page_text)

            page += 1
            if not data["mediaFiles"]:
                break
            for index, media in enumerate(data["mediaFiles"]):
                filename = urllib.parse.urlparse(media.get("expiringVideoUrl", media["expiringUrl"])).path.split("/")[-1]
                filename = f'{media["tookAt"].replace(":", "_")}-{filename}'
                destination_filename = os.path.join("downloaded", filename)
                download_coroutines.append(download_media(session, f"{args.album_url}/media_files/{media['uuid']}/download", destination_filename, media['uuid'], args.verbose, index+1, len(data["mediaFiles"])))

                if media["comments"]:
                    comment_filename = os.path.join("comments", os.path.splitext(filename)[0] + ".md")
                    comment_filename = comment_filename.replace(':', '_')
                    with open(comment_filename, "w", encoding='utf-8') as comment_f:
                        total_comments = len(media["comments"])
                        for comment in media["comments"]:
                            if not comment["isDeleted"]:
                                comment_f.write(f'**{comment["user"]["nickname"]}**: {comment["body"]}\n\n')
                            comments_saved_counter += 1
                        print(f"\rComments saved: {comments_saved_counter}", end="")

        await gather_with_concurrency(concurrency, *download_coroutines)

    return comments_saved_counter

def main() -> None:
    loop = asyncio.get_event_loop()
    comments_saved_counter = loop.run_until_complete(async_main(concurrency=4))
    print(f"Total comments saved: {comments_saved_counter}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
        sys.exit(0)
