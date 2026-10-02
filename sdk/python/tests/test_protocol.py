"""test_protocol.py — 0xA5 协议编解码双向测试（vectors.json 同固件向量）。

运行（stdlib-only，无需 pytest）::

    "E:/Program Files/KiCad/10.0/bin/python.exe" sdk/python/tests/test_protocol.py

覆盖：
1. 8 组向量 encode -> 期望字节串（黄金字节）；
2. 同 8 组 decode 往返 == {cmd, ports, pwm}；
3. CRC 独立锚点（CRC-8/ATM 检查值 0xF4）；
4. 坏 CRC / 坏魔数 / 坏长度 / 参数越界的错误路径。
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # sdk/python 入包路径

from flowio_sdk import ProtocolError, crc8, decode, encode  # noqa: E402

VECTORS_PATH = Path(__file__).with_name("vectors.json")


def _load_vectors():
    with VECTORS_PATH.open("r", encoding="utf-8") as f:
        blob = json.load(f)
    return blob["crc_anchors"], blob["vectors"]


CRC_ANCHORS, VECTORS = _load_vectors()


class TestCrcAnchors(unittest.TestCase):
    def test_independent_check_value(self):
        # CRC-8/ATM 标准检查值——多项式/初值/移位方向被第三方结果钉死
        self.assertEqual(f"{crc8(b'123456789'):02x}", CRC_ANCHORS["123456789"])

    def test_single_magic_byte(self):
        # firmware/tests/test_proto.c t_crc_known_vector: 单字节 0xA5 定值防手滑改多项式
        magic = b"\xA5"
        self.assertEqual(f"{crc8(magic):02x}", CRC_ANCHORS["a5"])


class TestEncodeGoldenFrames(unittest.TestCase):
    def test_encode_matches_golden_bytes(self):
        for v in VECTORS:
            with self.subTest(vector=v["name"]):
                frame = encode(v["cmd"], v["ports"], v["pwm"])
                self.assertEqual(frame.hex(), v["frame_hex"])
                self.assertEqual(len(frame), 5)
                self.assertEqual(frame[0], 0xA5)  # PN_PROTO_MAGIC


class TestDecodeRoundtrip(unittest.TestCase):
    def test_decode_golden_frames(self):
        for v in VECTORS:
            with self.subTest(vector=v["name"]):
                got = decode(bytes.fromhex(v["frame_hex"]))
                self.assertEqual(got["cmd"], v["cmd"])
                self.assertEqual(got["cmd_byte"], ord(v["cmd"]))
                self.assertEqual(got["ports"], v["ports"])
                self.assertEqual(got["pwm"], v["pwm"])

    def test_roundtrip_encode_decode(self):
        for v in VECTORS:
            with self.subTest(vector=v["name"]):
                got = decode(encode(v["cmd"], v["ports"], v["pwm"]))
                self.assertEqual(
                    (got["cmd"], got["ports"], got["pwm"]),
                    (v["cmd"], v["ports"], v["pwm"]),
                )


class TestErrorPaths(unittest.TestCase):
    def test_bad_crc_rejected(self):
        frame = bytearray(encode("+", 1, 200))
        frame[4] ^= 0xFF  # firmware t_bad_crc_dropped 同款破坏法
        with self.assertRaises(ProtocolError):
            decode(bytes(frame))

    def test_bad_magic_rejected(self):
        frame = bytearray(encode("!", 1, 0))
        frame[0] = 0x5A
        with self.assertRaises(ProtocolError):
            # 重新算 CRC 排除 CRC 因素，专测魔数
            frame[4] = crc8(bytes(frame[:4]))
            decode(bytes(frame))

    def test_bad_length_rejected(self):
        with self.assertRaises(ProtocolError):
            decode(encode("+", 1, 200)[:4])
        with self.assertRaises(ProtocolError):
            decode(encode("+", 1, 200) + b"\x00")

    def test_param_out_of_range(self):
        with self.assertRaises(ValueError):
            encode("+", 0x100, 0)
        with self.assertRaises(ValueError):
            encode("+", 0, 256)
        with self.assertRaises(ValueError):
            encode("++", 0, 0)  # cmd 必须单字符


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    if result.wasSuccessful():
        print("sdk protocol tests OK")
        sys.exit(0)
    sys.exit(1)
