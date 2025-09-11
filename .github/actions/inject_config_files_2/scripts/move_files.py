import argparse
import pathlib
import shutil
import sys
from typing import Optional

import yaml


def read_yaml(p: pathlib.Path) -> dict:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise SystemExit(f"Failed to read YAML meta {p}: {e}")


def safe_join(root: pathlib.Path, rel: str) -> pathlib.Path:
    root = root.resolve()
    dst = (root / rel).resolve()
    # prevent path traversal outside the repo root
    if not str(dst).startswith(str(root) + "/") and dst != root:
        raise SystemExit(f"Refusing to write outside repo: {dst}")
    return dst


def find_files_dir(src_root: pathlib.Path, env: Optional[str]) -> pathlib.Path:
    """
    Try a few sensible layouts:
      1) <source>/
      2) <source>/files
      3) <source>/<env>/files
    """
    candidates = [src_root, src_root / "files"]
    if env:
        candidates.append(src_root / env / "files")

    for d in candidates:
        if d.is_dir():
            return d

    tried = ", ".join(str(c) for c in candidates)
    raise SystemExit(f"Could not locate files dir under {src_root}. Tried: {tried}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Move orchestrator files into repo paths from .meta 'destination'")
    ap.add_argument("--env", default="prod", help="Environment subfolder if layout includes <env>/files")
    ap.add_argument("--root", default=".", help="Repo root (safety base for destinations)")
    ap.add_argument("--source-path", required=True, help="Path that contains the files/.meta bundle")
    args = ap.parse_args()

    repo_root = pathlib.Path(args.root).resolve()
    src_root = pathlib.Path(args.source_path).resolve()
    files_dir = find_files_dir(src_root, args.env)

    if not files_dir.exists():
        raise SystemExit(f"Files folder not found: {files_dir}")

    copied = 0
    for p in sorted(files_dir.iterdir()):
        if not p.is_file() or p.name.endswith(".meta"):
            continue

        meta = p.with_name(p.name + ".meta")
        if not meta.exists():
            raise SystemExit(f"Missing .meta for file: {p}")

        m = read_yaml(meta)
        dest_rel = m.get("destination")
        if not dest_rel:
            raise SystemExit(f"Missing 'destination' in meta: {meta}")

        dest_abs = safe_join(repo_root, str(dest_rel))
        dest_abs.parent.mkdir(parents=True, exist_ok=True)

        print(f"[copy] {p} -> {dest_rel}")
        shutil.copy2(p, dest_abs)
        copied += 1

    print(f"[done] copied {copied} file(s) from {files_dir}")


if __name__ == "__main__":
    main()
