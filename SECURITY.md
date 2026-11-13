# Security policy

## Supported versions

Security fixes go into the latest commit on `main`. Update your installation as described in the [Docker guide](docs/docker.md#update-the-receiver).

## Report a vulnerability

Please don't open a public issue for security problems. Use GitHub's private reporting instead: open the **Security** tab of this repository and choose **Report a vulnerability**. Include the affected file or setting, steps to reproduce, and the impact you expect.

You will get a reply as soon as the maintainer can look at it. Once a fix is available, the advisory will be published with credit to you, unless you prefer to stay anonymous.

## Scope

In scope are the receiver code in `ds940/`, the Dockerfile, and the Compose files in this repository.

Report problems in Brother's `brscan5` driver or the scanner firmware to Brother, and problems in Paperless-ngx to the [Paperless-ngx project](https://github.com/paperless-ngx/paperless-ngx/security).

## Deployment notes

- Keep the scanner and the receiver on a trusted local network. The scanner protocol is not encrypted, and the receiver does not open any listening ports.
- The included Paperless-ngx stack listens only on `127.0.0.1` unless you set `PAPERLESS_BIND_IP`. Don't expose it to the internet without a reverse proxy with TLS.
- Keep `.env` private, for example with `chmod 600 .env`. It holds the database password and the Paperless-ngx secret key.
