"""Receiver settings and the brscan5 device registration."""

from dataclasses import dataclass
from ipaddress import IPv4Address
import os
from pathlib import Path


DPI = 300


@dataclass(frozen=True)
class Settings:
    scanner_ip: str
    work: Path
    output: Path
    paper_size: str

    @classmethod
    def from_environment(cls):
        address = os.environ.get("SCANNER_IP", "").strip()
        try:
            scanner_ip = str(IPv4Address(address))
        except ValueError as error:
            raise ValueError("SCANNER_IP must be the scanner's LAN IPv4 address") from error

        paper_size = os.environ.get("SCAN_PAPER_SIZE", "a4").strip().lower()
        if paper_size not in {"a4", "auto", "legal"}:
            raise ValueError("SCAN_PAPER_SIZE must be a4, auto, or legal")
        return cls(
            scanner_ip,
            Path(os.environ.get("WORK_DIR", "/work")),
            Path(os.environ.get("OUTPUT_DIR", "/consume")),
            paper_size,
        )

    def configure_driver(self):
        home = self.work / "home"
        home.mkdir(exist_ok=True)
        os.environ["HOME"] = str(home)
        (self.work / "brsanenetdevice.cfg").write_text(
            f'DEVICE=DS940 , "DS-940DW" , 0x4f9:0x46a , IP-ADDRESS={self.scanner_ip} , FLAG=\n',
            encoding="ascii",
        )
