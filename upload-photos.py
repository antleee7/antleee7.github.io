#!/usr/bin/env python3
"""Copy photographs into this gallery; optionally commit and push with Git."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
ROOT = Path(__file__).resolve().parent


def git(root, *args):
    return subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(root), *args],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.digest()


def copy_photos(root, sources):
    gallery = root / "photos"
    if gallery.is_symlink():
        raise ValueError("The photos directory must not be a symbolic link.")
    gallery.mkdir(exist_ok=True)
    # Preflight the whole batch before copying anything. Compare names without
    # case so the same gallery works on both Windows and GitHub's Linux builder.
    existing = {path.name.casefold(): path for path in gallery.iterdir()}
    planned = {}
    for value in sources:
        source = Path(value).expanduser().resolve(strict=True)
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
            raise ValueError(f"Unsupported photo: {source}")
        if source.name.startswith((".", "_")) or source.name.endswith((" ", ".")):
            raise ValueError(f"Rename this file before uploading: {source.name}")
        key = source.name.casefold()
        previous = existing.get(key) or planned.get(key)
        if previous is not None:
            if previous.is_symlink() or not previous.is_file() or digest(previous) != digest(source):
                raise ValueError(f"A different photo already uses the name {source.name}; rename the new file.")
            continue
        planned[key] = source

    copied = []
    for source in planned.values():
        target = gallery / source.name
        # Exclusive creation also protects against a file appearing after preflight.
        with source.open("rb") as original, target.open("xb") as destination:
            shutil.copyfileobj(original, destination)
        copied.append(target.relative_to(root).as_posix())
        print(f"Added {target.name}")
    return copied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photos", nargs="+", help="Photo paths; quote paths containing spaces")
    parser.add_argument("--push", action="store_true", help="Commit the new photos and push the current branch to its upstream")
    args = parser.parse_args(argv)
    try:
        if args.push:
            if Path(git(ROOT, "rev-parse", "--show-toplevel")).resolve() != ROOT:
                raise ValueError("Run this script from a clone of the website repository.")
            if git(ROOT, "status", "--porcelain", "--untracked-files=all"):
                raise ValueError("Commit or set aside existing changes before using --push.")
            git(ROOT, "symbolic-ref", "--quiet", "--short", "HEAD")
            git(ROOT, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
            # Fail before copying if Git's commit identity has not been configured.
            git(ROOT, "var", "GIT_AUTHOR_IDENT")
            git(ROOT, "var", "GIT_COMMITTER_IDENT")
        copied = copy_photos(ROOT, args.photos)
        if not copied:
            print("These photos are already in the gallery. No changes made.")
            return 0
        if args.push:
            git(ROOT, "add", "--", *copied)
            git(ROOT, "commit", "--only", "-m", f"Add {len(copied)} gallery photo(s)", "--", *copied)
            # Explicit upstream makes this independent of push.default settings.
            branch = git(ROOT, "branch", "--show-current")
            remote = git(ROOT, "config", "--get", "branch." + branch + ".remote")
            merge_ref = git(ROOT, "config", "--get", "branch." + branch + ".merge")
            git(ROOT, "push", "--no-follow-tags", "--recurse-submodules=no", "--", remote, "HEAD:" + merge_ref)
            print("Pushed. GitHub Pages will rebuild when the publishing branch changes.")
        else:
            print("Photos copied for review. Commit and push when ready; no HTML edits are needed.")
        return 0
    except subprocess.CalledProcessError as error:
        print(f"Git could not finish: {error.stderr.strip()}", file=sys.stderr)
        print("Any copied photos or local commit remain available. Check git status; if a push failed, retry git push after fixing access.", file=sys.stderr)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
