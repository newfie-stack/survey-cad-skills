"""Build the reviewed Crown Plan Agent skill into a portable ChatGPT plugin.

This builds files only. It does not install dependencies, contact a service,
publish a plugin, or determine whether source material may be disclosed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import struct
from urllib.parse import unquote
import zipfile
import zlib


SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PUBLIC_AUTHOR = "newfie-stack"
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_ICON_BYTES = 5 * 1024 * 1024
MAX_FILES = 4096
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".venv", ".git"}
RUNTIME_DIRS = {
    "engine": {".py", ".json", ".md"},
    "references": {".md"},
    "tests": {".py", ".json", ".md"},
    "agents": {".yaml", ".yml"},
}
DEVELOPMENT_TEST = "tests/test_chatgpt_packaging.py"
SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate plugin manifest key")
        value[key] = item
    return value


def _read_file(path: Path, root: Path, *, binary=False) -> bytes:
    if not path.is_relative_to(root):
        raise ValueError("Source path is not contained")
    for selected in (path, *path.parents):
        if selected.is_symlink():
            raise ValueError("Symlink source paths are not permitted")
        if selected == root:
            break
    if not path.is_file():
        raise ValueError("Missing required source file or icon asset")
    limit = MAX_ICON_BYTES if binary else MAX_TEXT_BYTES
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Source file exceeds the package size limit")
    if not binary:
        try:
            text = data.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Unexpected non-UTF-8 source artifact") from exc
        if "\x00" in text:
            raise ValueError("Unexpected binary source artifact")
    return data


def _frontmatter_value(data: bytes, field: str) -> str:
    text = data.decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("SKILL.md requires YAML frontmatter")
    header = text[4:].split("\n---\n", 1)[0]
    matches = re.findall(r"^" + re.escape(field) + r":[ \t]*(.+)$", header, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("Missing or duplicate skill " + field)
    value = matches[0].strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not value:
        raise ValueError("Missing skill " + field)
    return value


def _asset_path(value) -> str:
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise ValueError("Icon asset path must be contained and relative")
    selected = PurePosixPath(value)
    if selected.is_absolute() or ".." in selected.parts:
        raise ValueError("Icon asset path must be contained and relative")
    if len(selected.parts) != 2 or selected.parts[0] != "assets" or selected.suffix != ".png":
        raise ValueError("Icon asset must be a PNG directly inside assets")
    return str(selected)


def _validate_manifest(data: bytes) -> tuple[dict, set[str]]:
    def invalid_constant(_):
        raise ValueError("Nonfinite plugin manifest values are unsupported")
    try:
        manifest = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid plugin JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("$schema") != SCHEMA:
        raise ValueError("Plugin requires the Agent Plugins 1.0 schema")
    name = manifest.get("name")
    if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Invalid portable plugin name")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER.fullmatch(version) is None:
        raise ValueError("Plugin version must be semantic")
    prerelease = version.split("+", 1)[0].partition("-")[2]
    if any(part.isdigit() and len(part) > 1 and part.startswith("0")
           for part in prerelease.split(".")):
        raise ValueError("Plugin version has an invalid numeric prerelease")
    for key in ("description", "homepage", "repository", "license"):
        if key in manifest and (not isinstance(manifest[key], str) or not manifest[key].strip()):
            raise ValueError("Invalid plugin metadata: " + key)
    if "keywords" in manifest and (not isinstance(manifest["keywords"], list)
                                   or any(not isinstance(item, str) or not item.strip()
                                          for item in manifest["keywords"])):
        raise ValueError("Invalid plugin keywords metadata")
    if manifest.get("author") != {"name": PUBLIC_AUTHOR}:
        raise ValueError("Public template author must use the reviewed public handle, not account metadata")
    if any(key in manifest for key in ("skills", "mcpServers", "apps", "interface")):
        raise ValueError("Unexpected nonportable plugin declaration")
    extensions = manifest.get("extensions", {})
    if not isinstance(extensions, dict) or set(extensions) != {"com.openai"}:
        raise ValueError("Invalid OpenAI plugin extensions")
    settings = extensions["com.openai"]
    if not isinstance(settings, dict) or set(settings) != {"interface"}:
        raise ValueError("Unexpected app or server declaration in skills-only plugin")
    interface = settings["interface"]
    if not isinstance(interface, dict):
        raise ValueError("Plugin interface must be an object")
    for key in ("displayName", "shortDescription", "developerName", "category"):
        if not isinstance(interface.get(key), str) or not interface[key].strip():
            raise ValueError("Invalid plugin interface " + key)
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Plugin subtitle exceeds 30 characters")
    if interface["developerName"] != PUBLIC_AUTHOR:
        raise ValueError("Public developer attribution must not use normalized account metadata")
    if interface["category"] != "Productivity" or interface.get("capabilities") != []:
        raise ValueError("Unexpected skills-only plugin category or capabilities")
    prompts = interface.get("defaultPrompt")
    if isinstance(prompts, str):
        prompts = [prompts]
    if (not isinstance(prompts, list) or not 1 <= len(prompts) <= 3
            or any(not isinstance(prompt, str) or not prompt.strip() for prompt in prompts)):
        raise ValueError("Invalid plugin default prompts")
    for key in ("brandColor", "brandColorDark"):
        if key in interface and (not isinstance(interface[key], str)
                                 or not re.fullmatch(r"#[0-9a-fA-F]{6}", interface[key])):
            raise ValueError("Invalid plugin brand colour")
    assets = {_asset_path(interface.get(key)) for key in
              ("logo", "composerIcon", "logoDark", "composerIconDark")}
    if len(assets) != 2:
        raise ValueError("Expected the reviewed light and dark icon assets")
    return manifest, assets


def _validate_png(data: bytes) -> None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Icon asset is not PNG")
    offset, kinds, header, image_data = 8, [], None, []
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("Truncated PNG icon asset")
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError("Truncated PNG icon asset")
        payload = data[offset + 8:offset + 8 + size]
        checksum = struct.unpack(">I", data[offset + 8 + size:end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != checksum:
            raise ValueError("Invalid PNG icon asset checksum")
        if not kinds:
            if kind != b"IHDR" or size != 13:
                raise ValueError("PNG icon asset requires IHDR")
            header = struct.unpack(">IIBBBBB", payload)
        if kind == b"IDAT":
            image_data.append(payload)
        kinds.append(kind)
        offset = end
        if kind == b"IEND":
            if size or offset != len(data):
                raise ValueError("Unexpected trailing PNG icon data")
            break
    if b"IDAT" not in kinds or kinds[-1:] != [b"IEND"]:
        raise ValueError("Incomplete PNG icon asset")
    width, height, depth, colour, compression, filtering, interlace = header
    if width != height or not 256 <= width <= 4096:
        raise ValueError("Icon dimensions must be square, between 256 and 4096 pixels")
    if depth != 8 or colour not in {2, 6} or (compression, filtering, interlace) != (0, 0, 0):
        raise ValueError("Reviewed PNG icons must be non-interlaced 8-bit RGB or RGBA")
    stride = width * (3 if colour == 2 else 4) + 1
    expected = stride * height
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(b"".join(image_data), expected + 1)
    except zlib.error as exc:
        raise ValueError("Invalid PNG pixel stream") from exc
    if (len(pixels) != expected or not decoder.eof or decoder.unconsumed_tail
            or decoder.unused_data or any(pixels[offset] > 4 for offset in range(0, expected, stride))):
        raise ValueError("Invalid PNG pixel rows")


def _collect_runtime(skill_root: Path) -> dict[str, bytes]:
    files = {}
    for directory, names, filenames in os.walk(skill_root, followlinks=False):
        folder = Path(directory)
        relative_folder = folder.relative_to(skill_root)
        for name in list(names):
            selected = folder / name
            if selected.is_symlink():
                raise ValueError("Symlink source directories are not permitted")
            if name in CACHE_DIRS or (folder == skill_root and name in {"packaging", "tools"}):
                names.remove(name)
            elif folder == skill_root and name not in RUNTIME_DIRS:
                raise ValueError("Unexpected skill source directory")
        for name in filenames:
            selected = folder / name
            relative = selected.relative_to(skill_root).as_posix()
            if selected.is_symlink():
                raise ValueError("Symlink source files are not permitted")
            if relative == DEVELOPMENT_TEST:
                continue
            if folder == skill_root:
                allowed = (selected.suffix == ".md" and not name.startswith(".")) or name == "requirements.txt"
            else:
                owner = relative_folder.parts[0]
                allowed = selected.suffix in RUNTIME_DIRS[owner] and not name.startswith(".")
            if not allowed:
                raise ValueError("Unexpected or forbidden runtime source artifact")
            files["skills/crown-plan-agent/" + relative] = _read_file(selected, skill_root)
            if len(files) > MAX_FILES:
                raise ValueError("Too many runtime source files")
    return files


def _validate_markdown(files: dict[str, bytes]) -> None:
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        text = data.decode("utf-8")
        targets = re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text)
        targets += [angle or bare for angle, bare in re.findall(
            r"^ {0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|(\S+))", text, re.MULTILINE)]
        for value in targets:
            value = value.strip("<>")
            if value.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
                continue
            target = unquote(value.split("#", 1)[0])
            contained = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
            if target.startswith("/") or contained.startswith("../") or contained not in files:
                raise ValueError("Missing or uncontained Markdown reference target: " + name)


def build_plugin_archive(skill_root: Path, output: Path) -> dict:
    """Write one deterministic fresh archive from reviewed skill source."""
    skill_root, output = Path(skill_root), Path(output)
    if skill_root.is_symlink():
        raise ValueError("Symlink skill roots are not permitted")
    skill_root = skill_root.resolve(strict=True)
    if output.resolve().is_relative_to(skill_root):
        raise ValueError("Output archive must be outside the skill source folder")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output archive already exists")
    if output.suffix.lower() != ".zip":
        raise ValueError("Output archive must have a .zip suffix")
    if not output.parent.is_dir():
        raise ValueError("Output directory does not exist")
    template = skill_root / "packaging" / "chatgpt"
    manifest_bytes = _read_file(template / "plugin.json", skill_root)
    manifest, assets = _validate_manifest(manifest_bytes)
    files = _collect_runtime(skill_root)
    skill_data = files.get("skills/crown-plan-agent/SKILL.md")
    if skill_data is None or _frontmatter_value(skill_data, "name") != "crown-plan-agent":
        raise ValueError("Missing canonical Crown Plan Agent skill")
    _frontmatter_value(skill_data, "description")
    if _frontmatter_value(skill_data, "version") != manifest["version"]:
        raise ValueError("Skill and plugin version must match")
    files["plugin.json"] = manifest_bytes
    files["README.md"] = _read_file(template / "README.md", skill_root)
    license_path = skill_root.parents[1] / "LICENSE"
    files["LICENSE"] = _read_file(license_path, skill_root.parents[1])
    for relative in sorted(assets):
        data = _read_file(template / relative, skill_root, binary=True)
        _validate_png(data)
        files[relative] = data
    asset_root = template / "assets"
    if any(path.is_symlink() for path in asset_root.rglob("*")):
        raise ValueError("Symlink icon assets are not permitted")
    if {p.relative_to(template).as_posix() for p in asset_root.rglob("*") if p.is_file()} != assets:
        raise ValueError("Unexpected or missing icon asset")
    _validate_markdown(files)
    content = [{"path": name, "sha256": hashlib.sha256(data).hexdigest()}
               for name, data in sorted(files.items())]
    build_manifest = {
        "version": manifest["version"], "files": content,
        "development_only_excluded": ["packaging/", "tools/", DEVELOPMENT_TEST, "known caches"],
        "source_policy": "Reviewed source only; no project inputs or external provider implementation",
    }
    files["BUILD_MANIFEST.json"] = (json.dumps(build_manifest, indent=2, sort_keys=True) + "\n").encode()
    created = False
    try:
        with output.open("xb") as destination:
            created = True
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name, data in sorted(files.items()):
                    entry = zipfile.ZipInfo(manifest["name"] + "/" + name, date_time=(1980, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"archive": str(output), "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "version": manifest["version"], "files": len(files)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed Crown Plan Agent ChatGPT plugin; no upload")
    parser.add_argument("--output", required=True, type=Path, help="Fresh ZIP outside the skill source folder")
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Complete reviewed skill folder (default: this checkout)")
    args = parser.parse_args(argv)
    try:
        result = build_plugin_archive(args.skill_root, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
