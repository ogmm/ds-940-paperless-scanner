"""The brscan5 SANE session used for one poll or one duplex scan."""

import ctypes as C

from .config import DPI


DEVICE_BUSY = 3
EOF = 5
JAMMED = 6
NO_DOCS = 7
COVER_OPEN = 8
FIXED_SCALE = 1 << 16
PIXEL_MM = 25.4 / DPI
INACTIVE = 1 << 5


class SaneFailure(RuntimeError):
    def __init__(self, action, status):
        self.action = action
        self.status = status
        super().__init__(f"SANE {action} returned status {status}")


class DeviceDescriptor(C.Structure):
    _fields_ = [
        ("name", C.c_char_p),
        ("vendor", C.c_char_p),
        ("model", C.c_char_p),
        ("type", C.c_char_p),
    ]


class OptionDescriptor(C.Structure):
    _fields_ = [
        ("name", C.c_char_p),
        ("title", C.c_char_p),
        ("description", C.c_char_p),
        ("type", C.c_int),
        ("unit", C.c_int),
        ("size", C.c_int),
        ("cap", C.c_int),
        ("constraint_type", C.c_int),
        ("constraint", C.c_void_p),
    ]


class OptionRange(C.Structure):
    _fields_ = [("minimum", C.c_int), ("maximum", C.c_int), ("quantization", C.c_int)]


class FrameParameters(C.Structure):
    _fields_ = [
        ("format", C.c_int),
        ("last_frame", C.c_int),
        ("bytes_per_line", C.c_int),
        ("pixels_per_line", C.c_int),
        ("lines", C.c_int),
        ("depth", C.c_int),
    ]


