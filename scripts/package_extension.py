#!/usr/bin/env python3
"""
TrueStars VN — Extension Packaging & Validation Script.
Validates Manifest V3 compliance, icons, and packages a clean ZIP archive.
"""

import os
import sys
import json
import zipfile
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXT_DIR = os.path.join(PROJECT_ROOT, "extension")
MANIFEST_PATH = os.path.join(EXT_DIR, "manifest.json")
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

def validate_manifest():
    print("[1/3] Validating manifest.json...")
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Missing {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if manifest.get("manifest_version") != 3:
        raise ValueError("manifest_version must be 3")

    # Check icons
    icons = manifest.get("icons", {})
    for size_str, rel_path in icons.items():
        size = int(size_str)
        abs_path = os.path.join(EXT_DIR, rel_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Referenced icon {abs_path} does not exist!")
        with Image.open(abs_path) as img:
            if img.size != (size, size):
                raise ValueError(f"Icon {rel_path} size {img.size} does not match required {size}x{size}!")
    print("  ✓ Icons valid and exact dimensions confirmed.")

    # Check content scripts
    for cs in manifest.get("content_scripts", []):
        for js in cs.get("js", []):
            p = os.path.join(EXT_DIR, js)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Content script {p} does not exist!")
        for css in cs.get("css", []):
            p = os.path.join(EXT_DIR, css)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Content CSS {p} does not exist!")
    print("  ✓ Content scripts and stylesheets verified.")

    # Check web accessible resources
    for war in manifest.get("web_accessible_resources", []):
        for res in war.get("resources", []):
            if "*" in res:
                continue
            p = os.path.join(EXT_DIR, res)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Web accessible resource {p} does not exist!")
    print("  ✓ Web accessible resources verified.")
    return manifest

def build_zip():
    print("[2/3] Packaging clean ZIP archives...")
    out_dist = os.path.join(DIST_DIR, "truestars_extension.zip")
    out_pub = os.path.join(PUBLIC_DIR, "truestars_extension.zip")

    for zip_path in [out_dist, out_pub]:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(EXT_DIR):
                for f in files:
                    if f.startswith(".") or f.endswith(".pyc") or f.endswith("~"):
                        continue
                    abs_path = os.path.join(root, f)
                    rel_path = os.path.relpath(abs_path, EXT_DIR)
                    zipf.write(abs_path, arcname=rel_path)
        print(f"  ✓ Created: {zip_path} ({os.path.getsize(zip_path):,} bytes)")

def summary():
    print("[3/3] Extension Packaging Complete!")
    print("  Ready for Chrome Web Store upload & direct browser loading:")
    print("  1. Load Unpacked: Point Chrome to /home/redking/Projects/vn_hotel_star_watchdog/extension")
    print("  2. Web Store Package: /home/redking/Projects/vn_hotel_star_watchdog/dist/truestars_extension.zip")

if __name__ == "__main__":
    validate_manifest()
    build_zip()
    summary()
