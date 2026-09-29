#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import urllib.parse


ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "pets.json"
CATALOG = ROOT / "catalog.json"
SIGNATURE = ROOT / "catalog.sig.json"
SIGNING_SCRIPT = ROOT / "scripts" / "catalog-signing.swift"
PREVIEW_SCRIPT = ROOT / "scripts" / "build-preview.swift"
PREVIEWS = ROOT / "previews"
REPOSITORY = "ibuhs/vehla-pets"
PUBLISHER_ID = "com.vehla.publisher"
PUBLISHER_NAME = "Vehla"
KEY_ID = "release-2026-07"
EXPECTED_WIDTH = 1536
EXPECTED_HEIGHT = 2288
MAXIMUM_ATLAS_SIZE = 20 * 1024 * 1024
MAXIMUM_PREVIEW_SIZE = 512 * 1024


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-root", required=True, type=pathlib.Path)
    parser.add_argument("--tag", required=True)
    return parser.parse_args()


def atlas_dimensions(path: pathlib.Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    width = re.search(r"pixelWidth:\s*(\d+)", result)
    height = re.search(r"pixelHeight:\s*(\d+)", result)
    if width is None or height is None:
        raise SystemExit(f"Could not inspect atlas dimensions: {path}")
    return int(width.group(1)), int(height.group(1))


def locate_atlas(root: pathlib.Path, filename: str) -> pathlib.Path:
    matches = [path for path in root.rglob(filename) if path.is_file()]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one {filename} under {root}; found {len(matches)}."
        )
    return matches[0]


def signing_output(command: str, *arguments: str) -> str:
    if not os.environ.get("VEHLA_PUBLISHER_PRIVATE_KEY"):
        raise SystemExit("VEHLA_PUBLISHER_PRIVATE_KEY is required.")
    return subprocess.run(
        ["swift", str(SIGNING_SCRIPT), command, *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    options = arguments()
    source = json.loads(SOURCE.read_text())
    if source.get("schemaVersion") != 1:
        raise SystemExit("Unsupported pets.json schema version.")

    pet_ids: set[str] = set()
    catalog_pets = []
    for pet in source.get("pets", []):
        pet_id = pet["id"]
        if pet_id in pet_ids:
            raise SystemExit(f"Duplicate Pet ID: {pet_id}")
        pet_ids.add(pet_id)

        filename = pet["filename"]
        atlas = locate_atlas(options.assets_root, filename)
        data = atlas.read_bytes()
        if len(data) > MAXIMUM_ATLAS_SIZE:
            raise SystemExit(f"{filename} exceeds the atlas size limit.")
        width, height = atlas_dimensions(atlas)
        if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
            raise SystemExit(
                f"{filename} is {width}×{height}; expected "
                f"{EXPECTED_WIDTH}×{EXPECTED_HEIGHT}."
            )

        preview_filename = f"{pet_id}-preview.png"
        preview = PREVIEWS / preview_filename
        subprocess.run(
            ["swift", str(PREVIEW_SCRIPT), str(atlas), str(preview)],
            check=True,
        )
        preview_data = preview.read_bytes()
        if len(preview_data) > MAXIMUM_PREVIEW_SIZE:
            raise SystemExit(f"{preview_filename} exceeds the preview size limit.")

        encoded_tag = urllib.parse.quote(options.tag, safe="")
        encoded_filename = urllib.parse.quote(filename, safe="")
        encoded_preview_filename = urllib.parse.quote(preview_filename, safe="")
        catalog_pets.append(
            {
                **pet,
                "atlasURL": (
                    f"https://github.com/{REPOSITORY}/releases/download/"
                    f"{encoded_tag}/{encoded_filename}"
                ),
                "previewURL": (
                    f"https://github.com/{REPOSITORY}/releases/download/"
                    f"{encoded_tag}/{encoded_preview_filename}"
                ),
                "previewSha256": hashlib.sha256(preview_data).hexdigest(),
                "previewByteSize": len(preview_data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "byteSize": len(data),
                "width": width,
                "height": height,
            }
        )

    public_key = signing_output("public-key")
    catalog = {
        "schemaVersion": 1,
        "publisher": {
            "id": PUBLISHER_ID,
            "name": PUBLISHER_NAME,
            "keyID": KEY_ID,
        },
        "pets": catalog_pets,
    }
    catalog_data = (json.dumps(catalog, indent=2, ensure_ascii=False) + "\n").encode()
    with tempfile.NamedTemporaryFile(
        dir=ROOT,
        prefix=".catalog-",
        delete=False,
    ) as temporary:
        temporary.write(catalog_data)
        temporary_path = pathlib.Path(temporary.name)
    try:
        signature = signing_output("sign", str(temporary_path))
        temporary_path.replace(CATALOG)
    finally:
        temporary_path.unlink(missing_ok=True)

    signature_document = {
        "algorithm": "ed25519",
        "publisherID": PUBLISHER_ID,
        "keyID": KEY_ID,
        "publicKey": public_key,
        "signature": signature,
    }
    SIGNATURE.write_text(
        json.dumps(signature_document, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"Built and signed {len(catalog_pets)} Pet catalog entries.")


if __name__ == "__main__":
    main()
