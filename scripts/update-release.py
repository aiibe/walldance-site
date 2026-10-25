#!/usr/bin/env python3
"""Sync a published release into the static site; never rewrite signed XML."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

PUBLIC = Path(__file__).resolve().parents[1] / "public"
REPOSITORY = "aiibe/walldance"
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"


def fetch(url):
    request = Request(url, headers={"User-Agent": "walldance-site-release-sync"})
    with urlopen(request, timeout=30) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Release metadata or appcast exceeds 1 MB")
    return data


def prepare_release(release, page, fetch_asset=fetch):
    tag = release.get("tag_name", "")
    if (release.get("draft") is not False or release.get("prerelease") is not False
            or not release.get("published_at") or not re.fullmatch(r"v\d+\.\d+\.\d+", tag)):
        raise ValueError("Expected a published stable release")
    version = tag[1:]
    current = re.search(r'data-version="(\d+\.\d+\.\d+)"', page)
    if current and tuple(map(int, version.split("."))) < tuple(map(int, current[1].split("."))):
        raise ValueError("Refusing to replace the site with an older release")
    prefix = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"

    def asset(name):
        return next((item for item in release.get("assets", [])
                     if item.get("name") == name and item.get("state") == "uploaded"
                     and item.get("browser_download_url") == prefix + name), None)

    dmg = asset(f"Walldance-{version}.dmg")
    if not dmg:
        raise ValueError("Release has no Walldance DMG")
    feed_asset = asset("appcast.xml")
    appcast = None
    if feed_asset:
        appcast = fetch_asset(feed_asset["browser_download_url"])
        root = ET.fromstring(appcast)
        item = next((item for item in root.findall("channel/item")
                     if item.findtext(f"{SPARKLE}shortVersionString") == version), None)
        enclosure = item.find("enclosure") if item is not None else None
        if (enclosure is None or enclosure.get("url") != dmg["browser_download_url"]
                or enclosure.get("length") != str(dmg["size"])
                or len(base64.b64decode(enclosure.get(f"{SPARKLE}edSignature", ""), validate=True)) != 64):
            raise ValueError("Appcast does not match the signed release archive")
    elif version != "0.1.0":
        raise ValueError("Release has no signed appcast")

    page, links = re.subn(r'(<a class="download-button" href=")[^"]+("[^>]*>)',
                          lambda match: match[1] + dmg["browser_download_url"] + match[2], page)
    page, labels = re.subn(r'<p class="release-status"[^>]*>.*?</p>',
                           f'<p class="release-status" data-version="{version}">Version {version} · Open the DMG, then drag Walldance into Applications.</p>', page)
    if links != 1 or labels != 1:
        raise ValueError("Expected one download link and one release label in index.html")
    return page, appcast


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fchmod(file.fileno(), 0o644)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?", default="latest", help="Published tag, e.g. v0.1.1; defaults to latest")
    args = parser.parse_args()
    if args.tag != "latest" and not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
        parser.error("Tag must have the form v1.2.3")
    endpoint = "latest" if args.tag == "latest" else f"tags/{args.tag}"
    release = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/{endpoint}"))
    if args.tag != "latest" and release.get("tag_name") != args.tag:
        raise ValueError("GitHub returned a different release tag")
    page, appcast = prepare_release(release, (PUBLIC / "index.html").read_text())
    if appcast is not None:
        atomic_write(PUBLIC / "appcast.xml", appcast)
    elif (PUBLIC / "appcast.xml").exists():
        raise ValueError("Refusing to keep an old appcast alongside a release without updates")
    atomic_write(PUBLIC / "index.html", page.encode())
    print(f"Synced {release['tag_name']}. Review, commit, and redeploy public/.")


if __name__ == "__main__":
    main()
