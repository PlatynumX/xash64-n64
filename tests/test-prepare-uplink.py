#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare-uplink.py"

spec = importlib.util.spec_from_file_location("prepare_uplink", SCRIPT)
assert spec and spec.loader
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


def write_bsp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<i", 30) + b"synthetic-not-valve-data")


def write_pak(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, bytes]] = []
    for name in prep.MAPS:
        entries.append((f"maps/{name}", struct.pack("<i", 30) + f"synthetic-{name}".encode()))
    entries.append(("sound/synthetic.wav", b"not-valve-data"))

    payload = bytearray(b"PACK" + b"\0" * 8)
    directory_rows: list[bytes] = []
    for name, data in entries:
        offset = len(payload)
        payload.extend(data)
        encoded = name.encode("ascii")
        assert len(encoded) < 56
        directory_rows.append(encoded + b"\0" * (56 - len(encoded)) + struct.pack("<ii", offset, len(data)))
    dir_offset = len(payload)
    directory = b"".join(directory_rows)
    payload.extend(directory)
    payload[4:12] = struct.pack("<ii", dir_offset, len(directory))
    path.write_bytes(payload)


def test_mirror_parser() -> None:
    html = '''<html><body><a href="/downloads/mirror/70848/124/token">download hluplink.exe</a></body></html>'''
    got = prep.parse_moddb_mirror_link(html)
    assert got == "https://www.moddb.com/downloads/mirror/70848/124/token", got


def test_prepare_from_directory() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-test-") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "source" / "valve"
        for name in prep.MAPS:
            write_bsp(source / "maps" / name)
        (source / "liblist.gam").write_text("game Half-Life Uplink\n", encoding="utf-8")
        dest = tmp / "sd"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(tmp / "source"), str(dest)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout
        for name in prep.MAPS:
            assert (dest / "xash" / "valve" / "maps" / name).is_file()
        assert (dest / "xash" / "uplink-manifest.txt").is_file()


def test_prepare_from_pak() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-pak-test-") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "source" / "MAINDIR" / "valve"
        write_pak(source / "pak0.pak")
        (source / "liblist.gam").write_text("game Half-Life Uplink\n", encoding="utf-8")

        assert prep.find_data_roots(tmp / "source") == [source]
        mode, pak = prep.verify_uplink_root(source)
        assert mode == "pak"
        assert pak == source / "pak0.pak"

        dest = tmp / "sd"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(tmp / "source"), str(dest)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        assert proc.returncode == 0, proc.stdout
        assert (dest / "xash" / "valve" / "pak0.pak").is_file()
        assert not (dest / "xash" / "valve" / "maps" / "hldemo1.bsp").exists()
        manifest = (dest / "xash" / "uplink-manifest.txt").read_text(encoding="utf-8")
        assert "pak0.pak::maps/hldemo1.bsp" in manifest
        assert "pak0.pak::maps/hldemo2.bsp" in manifest
        assert "pak0.pak::maps/hldemo3.bsp" in manifest


def test_download_cli_shape() -> None:
    source, dest, download, force, cache = prep.parse_args(
        ["--download", "/tmp/sd", "--force", "--cache-dir", "/tmp/cache"]
    )
    assert source is None
    assert dest == Path("/tmp/sd")
    assert download is True
    assert force is True
    assert cache == Path("/tmp/cache")


def test_signature_scanner() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-signature-") as tmp_name:
        path = Path(tmp_name) / "fake.exe"
        data = b"MZ" + b"A" * 127 + b"ISc(" + b"B" * 257 + b"MSCF"
        path.write_bytes(data)
        hits = prep.signature_offsets(path)
        assert hits["InstallShield CAB"] == [129]
        assert hits["Microsoft CAB"] == [390]


def test_valid_pe_scanner_rejects_random_mz_noise() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-pe-") as tmp_name:
        path = Path(tmp_name) / "fake.exe"
        data = bytearray(1024)
        data[0:2] = b"MZ"
        data[0x3C:0x40] = (0x80).to_bytes(4, "little")
        data[0x80:0x84] = b"PE\0\0"
        data[300:302] = b"MZ"
        data[300 + 0x3C:300 + 0x40] = (0xDEADBEEF).to_bytes(4, "little")
        path.write_bytes(data)
        assert prep.valid_pe_offsets(path) == [0]


def test_wise_detection() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-wise-detect-") as tmp_name:
        wise = Path(tmp_name) / "wise.exe"
        wise.write_bytes(b"MZ" + b"x" * 64 + b"Initializing Wise Installation Wizard...")
        plain = Path(tmp_name) / "plain.exe"
        plain.write_bytes(b"MZ-not-wise")
        assert prep.looks_like_wise_installer(wise)
        assert not prep.looks_like_wise_installer(plain)


def test_cabextract_route_and_output_check() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-cabextract-") as tmp_name:
        tmp = Path(tmp_name)
        bindir = tmp / "bin"
        bindir.mkdir()
        fake = bindir / "cabextract"
        fake.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -d) out=$2; shift 2 ;;\n"
            "    *) shift ;;\n"
            "  esac\n"
            "done\n"
            "mkdir -p \"$out\"\n"
            "printf extracted > \"$out/from-cabextract.bin\"\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        source = tmp / "fake.exe"
        source.write_bytes(b"MZ-not-a-real-installer")
        out = tmp / "out"
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bindir}:{old_path}"
        try:
            assert prep.try_cabextract(source, out)
        finally:
            os.environ["PATH"] = old_path
        assert (out / "cabextract" / "from-cabextract.bin").is_file()




