"""ETAG command framing and image packets."""

import struct

from .image import encode


def packets(image, firmware):
    # APK SendPublishTemplateActivity.h2, type 1. These are app commands,
    # not Bluetooth pairing or firmware flashing.
    yield bytes.fromhex("ac05ca")
    yield bytes.fromhex("ac1100112233445566778899112233445566ca")
    yield bytes.fromhex("ac07ca")
    for plane, data in enumerate(encode(image, firmware)):
        count = (len(data) + 229) // 230
        for index in range(count):
            chunk = data[index * 230 : (index + 1) * 230]
            yield struct.pack(">BBBHHH", 0xAC, 1, plane, index, count, len(chunk)) + chunk + b"\xca"
    yield bytes.fromhex("ac03ca")
