# Repository guidelines

Walldance is a static landing page following the design of `../cococut-site`: warm background, centered type, one download button, and three feature columns. Deploy `public/` directly; there is no build step or runtime script.

- `public/` contains the page, styles, app icon, and published signed appcast when available.
- `scripts/update-release.py` updates the download link and copies a published release's appcast.

Use two spaces in HTML/CSS and four spaces in Python. Keep dependencies at zero. Preserve keyboard focus, mobile layout, and reduced-motion styles. Never modify signed appcast bytes or expose drafts or prereleases. Run `python3 -m unittest discover -s test -v` and `git diff --check` after changes. Keep the page version, DMG link, and appcast aligned.

## Releases and Site Updates

For every new app version, remind the user that publishing the GitHub release and updating this static site are separate steps:

1. In `../walldance`, update `CHANGELOG.md`, commit, and push a version tag such as `v0.1.2`. CI creates a draft GitHub release with the notarized DMG and signed `appcast.xml`.
2. Keep the release as a draft for review unless explicitly asked to publish. Sync the site only after the stable release is published.
3. In this repository, run `python3 scripts/update-release.py v0.1.2`, using the actual published tag. This updates the download link and copies the signed feed unchanged into `public/appcast.xml`.
4. Review, commit, push, and redeploy `public/` to `https://walldance.souk.dev` using static hosting.

DMGs download from GitHub Releases. The site hosts the page and update feed. Installed apps discover the new version only after the updated feed is deployed. Keep published DMGs available for clients with older feeds.
