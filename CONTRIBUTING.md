# Contributing

Thanks for helping improve the DS-940DW scan receiver. Bug reports from real scanners, setup notes for other NAS systems, and fixes are all welcome.

## Report a problem

Open an issue with the **Bug report** form. Scanner problems are much easier to diagnose with:

- the host system and CPU architecture, for example Synology DSM 7.2 on x86-64 or Debian 13 on a mini PC,
- the output destination, such as a local folder, an SMB or NFS share, or Paperless-ngx,
- `SCAN_PAPER_SIZE` and the scanner's firmware version, if you know it,
- the last lines of `docker compose logs scanner` and the contents of `work/auto-status.json`.

Remove IP addresses, host names, and document names you don't want to share before you post logs. Report security problems privately, as described in [SECURITY.md](SECURITY.md).

## Develop and test

The receiver targets Python 3.12 on Linux. The tests replace Brother's driver with fakes, so they run without a scanner.

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

On macOS, or from WSL on Windows, run the same tests in a container:

```sh
docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD:/src" -w /src python:3.12-slim-bookworm \
  sh -c "pip install -q -r requirements-dev.txt && python -m unittest discover -s tests -v"
```

Before opening a pull request, also check that both Compose files resolve and that the image builds:

```sh
SCANNER_IP=192.0.2.42 docker compose config --quiet
SCANNER_IP=192.0.2.42 POSTGRES_PASSWORD=test PAPERLESS_SECRET_KEY=test \
  docker compose -f compose.yaml -f compose.paperless.yaml config --quiet
docker build --platform linux/amd64 -t ds-940-paperless-scanner:dev .
```

CI runs the same checks on every pull request.

## Pull requests

- Keep each pull request focused on one change and add tests for new behavior.
- Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/) style used in this repository, such as `fix: retry delivery after a share reconnects` or `docs: add an Unraid example`.
- If the change affects scanning, describe how you tested it on a physical scanner. A marked two-sided test sheet is a good check.
- Update the README or the guides in `docs/` when behavior or setup steps change. The translations in `docs/i18n/` follow [docs/synology.md](docs/synology.md). If you can't update a translation, mention it in the pull request.

Never commit `.env`, scans, or files from `work/`. The `.gitignore` excludes them by default.

## Code of conduct

Everyone taking part in this project is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
