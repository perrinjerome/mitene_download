"""
This module provides functionality to download and manage media from album URLs.
It supports asynchronous downloads, database caching, and error handling.
"""
import asyncio
import json
import sys
import urllib.parse
import aiohttp
import os
import shutil
import hashlib
import sqlite3
import aiofiles
import random
from pathlib import Path
from typing import Awaitable, Optional
from tqdm import tqdm

db_connection = None


def init_db():
    global db_connection
    db_connection = sqlite3.connect("cache.db")
    db_connection.execute(
        """CREATE TABLE IF NOT EXISTS cache
                             (url TEXT PRIMARY KEY,
                              cache_filename TEXT,
                              status TEXT,
                              downloaded_size INTEGER,
                              media_type TEXT,
                              creation_date TEXT,
                              last_modified TEXT,
                              file_size INTEGER,
                              checksum TEXT,
                              download_count INTEGER DEFAULT 0,
                              last_accessed TEXT,
                              error_log TEXT,
                              retry_count INTEGER DEFAULT 0,
                              re_download BOOLEAN DEFAULT FALSE)"""
    )
    db_connection.execute(
        """CREATE TABLE IF NOT EXISTS album_urls
                             (url TEXT PRIMARY KEY)"""
    )
    db_connection.commit()


def close_db():
    global db_connection
    if db_connection:
        db_connection.close()


def update_cache(url, cache_filename, status="partial", downloaded_size=0):
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute(
        "REPLACE INTO cache (url, cache_filename, status, downloaded_size) VALUES (?, ?, ?, ?)",
        (url, cache_filename, status, downloaded_size),
    )
    db_connection.commit()


def save_album_url(url: str):
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute("INSERT OR REPLACE INTO album_urls (url) VALUES (?)", (url,))
    db_connection.commit()


def get_all_album_urls() -> list:
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute("SELECT url FROM album_urls")
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def delete_album_url(url: str):
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM album_urls WHERE url = ?", (url,))
    db_connection.commit()


def get_cache_info(url):
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT cache_filename, status, downloaded_size FROM cache WHERE url=?", (url,)
    )
    row = cursor.fetchone()
    return row if row else (None, None, 0)


def calculate_checksum(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def backup_file(file_path: str, backup_dir: str) -> None:
    backup_dir_path = Path(backup_dir)
    backup_dir_path.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file_path, backup_dir_path / Path(file_path).name)


class TqdmUpTo(tqdm):
    def update_to(
        self, b: int = 1, bsize: int = 1, tsize: Optional[int] = None
    ) -> None:
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


class AsyncPageIterator:
    def __init__(self, session, album_url, password):
        self.session = session
        self.album_url = album_url
        self.password = password
        self.page = 0
        self.last_page = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.last_page:
            raise StopAsyncIteration

        self.page += 1
        page_url = f"{self.album_url}?page={self.page}"
        response = await self.session.get(page_url)

        response_text = await response.text()
        if self.page == 1 and "Please enter your password" in response_text:
            if not self.password:
                raise StopAsyncIteration
            authenticity_token = response_text.split(
                'name="authenticity_token" value="'
            )[1].split('"')[0]
            await self.session.post(
                f"{self.album_url}/login",
                data={
                    "session[password]": self.password,
                    "authenticity_token": authenticity_token,
                },
            )

        page_text = response_text.split("//<![CDATA[\nwindow.gon={};gon.media=")[
            1
        ].split(";gon.familyUserIdToColorMap=")[0]
        data = json.loads(page_text)

        if not data["mediaFiles"]:
            self.last_page = True

        return data


async def gather_with_concurrency(n: int, *tasks: Awaitable[None]) -> None:
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task: Awaitable[None]) -> None:
        async with semaphore:
            await task

    await asyncio.gather(*(sem_task(task) for task in tasks))


async def download_media(
    session: aiohttp.ClientSession,
    url: str,
    destination_filename: str,
    media_name: str,
    verbose: bool,
    current_index: int,
    total_media: int,
    max_retries: int = 4,
    buffer_size: int = 8192,
) -> None:
    cache_info = get_cache_info(url)
    downloaded_size = cache_info[2] if cache_info else 0
    destination_file_path = Path(destination_filename)

    if cache_info and cache_info[1] == "complete":
        return

    headers = {"Range": f"bytes={downloaded_size}-"} if downloaded_size > 0 else {}
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=1200) as r:
                r.raise_for_status()

                mode = "ab" if downloaded_size > 0 else "wb"
                with TqdmUpTo(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    total=int(r.headers.get("content-length", 0)) + downloaded_size,
                    initial=downloaded_size,
                    desc=f"Downloading {media_name}",
                    leave=False,
                    mininterval=0.1,
                    ncols=100,
                ) as pbar:
                    async with aiofiles.open(destination_file_path, mode) as f:
                        bytes_accumulated = 0
                        update_interval = 1024 * 1024
                        while True:
                            chunk = await r.content.read(buffer_size)
                            if not chunk:
                                break
                            await f.write(chunk)
                            bytes_accumulated += len(chunk)
                            if bytes_accumulated >= update_interval:
                                pbar.update(bytes_accumulated)
                                downloaded_size += bytes_accumulated
                                update_cache(
                                    url,
                                    str(destination_file_path),
                                    "partial",
                                    downloaded_size,
                                )
                                bytes_accumulated = 0

                        if bytes_accumulated > 0:
                            pbar.update(bytes_accumulated)
                            downloaded_size += bytes_accumulated
                            update_cache(
                                url,
                                str(destination_file_path),
                                "partial",
                                downloaded_size,
                            )

            update_cache(url, str(destination_file_path), "complete", downloaded_size)
            break
        except (aiohttp.ClientPayloadError, aiohttp.ClientError) as e:
            print(f"Error occurred during download: {e}")
            if attempt < max_retries - 1:
                retry_wait = 2**attempt + random.uniform(0, 1)
                print(
                    f"Retrying download of {media_name} in {retry_wait:.2f} seconds (Attempt {attempt + 2}/{max_retries})..."
                )
                await asyncio.sleep(retry_wait)
            else:
                print(f"Max retries reached for {media_name}. Download failed.")
                break


