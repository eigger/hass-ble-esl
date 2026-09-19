"""Tests for PickSmart QuickLZ Level 1 chunked compression and decompression."""

from __future__ import annotations

from custom_components.ble_esl.esl_ble.picksmart.compression import (
    _qlz_compress_core,
    _qlz_decompress_core,
    compress,
    decompress,
)


def test_quicklz_core_roundtrip():
    """Verify single 64-byte chunk QuickLZ L1 core compression roundtrip."""
    chunk = b"A" * 64
    compressed = _qlz_compress_core(chunk)
    assert compressed is not None
    decompressed = _qlz_decompress_core(compressed, 64)
    assert decompressed == chunk


def test_quicklz_full_compress_decompress_roundtrip():
    """Verify multi-part QuickLZ Level 1 compress2 roundtrip."""
    chunk = b"PIC_SMART_TEST_DATA_64B_CHUNK__" * 2  # 64 bytes
    payload = chunk * 20  # 1280 bytes -> part1 640B, part2 640B

    compressed = compress(payload)
    decompressed = decompress(compressed)
    assert decompressed == payload


def test_quicklz_force_raw():
    """Verify raw fallback (0x74 chunks) roundtrip."""
    chunk = b"RAW_UNCOMPRESSED_CHUNK_64_BYTES_" * 2  # 64 bytes
    payload = chunk * 10  # 640 bytes

    compressed_raw = compress(payload, force_raw=True)
    assert compressed_raw[4] == 0x74  # First chunk is raw
    decompressed = decompress(compressed_raw)
    assert decompressed == payload
