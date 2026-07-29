#!/usr/bin/env python3
"""Download/extract and prepare Half-Life: Uplink data for Xash64/N64.

Two modes are supported:

  prepare-uplink.py SOURCE DEST [--force]
  prepare-uplink.py --download DEST [--force]

Download mode retrieves the original public Half-Life: Uplink demo installer
from ModDB's current mirror flow, verifies the published installer MD5 and byte
size, caches the verified EXE, then tries several extraction paths suitable for
late-1990s Windows self-extractors. No Valve game data is stored in this repo.
"""
from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import hashlib
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

MAPS = ("hldemo1.bsp", "hldemo2.bsp", "hldemo3.bsp")
BSP_VERSION = 30

MODDB_START_URL = "https://www.moddb.com/downloads/start/70848"
MODDB_MIRROR_PREFIX = "/downloads/mirror/70848/"
UPLINK_INSTALLER_NAME = "hluplink.exe"
UPLINK_INSTALLER_SIZE = 50_872_079
UPLINK_INSTALLER_MD5 = "498afa6af130a64ff5966774654b0f18"

# The user's r5 diagnostic proves the Uplink wrapper itself is Wise: its PE
# contains both "WiseMain" and "Initializing Wise Installation Wizard...".
# REWise is purpose-built for this exact installer family. r8 pins the release
# tag and clones it with git instead of trusting a forge-generated tarball hash
# that proved brittle in r5; the exact cloned commit is recorded in the log.
REWISE_VERSION = "0.3.1"
REWISE_GIT_URL = "https://codeberg.org/CYBERDEV/REWise.git"
REWISE_GIT_TAG = f"v{REWISE_VERSION}"
USER_AGENT = "Mozilla/5.0 (Xash64-N64 Uplink preparer; +https://github.com/FWGS/xash3d-fwgs)"

# These are diagnostic markers only. Presence of a marker is not treated as
# proof that the surrounding bytes form a valid archive.
SIGNATURES: tuple[tuple[str, bytes], ...] = (
    ("Microsoft CAB", b"MSCF"),
    ("InstallShield CAB", b"ISc("),
    ("ZIP local header", b"PK\x03\x04"),
    ("InstallShield text", b"InstallShield"),
    ("PackageForTheWeb text", b"PackageForTheWeb"),
    ("WiseMain", b"WiseMain"),
    ("Wise wizard text", b"Wise Installation Wizard"),
    ("Wise installer text", b"Wise Installation System"),
    ("UNWISE text", b"UNWISE"),
)


class PrepError(RuntimeError):
    pass


class MirrorLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and MODDB_MIRROR_PREFIX in href:
            self.hrefs.append(href)


def bsp_version(path: Path) -> int:
    with path.open("rb") as handle:
        raw = handle.read(4)
    if len(raw) != 4:
        raise PrepError(f"BSP is too short to contain a header: {path}")
    return struct.unpack("<i", raw)[0]


