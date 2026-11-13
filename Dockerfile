FROM python:3.12-slim-bookworm

# Pin the driver from the installation this project is based on.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates curl libsane1 sane-utils libusb-0.1-4 libnsl2 \
    && curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        https://download.brother.com/pub/com/linux/linux/packages/brscan5-1.5.1-0.amd64.deb \
        --output /tmp/brscan5.deb \
    && echo '7ff1be6e407272843b41ddbf05889ea10cf16b83072a429f8fb443f4dda41ad8  /tmp/brscan5.deb' | sha256sum -c - \
    && dpkg -i /tmp/brscan5.deb \
    && rm /tmp/brscan5.deb /etc/opt/brother/scanner/brscan5/brsanenetdevice.cfg \
    && ln -s /work/brsanenetdevice.cfg /etc/opt/brother/scanner/brscan5/brsanenetdevice.cfg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 ds940 \
    && useradd --uid 1000 --gid 1000 --home-dir /work/home --no-create-home --shell /usr/sbin/nologin ds940

ENV HOME=/work/home \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ds940/ ds940/

LABEL org.opencontainers.image.title="ds-940-paperless-scanner" \
      org.opencontainers.image.description="Hands-free scan-to-folder receiver for the Brother DS-940DW Wi-Fi scanner" \
      org.opencontainers.image.source="https://github.com/ogmm/ds-940-paperless-scanner"

USER 1000:1000
ENTRYPOINT ["python", "-m", "ds940.supervisor"]
