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
    if not str(dst).startswith(str(root) + "/") and dst != root:
        raise SystemExit(f"Refusing to write outside repo: {dst}")
    return dst

def has_copyable_files(d: pathlib.Path) -> bool:
    try:
        for c in d.iterdir():
            if c.is_file() and not c.name.endswith(".meta"):
                return True
    except FileNotFoundError:
        return False
    return False

def find_files_dir(src_root: pathlib.Path, env: Optional[str]) -> pathlib.Path:
    # 1) <source>/<env>/files
    if env:
        d = src_root / env / "files"
        if d.is_dir():
            return d
    # 2) <source>/files
    d = src_root / "files"
    if d.is_dir():
        return d
    # 3) any "* / files" within 3 levels (grab first that has files)
    for d in src_root.glob("**/files"):
        if d.is_dir() and has_copyable_files(d):
            return d
    # 4) last resort: top-level only if it actually has files
    if src_root.is_dir() and has_copyable_files(src_root):
        return src_root

    tried = []
    if env:
        tried.append(str(src_root / env / "files"))
    tried.append(str(src_root / "files"))
    tried.append(f"{src_root}/**/files")
    tried.append(str(src_root))
    raise SystemExit(f"Could not locate files dir with copyable files under {src_root}. Tried: {', '.join(tried)}")

def main() -> None:
    ap = argparse.ArgumentParser(description="Move orchestrator files into repo paths from .meta 'destination'")
    ap.add_argument("--env", default="prod", help="Environment name (for <env>/files layout)")
    ap.add_argument("--root", default=".", help="Repo root (safety base for destinations)")
    ap.add_argument("--source-path", required=True, help="Artifact extraction root")
    args = ap.parse_args()

    repo_root = pathlib.Path(args.root).resolve()
    src_root = pathlib.Path(args.source_path).resolve()
    files_dir = find_files_dir(src_root, args.env)

    print(f"[info] using files_dir: {files_dir}")
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
