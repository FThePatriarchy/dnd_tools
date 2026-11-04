"""Pinned 5etools v2.30.1 source files, used only by the source cross-checks.

The engine itself runs from data/handwritten/. The tests that check those
files against the 2024 books read the 5etools data: raw_data/ (class,
spell and bestiary files) and four files from 5etools-v2.30.1.zip. In a
fresh clone, fetch them with

    python -m engine.source_files --fetch

which downloads the same release tag into raw_data/ (the zip's files go to
raw_data/archive/, read when the zip itself is absent). Both are gitignored.
"""
import argparse
from pathlib import Path
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
VERSION = "v2.30.1"
ZIP = REPO / f"5etools-{VERSION}.zip"
RAW = REPO / "raw_data"
ARCHIVE = RAW / "archive"
BASE = f"https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/{VERSION}/"
CLASSES = ("barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard")
# local path under raw_data/ -> path in the 5etools release
RAW_FILES = {f"class/class-{c}.json": f"data/class/class-{c}.json" for c in CLASSES}
RAW_FILES.update({"spell/spells-xphb.json": "data/spells/spells-xphb.json",
                  "bestiary/bestiary-xmm.json": "data/bestiary/bestiary-xmm.json",
                  "bestiary/bestiary-xphb.json": "data/bestiary/bestiary-xphb.json"})
ARCHIVE_FILES = ("data/book/book-xdmg.json", "data/items.json", "data/magicvariants.json", "data/spells/sources.json")


def archive_member(member):
    """Bytes of one file of the 5etools release: from the zip if present, else raw_data/archive/."""
    if ZIP.exists():
        with zipfile.ZipFile(ZIP) as z: return z.read(member)
    path = ARCHIVE / member
    if not path.exists():
        raise FileNotFoundError(f"{member}: neither {ZIP.name} nor {path} exists; run python -m engine.source_files --fetch")
    return path.read_bytes()


def fetch(force=False):
    jobs = [(RAW / local, remote) for local, remote in RAW_FILES.items()]
    jobs += [(ARCHIVE / member, member) for member in ARCHIVE_FILES]
    for path, remote in jobs:
        if path.exists() and not force: continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE + remote, timeout=60) as response: data = response.read()
        path.write_bytes(data)
        print(f"{path.relative_to(REPO)}  {len(data):,} bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", action="store_true", help="download missing source files")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = parser.parse_args()
    if args.fetch: fetch(args.force)
    else: parser.print_help()


if __name__ == "__main__":
    main()
