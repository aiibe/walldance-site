import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("update_release", Path(__file__).resolve().parents[1] / "scripts/update-release.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ReleaseSyncTests(unittest.TestCase):
    def setUp(self):
        self.page = '''<a class="download-button" href="https://github.com/aiibe/walldance/releases/download/v0.1.0/Walldance-0.1.0.dmg">Download for Mac</a>
<p class="release-status" data-version="0.1.0">Version 0.1.0 · Open the DMG, then drag Walldance into Applications.</p>'''
        self.prefix = "https://github.com/aiibe/walldance/releases/download/v0.1.1/"
        self.release = {
            "tag_name": "v0.1.1", "draft": False, "prerelease": False, "published_at": "2026-10-25T00:00:00Z",
            "assets": [self.asset("Walldance-0.1.1.dmg"), self.asset("appcast.xml")],
        }
        signature = base64.b64encode(bytes(64)).decode()
        self.feed = f'''<?xml version="1.0"?>\r\n<!-- preserve signed bytes -->
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"><channel><item>
<sparkle:shortVersionString>0.1.1</sparkle:shortVersionString>
<enclosure url="{self.prefix}Walldance-0.1.1.dmg" length="128" sparkle:edSignature="{signature}"/>
</item></channel></rss>\r\n'''.encode()

    def asset(self, name):
        return {"name": name, "state": "uploaded", "size": 128, "browser_download_url": self.prefix + name}

    def test_updates_page_and_preserves_appcast_bytes(self):
        page, feed = sync.prepare_release(self.release, self.page, lambda url: self.feed)
        self.assertIn(f'href="{self.prefix}Walldance-0.1.1.dmg"', page)
        self.assertIn('data-version="0.1.1">Version 0.1.1', page)
        self.assertEqual(feed, self.feed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "appcast.xml"
            sync.atomic_write(path, feed)
            self.assertEqual(path.read_bytes(), self.feed)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_rejects_drafts_and_prereleases(self):
        for field in ("draft", "prerelease"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                sync.prepare_release({**self.release, field: True}, self.page)

    def test_rejects_missing_or_mismatched_feed(self):
        self.release["assets"].pop()
        with self.assertRaises(ValueError):
            sync.prepare_release(self.release, self.page)
        self.release["assets"].append(self.asset("appcast.xml"))
        with self.assertRaises(ValueError):
            sync.prepare_release(self.release, self.page, lambda url: self.feed.replace(b'length="128"', b'length="129"'))

    def test_legacy_release_can_be_synced_without_a_feed(self):
        release = {**self.release, "tag_name": "v0.1.0", "assets": [{
            **self.asset("Walldance-0.1.0.dmg"),
            "browser_download_url": "https://github.com/aiibe/walldance/releases/download/v0.1.0/Walldance-0.1.0.dmg",
        }]}
        page, feed = sync.prepare_release(release, self.page)
        self.assertEqual(page, self.page)
        self.assertIsNone(feed)
        with self.assertRaises(ValueError):
            sync.prepare_release(release, self.page.replace('data-version="0.1.0"', 'data-version="0.1.1"'))
