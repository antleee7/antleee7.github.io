# Adding photographs

GitHub Pages already builds this repository with Jekyll from the root of `main`.
The gallery now discovers images directly inside `photos/` during that build.
Copy or upload a JPG, JPEG, PNG, GIF, WebP, or AVIF there and commit it. Uppercase
extensions and spaces in filenames work. No HTML changes, renaming, metadata
entry, JavaScript, or new hosting service is required. Images appear alphabetically
by filename; subfolders and non-image files are ignored. Avoid filenames starting
with a dot or underscore, which Jekyll treats as special files.

## One-time setup for Git over SSH

Install Git and Python 3. Configure your Git commit name and email if needed:

```sh
git config --global user.name "Your Name"
git config --global user.email "your verified GitHub email or GitHub noreply email"
```

Follow GitHub's [SSH setup instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).
Add your public key to your GitHub account and test the connection:

```sh
ssh -T git@github.com
```

GitHub's success message says you authenticated but do not have shell access;
exit code 1 is normal for that test. Verify any first-connection fingerprint
against GitHub's linked documentation. Then clone your site:

```sh
git clone git@github.com:antleee7/antleee7.github.io.git
cd antleee7.github.io
```

For an existing HTTPS clone, switch its remote once:

```sh
git remote set-url origin git@github.com:antleee7/antleee7.github.io.git
```

The script uses the clone's existing Git authentication. HTTPS clones work too.
SSH uploads here mean Git pushes; GitHub Pages does not accept SFTP uploads.

## Add and publish in one command

Start on the publishing branch and bring it up to date:

```sh
git switch main
git pull --ff-only
python upload-photos.py --push "path/to/photo one.JPG" "path/to/photo two.jpg"
```

Use `python3` instead of `python` on systems that require it, or `py` on Windows.
The script works from any current directory when invoked by its full path.
It preserves the photo bytes and filenames, refuses to overwrite a different
photo with the same name, and skips identical existing files. It validates the
whole batch before copying. With `--push`, it requires a clean clone, a configured
Git name/email, and an upstream branch; it commits only the new photos and pushes
the current branch to its upstream. Pushing a review branch does not publish it;
merging into `main` triggers the existing Pages build.

To copy photos for review without committing or pushing:

```sh
python upload-photos.py "path/to/photo.JPG"
git diff --stat
git status --short
```

If a push fails, your local commit is retained. Fix SSH/network access, use
`git pull --rebase` if the remote advanced, and retry `git push`. Re-running the
script with the same files skips them; it does not retry a previously failed push.

## Optional captions and descriptions

`_data/photos.json` preserves the original caption and contains descriptions for
the first two added photos. New photos appear without any entry in that file.
To supply a caption or a better screen-reader description later, add an entry
keyed by the exact filename:

```json
"photo one.JPG": {
  "alt": "A short description of the photograph",
  "caption": "An optional caption"
}
```

Keep the complete file valid JSON, including commas between entries. Text is
escaped before being rendered. Without metadata, the gallery derives alt text
from the filename and displays no caption. Commit metadata edits normally.

## Checking the gallery

The Gallery checks workflow runs the upload-script tests and the same Jekyll
build action used by Pages. It checks that every discovered photograph is present,
every local image link works, and all supplied captions and descriptions survive
the build. It also adds a temporary photo with spaces, brackets, a hash sign, and
an uppercase extension, without editing HTML or metadata, to verify discovery,
filename escaping, and fallback alt text. This workflow checks changes; the existing Pages deployment stays in
charge of publishing.

For the upload-script tests locally:

```sh
python -m unittest discover -s tests -p "test_*.py" -v
```

Opening the source `photos.html` directly will show Liquid template text.
Preview a Jekyll build or the published page instead.
