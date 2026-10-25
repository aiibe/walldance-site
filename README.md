# Walldance site

Static landing page and signed update feed for **https://walldance.souk.dev**. No JavaScript, dependencies, or build step. Deploy `public/` to any static host.

For local preview: `python3 -m http.server 8000 --directory public`.

Serve `public/` at **walldance.souk.dev** over HTTPS. Serve `/appcast.xml` unchanged as XML and configure its cache to revalidate after deployment.

After publishing a stable app release on GitHub:

```sh
python3 scripts/update-release.py v0.1.1
```

This updates the page's direct DMG link and copies the release's signed `appcast.xml` into `public/` without changing its bytes. Review, commit, push, and redeploy the site. Drafts and prereleases are rejected. Omit the tag to select the latest published stable release.

The current page links to 0.1.0, which predates in-app updates. `/appcast.xml` will be available after the first updater-enabled release is published and synced. Keep published DMGs available on GitHub for apps that already fetched older feeds.

Run `python3 -m unittest discover -s test -v` to check release synchronization.