def _pak_directory(pak_path: Path) -> dict[str, tuple[int, int]]:
    """Return a normalized Half-Life/Quake PAK directory.

    PAK files use a 12-byte PACK header followed by 64-byte directory records:
    56-byte path, little-endian file offset, little-endian file length.
    """
    try:
        size = pak_path.stat().st_size
        with pak_path.open("rb") as handle:
            header = handle.read(12)
            if len(header) != 12 or header[:4] != b"PACK":
                return {}
            dir_offset, dir_length = struct.unpack("<ii", header[4:12])
            if dir_offset < 0 or dir_length < 0 or dir_length % 64 != 0:
                return {}
            if dir_offset + dir_length > size:
                return {}
            handle.seek(dir_offset)
            directory: dict[str, tuple[int, int]] = {}
            for _ in range(dir_length // 64):
                raw = handle.read(64)
                if len(raw) != 64:
                    return {}
                name_raw, file_offset, file_length = raw[:56], *struct.unpack("<ii", raw[56:64])
                if file_offset < 0 or file_length < 0 or file_offset + file_length > size:
                    return {}
                name = name_raw.split(b"\0", 1)[0].decode("latin-1", errors="replace")
                name = name.replace("\\", "/").lstrip("/").lower()
                if name:
                    directory[name] = (file_offset, file_length)
            return directory
    except OSError:
        return {}


def _pak_uplink_maps(pak_path: Path) -> dict[str, tuple[int, int]]:
    directory = _pak_directory(pak_path)
    found: dict[str, tuple[int, int]] = {}
    for name in MAPS:
        key = f"maps/{name}".lower()
        if key in directory:
            found[name] = directory[key]
    return found


def find_uplink_pak(game_root: Path) -> Path | None:
    try:
        candidates = [p for p in game_root.iterdir() if p.is_file() and p.suffix.lower() == ".pak"]
    except OSError:
        return None
    for pak in sorted(candidates, key=lambda p: p.name.lower()):
        if len(_pak_uplink_maps(pak)) == len(MAPS):
            return pak
    return None


def find_data_roots(root: Path) -> list[Path]:
    candidates: set[Path] = set()

    # Some extracted/modern layouts expose BSPs directly.
    for map1 in root.rglob(MAPS[0]):
        if map1.parent.name.lower() != "maps":
            continue
        game_root = map1.parent.parent
        if all((game_root / "maps" / name).is_file() for name in MAPS):
            candidates.add(game_root)

    # Original WON-era Half-Life content normally keeps game assets, including
    # maps, inside pak0.pak. r8 only searched for loose maps, so it could
    # successfully extract Uplink and then walk straight past the real data.
    for pak in root.rglob("*"):
        if pak.is_file() and pak.suffix.lower() == ".pak" and len(_pak_uplink_maps(pak)) == len(MAPS):
            candidates.add(pak.parent)

    return sorted(candidates, key=lambda p: (len(p.parts), str(p).lower()))


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "text/html,application/octet-stream;q=0.9,*/*;q=0.8"),
    ]
    return opener


def parse_moddb_mirror_link(page_html: str, base_url: str = MODDB_START_URL) -> str:
    parser = MirrorLinkParser()
    parser.feed(page_html)
    if parser.hrefs:
        return urllib.parse.urljoin(base_url, parser.hrefs[0])

    # Defensive fallback in case ModDB slightly changes markup but keeps its mirror URL scheme.
    match = re.search(r'''href=["']([^"']*/downloads/mirror/70848/[^"']+)["']''', page_html, re.I)
    if match:
        return urllib.parse.urljoin(base_url, match.group(1))
    raise PrepError("ModDB download page did not contain the expected Uplink mirror link.")


def default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return base / "xash64-n64"


