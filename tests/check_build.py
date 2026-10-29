"""Verify actual Jekyll output, including discovery and escaped filenames/text."""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}


class GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.card = None
        self.caption = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("class") == "photo":
            self.card = {"caption": ""}
            self.cards.append(self.card)
        elif self.card is not None:
            if tag in {"a", "img"}:
                self.card[tag] = attrs
            elif tag == "p":
                self.caption = True

    def handle_endtag(self, tag):
        if tag == "div":
            self.card = None
        elif tag == "p":
            self.caption = False

    def handle_data(self, value):
        if self.card is not None and self.caption:
            self.card["caption"] += value


def check(build):
    source = (build / "photos.html").read_text(encoding="utf-8")
    assert "{%" not in source and "{{" not in source, "Unrendered Liquid in gallery"
    parser = GalleryParser()
    parser.feed(source)
    expected = sorted(path.name for path in (ROOT / "photos").iterdir()
                      if path.is_file() and path.suffix.lower() in EXTENSIONS
                      and not path.name.startswith((".", "_")))
    metadata = json.loads((ROOT / "_data/photos.json").read_text(encoding="utf-8"))
    found = []
    for card in parser.cards:
        img, link = card["img"], card["a"]
        url = urlsplit(img["src"])
        assert not url.query and not url.fragment, img["src"]
        path = unquote(url.path).lstrip("/")
        assert (build / path).is_file(), f"Broken gallery image: {path}"
        filename = Path(path).name
        found.append(filename)
        assert link["href"] == img["src"] and link["target"] == "_blank"
        assert link.get("rel") == "noopener"
        entry = metadata.get(filename, {})
        assert img["alt"] == entry.get("alt", Path(filename).stem.replace("-", " ").replace("_", " "))
        assert card["caption"] == entry.get("caption", "")
    assert found == expected, f"Expected {expected}, got {found}"
    assert (build / "index.html").is_file() and (build / "notes.html").is_file()
    assert not (build / "upload-photos.py").exists()
    assert not (build / "tests").exists()
    print(f"Verified {len(found)} gallery photos, links, captions, alt text, and maintenance-file exclusions.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