async def async_main(
    album_url: str, password: str, destination_directory: str, verbose: bool
) -> None:
    destination_directory_path = Path(destination_directory)
    destination_directory_path.mkdir(parents=True, exist_ok=True)

    photos_directory = destination_directory_path / "photos"
    comments_directory = destination_directory_path / "comments"
    videos_directory = destination_directory_path / "videos"

    photos_directory.mkdir(parents=True, exist_ok=True)
    comments_directory.mkdir(parents=True, exist_ok=True)
    videos_directory.mkdir(parents=True, exist_ok=True)

    conn = aiohttp.TCPConnector(limit_per_host=4)
    async with aiohttp.ClientSession(connector=conn) as session:
        page_iterator = AsyncPageIterator(session, album_url, password)
        download_coroutines = []
        comment_counter = 0
        async for data in page_iterator:
            for index, media in enumerate(data["mediaFiles"]):
                filename = urllib.parse.urlparse(
                    media.get("expiringVideoUrl", media.get("expiringUrl", ""))
                ).path.split("/")[-1]
                filename_formatted = f'{media["tookAt"].replace(":", "_")}-{filename}'

                if media.get("expiringVideoUrl"):
                    destination_filename = videos_directory / filename_formatted
                    if not destination_filename.suffix:
                        destination_filename = destination_filename.with_suffix(".mp4")
                else:
                    destination_filename = photos_directory / filename_formatted

                cache_info = get_cache_info(
                    f"{album_url}/media_files/{media['uuid']}/download"
                )
                if cache_info and cache_info[1] == "complete":
                    continue

                download_coroutines.append(
                    download_media(
                        session,
                        f"{album_url}/media_files/{media['uuid']}/download",
                        str(destination_filename),
                        media["uuid"],
                        verbose,
                        index + 1,
                        len(data["mediaFiles"]),
                    )
                )

                if media["comments"]:
                    comment_filename = comments_directory / (
                        Path(filename_formatted).stem + ".md"
                    )
                    try:
                        if not comment_filename.exists():
                            async with aiofiles.open(
                                comment_filename, "w", encoding="utf-8"
                            ) as comment_f:
                                for comment in media["comments"]:
                                    if not comment["isDeleted"]:
                                        await comment_f.write(
                                            f'{comment_counter + 1}. **{comment["user"]["nickname"]}**: {comment["body"]}\n\n'
                                        )
                                        comment_counter += 1
                                        print(
                                            f"Comments being saved: {comment_counter}",
                                            end="\r",
                                        )
                    except Exception as e:
                        print(f"\nError writing comments for {media['uuid']}: {e}")

        if not download_coroutines:
            print("No new downloads found. All files are up to date.")
        else:
            await gather_with_concurrency(4, *download_coroutines)
            print("All downloads completed successfully.")


def main() -> None:
    init_db()

    while True:
        album_urls = get_all_album_urls()
        if album_urls:
            print("Select an album URL from the list:")
            for index, url in enumerate(album_urls, start=1):
                print(f"{index}: {url}")

            print(
                "Enter 'a' to add a new URL or 'd' followed by the number to delete (e.g., 'd3')."
            )
            print("Enter 'x' to exit.")
            selection = input("Your choice: ").strip().lower()

            if selection == "a":
                album_url = input("Enter a new album URL: ")
                save_album_url(album_url)
            elif selection.startswith("d") and selection[1:].isdigit():
                index_to_delete = int(selection[1:])
                if 1 <= index_to_delete <= len(album_urls):
                    delete_album_url(album_urls[index_to_delete - 1])
                    print("URL deleted.")
                else:
                    print("Invalid index. Please try again.")
                    continue
            elif selection == "x":
                break
            else:
                print("Invalid input. Please try again.")
                continue
        else:
            print("No URLs saved. Please add a URL.")
            album_url = input("Enter a new album URL: ")
            save_album_url(album_url)

        if "album_url" in locals():
            if input("Does the album have a password? (y/n): ").strip().lower() == "y":
                password = input("Enter the password: ")
            else:
                password = None

            destination_directory = "files"
            verbose = input("Enable verbose logging (y/n): ").strip().lower() == "y"

            print("Starting the script. Please wait...")

            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(
                    async_main(album_url, password, destination_directory, verbose)
                )
            except Exception as e:
                print(f"Error occurred: {e}")

    close_db()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Script interrupted by user. Cleaning up...")
        close_db()
        print("Cleanup complete. Exiting.")