def installer_matches(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        if path.stat().st_size != UPLINK_INSTALLER_SIZE:
            return False
        return md5_file(path).lower() == UPLINK_INSTALLER_MD5
    except OSError:
        return False


def download_uplink_installer(cache_root: Path) -> Path:
    cache_root.mkdir(parents=True, exist_ok=True)
    out = cache_root / UPLINK_INSTALLER_NAME

    if installer_matches(out):
        print(f"Using cached verified Uplink installer: {out}")
        print(f"Verified MD5: {UPLINK_INSTALLER_MD5}")
        return out

    if out.exists():
        print(f"Discarding invalid cached installer: {out}", file=sys.stderr)
        out.unlink()

    part = out.with_suffix(out.suffix + ".part")
    part.unlink(missing_ok=True)
    opener = build_opener()
    try:
        with opener.open(MODDB_START_URL, timeout=30) as response:
            page = response.read().decode("utf-8", errors="replace")
            page_url = response.geturl()
        mirror_url = parse_moddb_mirror_link(page, page_url)

        digest = hashlib.md5(usedforsecurity=False)
        total = 0
        print("Downloading original Half-Life: Uplink demo installer...")
        with opener.open(mirror_url, timeout=60) as response, part.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                total += len(chunk)
                print(f"  {total / (1024 * 1024):6.1f} MiB", end="\r", flush=True)
        print(" " * 32, end="\r")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        part.unlink(missing_ok=True)
        raise PrepError(f"could not download Uplink from ModDB: {exc}") from exc

    actual_md5 = digest.hexdigest()
    if total != UPLINK_INSTALLER_SIZE:
        part.unlink(missing_ok=True)
        raise PrepError(f"download size mismatch: expected {UPLINK_INSTALLER_SIZE} bytes, got {total}")
    if actual_md5.lower() != UPLINK_INSTALLER_MD5:
        part.unlink(missing_ok=True)
        raise PrepError(f"download MD5 mismatch: expected {UPLINK_INSTALLER_MD5}, got {actual_md5}")

    part.replace(out)
    print(f"Downloaded + cached: {out} ({total} bytes)")
    print(f"Verified MD5: {actual_md5}")
    return out


def is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return bool(os.environ.get("TERMUX_VERSION")) or "com.termux" in prefix


def _print_subprocess_tail(label: str, proc: subprocess.CompletedProcess[str]) -> None:
    print(f"{label} failed (exit {proc.returncode}):", file=sys.stderr)
    output = proc.stdout or ""
    tail = "\n".join(output.splitlines()[-12:])
    if tail:
        print(tail, file=sys.stderr)


def rewise_log_path(cache_root: Path) -> Path:
    return cache_root / "rewise-bootstrap.log"


def _append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if text and not text.endswith("\n"):
            handle.write("\n")


def ensure_rewise_build_tools(cache_root: Path) -> None:
    """Ensure the tools needed to clone and build REWise are present."""
    log = rewise_log_path(cache_root)
    if is_termux():
        pkg = shutil.which("pkg")
        if not pkg:
            raise PrepError("Termux was detected but the pkg command was not found")
        print("REWise is required; ensuring Termux build dependencies...")
        proc = subprocess.run(
            [pkg, "install", "-y", "git", "clang", "cmake", "make", "zlib"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        _append_log(log, "===== TERMUX DEPENDENCIES =====\n" + (proc.stdout or ""))
        if proc.returncode != 0:
            _print_subprocess_tail("Termux dependency install", proc)
            raise PrepError(f"could not install REWise build dependencies; full log: {log}")

    missing = [name for name in ("git", "cmake", "make") if not shutil.which(name)]
    if not (shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")):
        missing.append("C compiler")
    if missing:
        raise PrepError(
            "REWise build prerequisites are missing: " + ", ".join(missing) + f"; full log: {log}"
        )


def _run_logged(
    command: list[str],
    *,
    cwd: Path | None,
    log: Path,
    label: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    rendered = " ".join(command)
    _append_log(log, f"\n===== {label} =====\n$ {rendered}")
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError as exc:
        _append_log(log, f"EXEC ERROR: {exc}")
        raise PrepError(f"{label} could not run: {exc}; full log: {log}") from exc
    _append_log(log, proc.stdout or "")
    if proc.returncode != 0:
        _print_subprocess_tail(label, proc)
        raise PrepError(f"{label} failed with exit {proc.returncode}; full log: {log}")
    return proc


def _prepare_rewise_source(cache_root: Path) -> tuple[Path, str]:
    """Clone the pinned REWise release and return (source_root, commit_sha)."""
    source_parent = cache_root / "tools" / "src"
    source_parent.mkdir(parents=True, exist_ok=True)
    source_root = source_parent / f"rewise-{REWISE_VERSION}"
    log = rewise_log_path(cache_root)

    if source_root.exists() and not (source_root / ".git").is_dir():
        shutil.rmtree(source_root)

    if not source_root.exists():
        _run_logged(
            [
                "git", "clone", "--depth", "1", "--branch", REWISE_GIT_TAG,
                "--single-branch", REWISE_GIT_URL, str(source_root),
            ],
            cwd=None,
            log=log,
            label=f"REWise {REWISE_VERSION} clone",
        )

    tag_proc = _run_logged(
        ["git", "rev-parse", "HEAD"],
        cwd=source_root,
        log=log,
        label="REWise commit identification",
    )
    commit = (tag_proc.stdout or "").strip().splitlines()[-1]
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise PrepError(f"REWise checkout returned an invalid commit id {commit!r}; full log: {log}")

    # Verify that the checkout still resolves to the requested release tag.
    _run_logged(
        ["git", "rev-parse", "--verify", f"refs/tags/{REWISE_GIT_TAG}^{{commit}}"],
        cwd=source_root,
        log=log,
        label="REWise tag verification",
    )
    print(f"REWise source: {REWISE_GIT_TAG} @ {commit}")
    return source_root, commit


def bootstrap_rewise(cache_root: Path) -> Path:
    """Return a usable REWise binary, building the pinned release when needed."""
    system = shutil.which("rewise")
    if system:
        return Path(system)

    cached = cache_root / "tools" / "bin" / "rewise"
    if cached.is_file() and os.access(cached, os.X_OK):
        return cached

    log = rewise_log_path(cache_root)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        f"Xash64 r10 REWise bootstrap\nrelease={REWISE_GIT_TAG}\nsource={REWISE_GIT_URL}\n",
        encoding="utf-8",
    )
    ensure_rewise_build_tools(cache_root)
    source_root, commit = _prepare_rewise_source(cache_root)

    build_root = cache_root / "tools" / "build" / f"rewise-{REWISE_VERSION}"
    if build_root.exists():
        shutil.rmtree(build_root)
    build_root.mkdir(parents=True, exist_ok=True)

    compiler = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
    assert compiler is not None
    env = os.environ.copy()
    env["CC"] = compiler

    # REWise 0.3.1 added upstream CMake support. Build only the project; do not
    # invoke an install target that could try to write into the Termux prefix.
    _run_logged(
        [
            "cmake", "-S", str(source_root), "-B", str(build_root),
            "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_C_COMPILER={compiler}",
        ],
        cwd=None,
        log=log,
        label="REWise CMake configure",
        env=env,
    )
    _run_logged(
        ["cmake", "--build", str(build_root), "--parallel", "2"],
        cwd=None,
        log=log,
        label="REWise CMake build",
        env=env,
    )

    candidates = sorted(
        (p for p in build_root.rglob("rewise") if p.is_file() and os.access(p, os.X_OK)),
        key=lambda p: (len(p.parts), str(p)),
    )
    if not candidates:
        raise PrepError(f"REWise build finished but no executable was found; full log: {log}")

    cached.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidates[0], cached)
    cached.chmod(0o755)
    version = _run_logged(
        [str(cached), "-v"],
        cwd=None,
        log=log,
        label="REWise version check",
    )
    version_text = (version.stdout or "").strip().replace("\n", " ")
    print(f"Cached REWise helper: {cached}")
    print(f"REWise build commit: {commit}")
    if version_text:
        print(f"REWise reports: {version_text}")
    return cached


def file_contains_any(path: Path, markers: tuple[bytes, ...]) -> bool:
    """Search a file in chunks without loading a 50 MiB installer into RAM."""
    max_marker = max(len(marker) for marker in markers)
    overlap = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return False
            data = overlap + chunk
            if any(marker in data for marker in markers):
                return True
            overlap = data[-(max_marker - 1):] if max_marker > 1 else b""


def looks_like_wise_installer(path: Path) -> bool:
    if path.suffix.lower() != ".exe":
        return False
    try:
        return file_contains_any(
            path,
            (b"WiseMain", b"Wise Installation Wizard", b"Wise Installation System"),
        )
    except OSError:
        return False


def try_rewise(source: Path, extract_dir: Path, cache_root: Path) -> bool:
    rewise = bootstrap_rewise(cache_root)
    out = extract_dir / "rewise"
    out.mkdir(parents=True, exist_ok=True)
    log = rewise_log_path(cache_root)

    # REWise defaults its temporary WiseScript.bin to /tmp. That works on a
    # conventional FHS Linux host, but unprivileged Android/Termux apps cannot
    # write to Android's root filesystem /tmp. REWise documents -t/--tmp-path
    # specifically to override this location, so always provide a known-writable
    # cache directory rather than relying on a host-specific default.
    rewise_tmp = cache_root / "tmp" / "rewise"
    rewise_tmp.mkdir(parents=True, exist_ok=True)
    if not os.access(rewise_tmp, os.W_OK):
        raise PrepError(f"REWise temporary directory is not writable: {rewise_tmp}")
    print(f"REWise temp path: {rewise_tmp}")

    # First ask REWise to parse/list the installer. This gives a precise failure
    # before extraction and is retained in the persistent bootstrap log.
    _run_logged(
        [str(rewise), "-l", "-t", str(rewise_tmp), str(source)],
        cwd=None,
        log=log,
        label="REWise installer list",
    )

    before = _count_files(out)
    _run_logged(
        [str(rewise), "-x", str(out), "-t", str(rewise_tmp), str(source)],
        cwd=None,
        log=log,
        label="REWise Uplink extraction",
    )
    if _count_files(out) <= before:
        raise PrepError(f"REWise exited successfully but produced no files; full log: {log}")
    print("Extraction method succeeded: REWise/Wise Installation System")
    return True


def valid_pe_offsets(path: Path, max_hits: int = 8) -> list[int]:
    """Return MZ offsets that actually resolve to an in-bounds PE signature."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    hits: list[int] = []
    start = 0
    while len(hits) < max_hits:
        pos = data.find(b"MZ", start)
        if pos < 0:
            break
        start = pos + 2
        if pos + 0x40 > len(data):
            continue
        e_lfanew = int.from_bytes(data[pos + 0x3C:pos + 0x40], "little")
        # Real DOS stubs point reasonably close to their PE header. Reject the
        # huge random e_lfanew values produced by compressed payload data.
        if e_lfanew < 0x40 or e_lfanew > 0x100000:
            continue
        pe = pos + e_lfanew
        if pe + 4 <= len(data) and data[pe:pe + 4] == b"PE\0\0":
            hits.append(pos)
    return hits


def _count_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def run_extract(command: list[str], label: str, output_dir: Path | None = None) -> bool:
    before = _count_files(output_dir) if output_dir is not None else 0
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"{label} could not run: {exc}", file=sys.stderr)
        return False

    after = _count_files(output_dir) if output_dir is not None else before + 1
    if proc.returncode == 0 and (output_dir is None or after > before):
        print(f"Extraction method succeeded: {label}")
        return True

    print(f"{label} could not extract this layer (continuing):", file=sys.stderr)
    tail = "\n".join(proc.stdout.splitlines()[-8:])
    if tail:
        print(tail, file=sys.stderr)
    return False


def signature_offsets(path: Path, max_hits: int = 4) -> dict[str, list[int]]:
    markers = {name: marker for name, marker in SIGNATURES}
    hits: dict[str, list[int]] = {name: [] for name in markers}
    max_marker = max(len(marker) for marker in markers.values())
    overlap = b""
    absolute = 0

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            data = overlap + chunk
            base = absolute - len(overlap)
            for name, marker in markers.items():
                start = 0
                while len(hits[name]) < max_hits:
                    pos = data.find(marker, start)
                    if pos < 0:
                        break
                    abs_pos = base + pos
                    if abs_pos >= 0 and (not hits[name] or hits[name][-1] != abs_pos):
                        hits[name].append(abs_pos)
                    start = pos + 1
            absolute += len(chunk)
            overlap = data[-(max_marker - 1):] if max_marker > 1 else b""

    return {name: positions for name, positions in hits.items() if positions}


def print_signature_report(path: Path) -> None:
    try:
        hits = signature_offsets(path)
    except OSError as exc:
        print(f"Signature scan failed: {exc}", file=sys.stderr)
        return
    print(f"Binary signature scan for {path.name}:", file=sys.stderr)
    pe_hits = valid_pe_offsets(path)
    if pe_hits:
        print("  valid PE executable(s): " + ", ".join(f"0x{x:X}" for x in pe_hits), file=sys.stderr)
    if not hits and not pe_hits:
        print("  no known archive/setup markers found", file=sys.stderr)
        return
    for name, positions in hits.items():
        rendered = ", ".join(f"0x{offset:X}" for offset in positions)
        print(f"  {name}: {rendered}", file=sys.stderr)


def try_cabextract(source: Path, extract_dir: Path) -> bool:
    cabextract = shutil.which("cabextract")
    if not cabextract:
        return False
    out = extract_dir / "cabextract"
    out.mkdir(parents=True, exist_ok=True)
    return run_extract(
        [cabextract, "-q", "-d", str(out), str(source)],
        "cabextract",
        out,
    )


def try_seven_zip(source: Path, extract_dir: Path) -> bool:
    seven_zip = shutil.which("7z") or shutil.which("7zz")
    if not seven_zip:
        return False
    out = extract_dir / "7z"
    out.mkdir(parents=True, exist_ok=True)
    return run_extract(
        [seven_zip, "x", "-y", f"-o{out}", str(source)],
        "7z",
        out,
    )


def try_unshield(source: Path, extract_dir: Path, label_suffix: str = "") -> bool:
    unshield = shutil.which("unshield")
    if not unshield:
        return False

    # Current unshield syntax is: unshield [options] x CABFILE.
    # Start with autodetection, then old-compression and forced old versions.
    variants: list[tuple[str, list[str]]] = [
        ("auto", []),
        ("old-compression", ["-O"]),
        ("v5", ["-i", "5"]),
        ("v4", ["-i", "4"]),
        ("v3", ["-i", "3"]),
    ]
    for variant, extra in variants:
        out = extract_dir / f"unshield-{label_suffix}{variant}"
        out.mkdir(parents=True, exist_ok=True)
        command = [unshield, *extra, "-d", str(out), "x", str(source)]
        if run_extract(command, f"unshield/{variant}", out):
            return True
    return False


def carve_installshield_cabs(source: Path, extract_dir: Path) -> bool:
    """Try InstallShield CAB streams embedded inside a larger self-extractor.

    unshield wants a CABFILE whose first bytes are the InstallShield CAB header.
    Old self-extracting installers sometimes prepend a launcher to that stream.
    We therefore locate ISc( markers, copy each marker-to-EOF candidate, and let
    unshield validate/reject the result. False positives are harmless.
    """
    unshield = shutil.which("unshield")
    if not unshield:
        return False

    offsets = signature_offsets(source).get("InstallShield CAB", [])
    if not offsets:
        return False

    succeeded = False
    with source.open("rb") as handle:
        for index, offset in enumerate(offsets):
            carved_dir = extract_dir / "carved"
            carved_dir.mkdir(parents=True, exist_ok=True)
            carved = carved_dir / f"installshield-{index:02d}-0x{offset:X}.cab"
            handle.seek(offset)
            with carved.open("wb") as out:
                shutil.copyfileobj(handle, out, length=1024 * 1024)
            print(f"Found embedded InstallShield CAB marker at 0x{offset:X}; testing carved stream...")
            if try_unshield(carved, extract_dir, f"carved{index}-"):
                succeeded = True
                break
    return succeeded


def try_extractcode(source: Path, extract_dir: Path) -> bool:
    """Optional last-resort path when the ExtractCode CLI is already installed."""
    extractcode = shutil.which("extractcode")
    if not extractcode:
        return False
    work = extract_dir / "extractcode"
    work.mkdir(parents=True, exist_ok=True)
    local = work / source.name
    shutil.copy2(source, local)
    # --all-formats is required because InstallShield is a special-package type.
    if not run_extract([extractcode, "--all-formats", "--quiet", str(local)], "extractcode"):
        return False
    return _count_files(work) > 1


def extract_one(source: Path, extract_dir: Path, cache_root: Path) -> bool:
    extract_dir.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(source):
        out = extract_dir / "zip"
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(out)
        print("Extraction method succeeded: Python zipfile")
        return True

    try:
        is_tar = tarfile.is_tarfile(source)
    except OSError:
        is_tar = False
    if is_tar:
        out = extract_dir / "tar"
        out.mkdir(parents=True, exist_ok=True)
        with tarfile.open(source) as archive:
            archive.extractall(out, filter="data")
        print("Extraction method succeeded: Python tarfile")
        return True

    suffix = source.suffix.lower()
    succeeded = False

    # The user's real hluplink.exe diagnostic contains WiseMain / Wise wizard
    # strings. For a positively identified Wise wrapper, REWise is the correct
    # parser: a bootstrap/parse failure must be surfaced, not hidden behind a
    # cascade of unrelated generic extractors.
    if suffix == ".exe" and looks_like_wise_installer(source):
        return try_rewise(source, extract_dir, cache_root)

    # cabextract explicitly supports searching Windows EXEs for embedded
    # Microsoft cabinet streams, so try it before asking 7-Zip to identify the wrapper.
    if suffix in {".exe", ".cab"}:
        succeeded = try_cabextract(source, extract_dir) or succeeded

    succeeded = try_seven_zip(source, extract_dir) or succeeded

    # Direct InstallShield CABs and carved ISc( streams go through unshield.
    try:
        with source.open("rb") as handle:
            header = handle.read(4)
    except OSError:
        header = b""
    if suffix == ".cab" or header == b"ISc(":
        succeeded = try_unshield(source, extract_dir) or succeeded

    if suffix == ".exe":
        succeeded = carve_installshield_cabs(source, extract_dir) or succeeded
        succeeded = try_extractcode(source, extract_dir) or succeeded

    return succeeded


def nested_archive_candidates(root: Path) -> list[Path]:
    extensions = {".cab", ".exe", ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"}
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in extensions]
    # Prefer CABs and smaller setup layers before recursively attacking giant executables.
    return sorted(
        files,
        key=lambda p: (0 if p.suffix.lower() == ".cab" else 1, p.stat().st_size, str(p).lower()),
    )


def extract_source(source: Path, temp_root: Path, cache_root: Path) -> Path:
    if source.is_dir():
        return source
    if not source.is_file():
        raise PrepError(f"Source does not exist: {source}")

    extract_root = temp_root / "extracted"
    first = extract_root / "layer0"
    if not extract_one(source, first, cache_root):
        print_signature_report(source)
        raise PrepError(
            f"Could not extract {source.name} with the applicable extractor(s). "
            f"The verified installer was kept at {source}."
        )

    if find_data_roots(first):
        return first

    visited: set[tuple[int, str]] = set()
    current_roots = [first]
    for depth in range(1, 5):
        next_roots: list[Path] = []
        index = 0
        for root in current_roots:
            for candidate in nested_archive_candidates(root):
                try:
                    st = candidate.stat()
                except OSError:
                    continue
                signature = (st.st_size, sha256_file(candidate))
                if signature in visited:
                    continue
                visited.add(signature)
                out = extract_root / f"layer{depth}-{index}"
                index += 1
                if extract_one(candidate, out, cache_root):
                    next_roots.append(out)
                    if find_data_roots(out):
                        return extract_root
        if not next_roots:
            break
        current_roots = next_roots

    return extract_root


def _read_pak_entry_prefix(pak: Path, entry: tuple[int, int], count: int) -> bytes:
    offset, length = entry
    if length < count:
        return b""
    with pak.open("rb") as handle:
        handle.seek(offset)
        return handle.read(count)


def _sha256_pak_entry(pak: Path, entry: tuple[int, int]) -> str:
    offset, length = entry
    digest = hashlib.sha256()
    with pak.open("rb") as handle:
        handle.seek(offset)
        remaining = length
        while remaining:
            chunk = handle.read(min(1024 * 1024, remaining))
            if not chunk:
                raise PrepError(f"short read while hashing PAK entry in {pak}")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def verify_uplink_root(game_root: Path) -> tuple[str, Path | None]:
    loose = all((game_root / "maps" / name).is_file() for name in MAPS)
    if loose:
        failures: list[str] = []
        for name in MAPS:
            path = game_root / "maps" / name
            version = bsp_version(path)
            if version != BSP_VERSION:
                failures.append(f"maps/{name}: expected BSP v{BSP_VERSION}, got v{version}")
        if failures:
            raise PrepError("Uplink verification failed:\n  " + "\n  ".join(failures))
        return "loose", None

    pak = find_uplink_pak(game_root)
    if pak is None:
        raise PrepError("Uplink verification failed: no loose Uplink maps and no PAK containing all three maps")

    entries = _pak_uplink_maps(pak)
    failures = []
    for name in MAPS:
        raw = _read_pak_entry_prefix(pak, entries[name], 4)
        if len(raw) != 4:
            failures.append(f"{pak.name}: maps/{name}: BSP header unreadable")
            continue
        version = struct.unpack("<i", raw)[0]
        if version != BSP_VERSION:
            failures.append(f"{pak.name}: maps/{name}: expected BSP v{BSP_VERSION}, got v{version}")
    if failures:
        raise PrepError("Uplink verification failed:\n  " + "\n  ".join(failures))
    return "pak", pak


def write_manifest(game_root: Path, manifest: Path) -> None:
    rows = ["# Xash64 Uplink local asset manifest", "# SHA256  SIZE  RELATIVE_PATH"]
    mode, pak = verify_uplink_root(game_root)

    if mode == "loose":
        selected: list[Path] = [game_root / "maps" / name for name in MAPS]
        for path in selected:
            rel = path.relative_to(game_root).as_posix()
            rows.append(f"{sha256_file(path)}  {path.stat().st_size}  {rel}")
    else:
        assert pak is not None
        rel = pak.relative_to(game_root).as_posix()
        rows.append(f"{sha256_file(pak)}  {pak.stat().st_size}  {rel}")
        entries = _pak_uplink_maps(pak)
        for name in MAPS:
            offset, length = entries[name]
            rows.append(
                f"{_sha256_pak_entry(pak, (offset, length))}  {length}  {rel}::maps/{name}"
            )

    for metadata in ("liblist.gam", "gameinfo.txt"):
        path = game_root / metadata
        if path.is_file():
            rel = path.relative_to(game_root).as_posix()
            rows.append(f"{sha256_file(path)}  {path.stat().st_size}  {rel}")

    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_extraction_inventory(root: Path, cache_root: Path) -> Path:
    inventory = cache_root / "uplink-extracted-inventory.txt"
    rows = ["# Xash64 r10 extracted Uplink inventory"]
    files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    for path in files[:2000]:
        try:
            rel = path.relative_to(root).as_posix()
            rows.append(f"{path.stat().st_size:10d}  {rel}")
        except OSError:
            continue
    if len(files) > 2000:
        rows.append(f"# truncated: {len(files) - 2000} additional files")
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return inventory


def copy_game_root(game_root: Path, destination: Path, force: bool) -> Path:
    out = destination / "xash" / "valve"
    if out.exists():
        if not force:
            raise PrepError(f"Destination already exists: {out} (use --force to replace it)")
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(game_root, out)
    return out


def parse_args(argv: list[str] | None = None) -> tuple[Path | None, Path, bool, bool, Path]:
    parser = argparse.ArgumentParser(
        description="Prepare Half-Life: Uplink data for the Xash64/N64 SummerCart layout."
    )
    parser.add_argument("paths", nargs="+", metavar="PATH")
    parser.add_argument(
        "--download",
        action="store_true",
        help="download/cache/verify the original Uplink demo installer, then extract it",
    )
    parser.add_argument("--force", action="store_true", help="replace destination/xash/valve if it exists")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=default_cache_dir(),
        help="installer cache directory (default: ~/.cache/xash64-n64)",
    )
    args = parser.parse_args(argv)

    cache_dir = args.cache_dir.expanduser().resolve()
    if args.download:
        if len(args.paths) != 1:
            parser.error("--download takes exactly one path: DEST")
        return None, Path(args.paths[0]), True, args.force, cache_dir
    if len(args.paths) != 2:
        parser.error("without --download, provide SOURCE DEST")
    return Path(args.paths[0]), Path(args.paths[1]), False, args.force, cache_dir


def main(argv: list[str] | None = None) -> int:
    source_arg, destination_arg, do_download, force, cache_dir = parse_args(argv)
    destination = destination_arg.expanduser().resolve()

    try:
        with tempfile.TemporaryDirectory(prefix="xash64-uplink-") as temp_name:
            temp_root = Path(temp_name)
            if do_download:
                source = download_uplink_installer(cache_dir)
            else:
                assert source_arg is not None
                source = source_arg.expanduser().resolve()

            extracted = extract_source(source, temp_root, cache_dir)
            roots = find_data_roots(extracted)
            if not roots:
                inventory = write_extraction_inventory(extracted, cache_dir)
                if source.is_file():
                    print_signature_report(source)
                raise PrepError(
                    "Could not find Uplink data as loose maps or inside a Half-Life PAK after extraction. "
                    f"Extracted file inventory kept at {inventory}. The source was not deleted."
                )
            if len(roots) > 1:
                print("Multiple Uplink data roots found; using the shallowest:", file=sys.stderr)
                for root in roots:
                    print(f"  {root}", file=sys.stderr)

            game_root = roots[0]
            storage_mode, storage_pak = verify_uplink_root(game_root)
            if storage_mode == "pak":
                assert storage_pak is not None
                print(f"Uplink maps verified inside {storage_pak.name} (PAK, BSP v{BSP_VERSION})")
            else:
                print(f"Uplink maps verified as loose BSP files (BSP v{BSP_VERSION})")
            out = copy_game_root(game_root, destination, force)
            manifest = destination / "xash" / "uplink-manifest.txt"
            write_manifest(out, manifest)

            print(f"Uplink source root: {game_root}")
            print(f"Prepared data:      {out}")
            if storage_mode == "loose":
                for name in MAPS:
                    path = out / "maps" / name
                    print(f"  {name}: {path.stat().st_size} bytes, BSP v{bsp_version(path)}")
            else:
                copied_pak = find_uplink_pak(out)
                assert copied_pak is not None
                entries = _pak_uplink_maps(copied_pak)
                print(f"  {copied_pak.name}: {copied_pak.stat().st_size} bytes")
                for name in MAPS:
                    _offset, length = entries[name]
                    print(f"  {name}: {length} bytes inside {copied_pak.name}, BSP v{BSP_VERSION}")
            print(f"Manifest:           {manifest}")
            if do_download:
                print(f"Cached installer:   {source}")
            print("READY: copy the xash directory to the root of the SummerCart SD card.")
            return 0
    except (OSError, PrepError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(f"prepare-uplink: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