def test_rewise_route_and_output_check() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-rewise-") as tmp_name:
        tmp = Path(tmp_name)
        bindir = tmp / "bin"
        bindir.mkdir()
        fake = bindir / "rewise"
        fake.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "op=$1\n"
            "case \"$op\" in\n"
            "  -l) [ \"$2\" = '-t' ]; tmp=$3; [ -d \"$tmp\" ]; [ -w \"$tmp\" ]; echo 'maps/hldemo1.bsp' ;;\n"
            "  -x) out=$2; [ \"$3\" = '-t' ]; tmp=$4; [ -d \"$tmp\" ]; [ -w \"$tmp\" ]; mkdir -p \"$out/valve/maps\"; printf fake > \"$out/valve/maps/hldemo1.bsp\" ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        source = tmp / "wise.exe"
        source.write_bytes(b"MZ-synthetic-wise-wrapper")
        out = tmp / "out"
        cache = tmp / "cache"
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bindir}:{old_path}"
        try:
            assert prep.try_rewise(source, out, cache)
        finally:
            os.environ["PATH"] = old_path
        assert (out / "rewise" / "valve" / "maps" / "hldemo1.bsp").is_file()
        assert (cache / "tmp" / "rewise").is_dir()


def test_rewise_release_pin() -> None:
    assert prep.REWISE_VERSION == "0.3.1"
    assert prep.REWISE_GIT_TAG == "v0.3.1"
    assert prep.REWISE_GIT_URL == "https://codeberg.org/CYBERDEV/REWise.git"


def test_wise_bootstrap_failure_is_not_hidden_by_generic_extractors() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-wise-stop-") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "wise.exe"
        source.write_bytes(b"MZ" + b"x" * 64 + b"WiseMain")
        out = tmp / "out"
        cache = tmp / "cache"

        original = prep.bootstrap_rewise
        def fail_bootstrap(_cache: Path) -> Path:
            raise prep.PrepError("synthetic REWise bootstrap failure")
        prep.bootstrap_rewise = fail_bootstrap
        try:
            try:
                prep.extract_one(source, out, cache)
            except prep.PrepError as exc:
                assert "synthetic REWise bootstrap failure" in str(exc)
            else:
                raise AssertionError("Wise bootstrap failure was incorrectly swallowed")
        finally:
            prep.bootstrap_rewise = original


def test_rewise_cmake_bootstrap_with_synthetic_source() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-rewise-build-") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "synthetic-rewise"
        source.mkdir()
        (source / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.10)\n"
            "project(rewise C)\n"
            "add_executable(rewise rewise.c)\n",
            encoding="utf-8",
        )
        (source / "rewise.c").write_text(
            '#include <stdio.h>\n'
            'int main(int argc, char **argv) { (void)argc; (void)argv; puts("REWise 0.3.1 synthetic"); return 0; }\n',
            encoding="utf-8",
        )
        cache = tmp / "cache"
        original_prepare = prep._prepare_rewise_source
        original_which = prep.shutil.which

        # Prevent a host-installed rewise from bypassing the bootstrap while
        # leaving compiler/cmake/git discovery untouched.
        def filtered_which(name: str):
            if name == "rewise":
                return None
            return original_which(name)

        prep._prepare_rewise_source = lambda _cache: (source, "0" * 40)
        prep.shutil.which = filtered_which
        try:
            built = prep.bootstrap_rewise(cache)
        finally:
            prep._prepare_rewise_source = original_prepare
            prep.shutil.which = original_which
        assert built.is_file()
        assert os.access(built, os.X_OK)
        log = prep.rewise_log_path(cache).read_text(encoding="utf-8")
        assert "REWise CMake configure" in log
        assert "REWise CMake build" in log
        assert "REWise version check" in log


def test_installer_cache_validation_without_real_demo() -> None:
    with tempfile.TemporaryDirectory(prefix="xash64-cache-") as tmp_name:
        path = Path(tmp_name) / "tiny.exe"
        content = b"synthetic"
        path.write_bytes(content)
        old_size = prep.UPLINK_INSTALLER_SIZE
        old_md5 = prep.UPLINK_INSTALLER_MD5
        prep.UPLINK_INSTALLER_SIZE = len(content)
        prep.UPLINK_INSTALLER_MD5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
        try:
            assert prep.installer_matches(path)
        finally:
            prep.UPLINK_INSTALLER_SIZE = old_size
            prep.UPLINK_INSTALLER_MD5 = old_md5


if __name__ == "__main__":
    test_mirror_parser()
    test_prepare_from_directory()
    test_prepare_from_pak()
    test_download_cli_shape()
    test_signature_scanner()
    test_valid_pe_scanner_rejects_random_mz_noise()
    test_wise_detection()
    test_cabextract_route_and_output_check()
    test_rewise_route_and_output_check()
    test_rewise_release_pin()
    test_wise_bootstrap_failure_is_not_hidden_by_generic_extractors()
    test_rewise_cmake_bootstrap_with_synthetic_source()
    test_installer_cache_validation_without_real_demo()
    print("test-prepare-uplink: PASS")
