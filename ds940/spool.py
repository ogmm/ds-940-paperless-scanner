"""Durable scan staging and publication to the watched directory."""

from contextlib import ExitStack
from filecmp import cmp
import json
import logging
import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

from PIL import Image

from .config import DPI


LOG = logging.getLogger(__name__)


def atomic_json(path, value, *, durable=False):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        if durable:
            stream.flush()
            os.fsync(stream.fileno())
    temporary.replace(path)


def build_pdf(images, target):
    with ExitStack() as stack:
        pages = [stack.enter_context(Image.open(path)) for path in images]
        temporary = target.with_suffix(".pdf.part")
        with temporary.open("xb") as stream:
            pages[0].save(
                stream, format="PDF", resolution=DPI, save_all=True, append_images=pages[1:]
            )
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)


class ScanSpool:
    def __init__(self, work, output):
        self.work = Path(work)
        self.output = Path(output)
        if not self.output.is_dir() or not os.access(self.output, os.W_OK | os.X_OK):
            raise ValueError("The output directory must be mounted and writable")
        self.jobs = self.work / "spool"
        self.jobs.mkdir(exist_ok=True)

    def new_scan(self):
        name = time.strftime("brother-%Y%m%d-%H%M%S-", time.gmtime()) + uuid4().hex[:8]
        folder = self.jobs / name
        folder.mkdir()
        return folder

    def publish(self, folder):
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["phase"] != "ready":
            return False

        source = folder / "document.pdf"
        target = self.output / f"{folder.name}.pdf"
        temporary = self.output / f".{folder.name}.part"
        with source.open("rb") as document:
            if document.read(5) != b"%PDF-":
                raise ValueError("Invalid staged PDF")
            if target.exists():
                if not cmp(source, target, shallow=False):
                    raise FileExistsError(f"Output already contains a different {target.name}")
            else:
                document.seek(0)
                with temporary.open("wb") as stream:
                    shutil.copyfileobj(document, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(target)
        manifest.update(phase="forwarded", destination=target.name)
        atomic_json(manifest_path, manifest, durable=True)
        atomic_json(self.work / "last-scan.json", manifest, durable=True)
        LOG.info("Delivered %s (%d pages)", target.name, manifest["pages"])
        return True

    def recover(self):
        for manifest in sorted(self.jobs.glob("brother-*/manifest.json")):
            if manifest.is_symlink() or manifest.parent.is_symlink():
                continue
            try:
                self.publish(manifest.parent)
            except (OSError, ValueError, KeyError, TypeError):
                LOG.exception("Could not publish %s. The spool still holds the scan.", manifest.parent.name)
