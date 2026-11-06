#!/usr/bin/env python3
"""Download the NASA Exoplanet Archive spectra for this project."""

from __future__ import annotations

import argparse
import csv
import io
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_MANIFEST = (
    "https://exoplanetarchive.ipac.caltech.edu/work/"
    "TMP_umZx4k_3214872/atmospheres/tab1/spectra.csv"
)
DEFAULT_DOWNLOAD_DIRECTORY = Path(__file__).resolve().parents[1] / "RawExoData" / "raw"


def read_clipboard() -> str:
    """Return macOS clipboard contents, when available."""
    try:
        return subprocess.run(
            ["pbpaste"], check=True, capture_output=True, text=True
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def parse_download_commands(text: str) -> list[tuple[str, str]]:
    """Convert wget or curl download commands into (filename, URL) pairs."""
    downloads: list[tuple[str, str]] = []

    for line in text.splitlines():
        words = shlex.split(line.strip())
        if not words:
            continue

        if words[0] == "wget":
            try:
                output_index = words.index("-O")
                filename = words[output_index + 1]
                url = words[output_index + 2]
            except (ValueError, IndexError):
                continue
        elif words[0] == "curl":
            try:
                output_index = next(
                    i for i, word in enumerate(words)
                    if word in ("-o", "--output")
                )
                filename = words[output_index + 1]
                url = next(word for word in words[output_index + 2:] if word.startswith("http"))
            except (StopIteration, IndexError):
                continue
        else:
            continue

        downloads.append((Path(filename).name, url))

    return downloads


def downloads_from_manifest(manifest_url: str) -> list[tuple[str, str]]:
    """Read archive SPEC_PATH entries and turn them into download URLs."""
    request = Request(manifest_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    downloads: list[tuple[str, str]] = []
    archive_root = manifest_url.rsplit("/", 1)[0] + "/"

    for row in reader:
        spec_path = (row.get("SPEC_PATH") or "").strip()
        if not spec_path:
            continue
        url = spec_path if urlparse(spec_path).scheme else urljoin(archive_root, spec_path)
        downloads.append((Path(urlparse(url).path).name, url))

    return downloads


def download_file(url: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"skip  {destination.name}")
        return True

    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=60) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        print(f"saved {destination.name}")
        return True
    except Exception as error:
        destination.unlink(missing_ok=True)
        print(f"FAILED {destination.name}: {error}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commands", nargs="?", type=Path,
                        help="Text file containing wget or curl download commands")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST,
                        help="NASA archive spectra.csv URL")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DOWNLOAD_DIRECTORY,
                        help="Directory for downloaded spectra")
    args = parser.parse_args()

    if args.commands:
        downloads = parse_download_commands(args.commands.read_text())
        source = str(args.commands)
    elif (clipboard := read_clipboard()).strip():
        downloads = parse_download_commands(clipboard)
        source = "clipboard"
    else:
        downloads = downloads_from_manifest(args.manifest)
        source = args.manifest

    if not downloads:
        print(f"No download commands found in {source}.")
        print("Save the pasted wget commands in a text file and pass it as an argument.")
        return 1

    print(f"Downloading {len(downloads)} files to {args.output_dir}")
    failures = sum(not download_file(url, args.output_dir / filename)
                   for filename, url in downloads)

    if failures:
        print(f"{failures} download(s) failed")
        return 1

    print("All downloads completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
