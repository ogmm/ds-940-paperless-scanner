# Brother DS-940DW to NAS and Paperless-ngx

[Polski](README.md) · [Synology step-by-step guide in Polish](docs/synology.md)

**Power on, wait for the receiver, and insert one sheet.** A container on the NAS pulls both sides over Wi‑Fi and writes one PDF. Send it to a network share or the Paperless-ngx consumption folder for indexing and OCR. Daily scanning needs only the scanner and the NAS.

The DS-940DW almost went back in a return parcel. We liked the small duplex scanner and wanted the kind of scan-to-NAS workflow we knew from more expensive devices. The receiver filled that gap. Mail, invoices, and receipts can now go into our home archive as soon as they arrive.

## Set up the receiver

1. Connect the Brother DS-940DW to your LAN in Wi‑Fi mode and reserve its IPv4 address in the router. Use an **amd64 Linux** host with Docker Compose or an amd64 Synology with Container Manager.
2. Download the source. In its root folder, create `work` and `consume`, then copy `.env.example` to `.env`.
3. Set `SCANNER_IP`, `SCAN_UID`, and `SCAN_GID` in `.env`. The selected user must be able to write to both directories. To use a NAS share, point `SCAN_OUTPUT_DIR` to the share’s host path. For an existing Paperless installation, use the host path of its `/usr/src/paperless/consume` mount.
4. Run `docker compose config --quiet` and `docker compose up -d --build scanner`. On Synology, you can also create a Container Manager project from `compose.yaml` in the source folder.
5. Power on the scanner and wait for `Ready for paper` in `docker compose logs scanner`. Insert a single sheet face up and wait for it to exit before feeding the next one. Power off after the batch.

### Start a new Paperless-ngx stack

Create `export` alongside `work` and `consume`. Put random values in `POSTGRES_PASSWORD` and `PAPERLESS_SECRET_KEY` in the local `.env`. Set `PAPERLESS_BIND_IP` to the NAS LAN address if you need access from other devices. Start the combined project.

```sh
docker compose -f compose.yaml -f compose.paperless.yaml config --quiet
docker compose -f compose.yaml -f compose.paperless.yaml up -d --build
```

Open Paperless on the configured host and port (8010 by default), create the admin account, and try a sheet with a mark on each side. Paperless moves the finished PDF out of the intake directory during import. [Paperless-ngx setup guide](https://docs.paperless-ngx.com/setup/)

## Paper sizes and operation

- `a4` is the default. `auto` enables the driver's document size detection. `legal` requests a fixed scan area of about 355.6 mm in length. The scanner accepted both settings in the original installation. A roughly 35 cm receipt jammed in automatic mode. Physical capture of a full-length receipt in Legal mode remains unverified.
- After extended idle time the scanner can report a busy session, including `-NG 401`. The receiver backs off and retries. Keep the scanner off between batches and power-cycle it if a session becomes stuck.
- `work/spool` retains the captured images and finished PDFs. Review disk usage and archive old forwarded jobs after confirming import.

The Dockerfile fetches a pinned copy of Brother's driver during the build. Its terms come from Brother. The repository contains source and example settings for local builds. Run `python -m unittest discover -s tests -v` on Linux after installing `requirements-dev.txt`. [Brother downloads](https://support.brother.com/g/b/downloadlist.aspx?c=gb&lang=en&prod=ds940dw_us_eu_as&os=128)