class SaneDevice:
    def __init__(self, paper_size):
        self.lib = C.CDLL("libsane.so.1")
        self.handle = C.c_void_p()
        self.initialized = False
        self.opened = False
        self.active = False
        device_list = C.POINTER(C.POINTER(DeviceDescriptor))
        signatures = {
            "sane_init": [C.POINTER(C.c_int), C.c_void_p],
            "sane_get_devices": [C.POINTER(device_list), C.c_int],
            "sane_open": [C.c_char_p, C.POINTER(C.c_void_p)],
            "sane_get_option_descriptor": [C.c_void_p, C.c_int],
            "sane_control_option": [C.c_void_p, C.c_int, C.c_int, C.c_void_p, C.POINTER(C.c_int)],
            "sane_start": [C.c_void_p],
            "sane_get_parameters": [C.c_void_p, C.POINTER(FrameParameters)],
            "sane_read": [C.c_void_p, C.c_void_p, C.c_int, C.POINTER(C.c_int)],
            "sane_cancel": [C.c_void_p],
            "sane_close": [C.c_void_p],
            "sane_exit": [],
        }
        for name, signature in signatures.items():
            getattr(self.lib, name).argtypes = signature
        self.lib.sane_get_option_descriptor.restype = C.POINTER(OptionDescriptor)
        for name in ("sane_cancel", "sane_close", "sane_exit"):
            getattr(self.lib, name).restype = None

        try:
            version = C.c_int()
            self.check(self.lib.sane_init(C.byref(version), None), "init")
            self.initialized = True
            devices = device_list()
            self.check(self.lib.sane_get_devices(C.byref(devices), 0), "enumerate")
            self.check(self.lib.sane_open(b"brother5:net1;dev0", C.byref(self.handle)), "open")
            self.opened = True
            self.set_option("mode", "24bit Color[Fast]")
            self.set_option("resolution", DPI)
            _, source = self.option("source")
            if source.constraint_type != 3 or not source.constraint:
                raise RuntimeError("brscan5 did not provide a feeder list")
            choices = C.cast(source.constraint, C.POINTER(C.c_char_p))
            for index in range(32):
                choice = choices[index]
                if not choice:
                    break
                if b"duplex" in choice.lower():
                    self.set_option("source", choice.decode())
                    break
            else:
                raise RuntimeError("brscan5 feeder list is missing its terminator")
            if not choice or b"duplex" not in choice.lower():
                raise RuntimeError("brscan5 did not offer a duplex feeder")

            self.geometry = self.configure_size(paper_size)
            self.set_option("SkipBlankPage", 0, optional=True)
        except Exception:
            self.close()
            raise

    @staticmethod
    def check(status, action):
        if status:
            raise SaneFailure(action, status)

    def option(self, name):
        count = C.c_int()
        info = C.c_int()
        self.check(
            self.lib.sane_control_option(self.handle, 0, 0, C.byref(count), C.byref(info)),
            "read option count",
        )
        for index in range(count.value):
            pointer = self.lib.sane_get_option_descriptor(self.handle, index)
            if pointer and pointer.contents.name == name.encode():
                return index, pointer.contents
        raise KeyError(f"SANE option {name} is unavailable")

    def set_option(self, name, value, *, optional=False):
        try:
            index, descriptor = self.option(name)
        except KeyError:
            if optional:
                return
            raise
        if descriptor.cap & INACTIVE:
            if optional:
                return
            raise RuntimeError(f"SANE option {name} is inactive")
        if descriptor.type == 3:
            data = C.create_string_buffer(value.encode(), descriptor.size)
        else:
            number = round(value * FIXED_SCALE) if descriptor.type == 2 else int(value)
            data = C.c_int(number)
        info = C.c_int()
        self.check(
            self.lib.sane_control_option(self.handle, index, 1, C.byref(data), C.byref(info)),
            f"set {name}",
        )

    def read_word(self, name):
        index, descriptor = self.option(name)
        value = C.c_int()
        if descriptor.size != C.sizeof(value):
            raise RuntimeError(f"Unexpected SANE option size for {name}")
        info = C.c_int()
        self.check(
            self.lib.sane_control_option(self.handle, index, 0, C.byref(value), C.byref(info)),
            f"read {name}",
        )
        return value.value

    def configure_size(self, paper_size):
        if paper_size == "auto":
            _, descriptor = self.option("br-y")
            if (
                descriptor.type != 2
                or descriptor.unit != 3
                or descriptor.constraint_type != 1
                or not descriptor.constraint
            ):
                raise RuntimeError("brscan5 did not report the duplex length range")
            length_range = C.cast(descriptor.constraint, C.POINTER(OptionRange)).contents
            max_height = length_range.maximum / FIXED_SCALE
            self.set_option("AutoDocumentSize", 1)
            if self.read_word("AutoDocumentSize") != 1:
                raise RuntimeError("brscan5 did not enable automatic document size")
            return f"automatic size, advertised maximum {max_height:.2f} mm"

        if paper_size == "a4":
            self.set_option("br-x", 210.0)
            self.set_option("br-y", 297.0)
            return "A4 (210 x 297 mm)"

        self.set_option("AutoDocumentSize", 0)
        if self.read_word("AutoDocumentSize") != 0:
            raise RuntimeError("brscan5 did not disable automatic document size for Legal")
        self.set_option("br-x", 215.9)
        self.set_option("br-y", 355.6)
        width = self.read_word("br-x") / FIXED_SCALE
        height = self.read_word("br-y") / FIXED_SCALE
        # brscan5 rounds these coordinates to its own scan area increments.
        if abs(width - 215.9) > PIXEL_MM or abs(height - 355.6) > PIXEL_MM:
            raise RuntimeError(f"brscan5 returned {width:.2f} x {height:.2f} mm for Legal")
        return f"Legal ({width:.2f} x {height:.2f} mm)"

    def start(self):
        # Even a NO_DOCS result can leave a vendor session to release.
        self.active = True
        return self.lib.sane_start(self.handle)

    def parameters(self):
        params = FrameParameters()
        self.check(self.lib.sane_get_parameters(self.handle, C.byref(params)), "parameters")
        return params

    def read(self):
        buffer = C.create_string_buffer(65536)
        size = C.c_int()
        status = self.lib.sane_read(self.handle, buffer, len(buffer), C.byref(size))
        if not 0 <= size.value <= len(buffer):
            raise RuntimeError("Invalid SANE read size")
        return status, buffer.raw[:size.value]

    def cancel(self):
        if self.opened and self.active:
            self.lib.sane_cancel(self.handle)
            self.active = False

    def close(self):
        if self.opened:
            self.cancel()
            self.lib.sane_close(self.handle)
            self.opened = False
        if self.initialized:
            self.lib.sane_exit()
            self.initialized = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
