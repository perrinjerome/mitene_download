"""
mitene_download.py:
A script to download media and comments from mitene album URLs. It handles pagination,
concurrent downloads, and supports password-protected albums.
"""

__version__ = '0.2.3'

import argparse
import asyncio
import json
import os
import sys
import urllib.parse
import mimetypes
from typing import Awaitable, Optional
from tqdm import tqdm
import aiohttp

comments_saved_counter = 0

class TqdmUpTo(tqdm[str]):
    def update_to(self, b: int = 1, bsize: int = 1, tsize: Optional[int] = None) -> None:
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

async def gather_with_concurrency(n: int, *tasks: Awaitable[None]) -> None:
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task: Awaitable[None]) -> None:
        async with semaphore:
            await task

    await asyncio.gather(*(sem_task(task) for task in tasks))

async def download_media(session: aiohttp.ClientSession, url: str, destination_filename: str, media_name: str,
                         verbose: bool, current_index: int, total_media: int, max_retries: int = 3) -> None:
    if os.path.exists(destination_filename):
        if verbose:
            print(f"{media_name} already exists. Skipping download.")
        return

    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=1200) as r:
                r.raise_for_status()
                retry_after = r.headers.get('Retry-After')
                if retry_after:
                    await asyncio.sleep(int(retry_after))
                content_type = r.headers.get('Content-Type', '')
                file_extension = mimetypes.guess_extension(content_type)
                if file_extension and not destination_filename.endswith(file_extension) and not (destination_filename.endswith('.jpg') and file_extension == '.jpeg'):
                    destination_filename += file_extension

                with open(destination_filename, "wb") as f:
                    total_size = int(r.headers.get('content-length', 0))
                    with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, desc=f"Downloading {current_index} of {total_media}", leave=False, mininterval=0.1, ncols=100, bar_format='{desc}: [{bar}] {percentage:3.0f}% - {n_fmt}/{total_fmt}') as pbar:
                        async for chunk in r.content.iter_chunked(1024):
                            f.write(chunk)
                            pbar.update(len(chunk))
            break
        except (aiohttp.ClientPayloadError, aiohttp.ClientError) as e:
            print(f"Error occurred: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
                continue

async def async_main() -> None:
    global comments_saved_counter

    parser = argparse.ArgumentParser(prog='mitene_download')
    parser.add_argument("album_url")
    parser.add_argument("--destination-directory", default="out")
    parser.add_argument("-p", "--password")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    os.makedirs("comments", exist_ok=True)
    os.makedirs("downloaded", exist_ok=True)

    conn = aiohttp.TCPConnector(limit_per_host=4)

    download_coroutines = [] 

    async with aiohttp.ClientSession(connector=conn) as session:
        page = 1
        while True:
            r = await session.get(f"{args.album_url}?page={page}")
            response_text = await r.text()
            if page == 1 and 'Please enter your password' in response_text:
                if not args.password:
                    sys.exit(1)
                authenticity_token = response_text.split('name="authenticity_token" value="')[1].split('"')[0]
                r = await session.post(f"{args.album_url}/login", data={'session[password]': args.password, 'authenticity_token': authenticity_token})
                if r.url.path.endswith('/login'):
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

                media_downloaded = os.path.exists(destination_filename)

                if not media_downloaded:
                    download_coroutines.append(download_media(session, f"{args.album_url}/media_files/{media['uuid']}/download", destination_filename, media['uuid'], args.verbose, index + 1, len(data["mediaFiles"])))
                if media["comments"]:
                    comment_filename = os.path.join("comments", os.path.splitext(filename)[0] + ".md")
                    comment_filename = comment_filename.replace(':', '_')
                    if not os.path.exists(comment_filename):
                        with open(comment_filename, "w", encoding='utf-8') as comment_f:
                            for comment in media["comments"]:
                                if not comment["isDeleted"]:
                                    comment_f.write(f'**{comment["user"]["nickname"]}**: {comment["body"]}\n\n')
                            comments_saved_counter += 1
                            print(f"\rComments saved: {comments_saved_counter}", end="")
        await gather_with_concurrency(4, *download_coroutines)
        await session.close()

def main() -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
