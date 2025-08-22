import argparse, sys, pathlib, shutil, os
from typing import List
import yaml

COMMENT_PREFIXES = ("//", "#", ";", "--")

def read_yaml(p: pathlib.Path) -> dict:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise SystemExit(f"Failed to read YAML meta {p}: {e}")

def safe_join(root: pathlib.Path, rel: str) -> pathlib.Path:
    dst = (root / rel).resolve()
    if not str(dst).startswith(str(root.resolve())):
        raise SystemExit(f"Refusing to write outside repo: {dst}")
    return dst

def inject_block(dest_file: pathlib.Path, block_name: str, payload: str) -> None:
    begin_tag = f">>> BEGIN GENERATED ({block_name})"
    end_tag   = "<<< END GENERATED"

    lines: List[str] = dest_file.read_text(encoding="utf-8").splitlines(True)
    out: List[str] = []
    i, replaced = 0, False
    # Ensure trailing newline in payload
    if not payload.endswith("\n"):
        payload += "\n"

    while i < len(lines):
        ln = lines[i]
        if any(ln.lstrip().startswith(cp) and begin_tag in ln for cp in COMMENT_PREFIXES):
            # Keep the BEGIN line as-is
            out.append(ln)
            # Write payload body
            out.append(payload)
            replaced = True
            i += 1
            # Skip existing body until END marker
            while i < len(lines) and not any(lines[i].lstrip().startswith(cp) and end_tag in lines[i] for cp in COMMENT_PREFIXES):
                i += 1
            if i < len(lines):
                # Keep the END line
                out.append(lines[i])
            else:
                raise SystemExit(f"Missing END marker '{end_tag}' in {dest_file}")
        else:
            out.append(ln)
        i += 1

    if not replaced:
        raise SystemExit(f"Block '{block_name}' not found in {dest_file}")
    dest_file.write_text("".join(out), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="prod", help="Environment subfolder under .config/generated")
    ap.add_argument("--root", default=".", help="Repo root (for safety join)")
    ap.add_argument("--generated-root", default=".config/generated", help="Where B pushed artifacts")
    args = ap.parse_args()

    repo_root = pathlib.Path(args.root).resolve()
    gen_root  = (repo_root / args.generated_root / args.env).resolve()
    files_dir = gen_root / "files"
    blocks_dir = gen_root / "blocks"

    if not gen_root.exists():
        raise SystemExit(f"Generated folder not found: {gen_root}")

    # 1) Copy files according to .meta
    if files_dir.exists():
        for p in sorted(files_dir.iterdir()):
            if p.suffix == ".meta" or not p.is_file():
                continue
            meta = (p.parent / (p.name + ".meta"))
            if not meta.exists():
                raise SystemExit(f"Missing .meta for file: {p}")
            m = read_yaml(meta)
            dest_rel = m.get("destination")
            if not dest_rel:
                raise SystemExit(f"Missing 'destination' in meta: {meta}")
            dest_abs = safe_join(repo_root, dest_rel)
            dest_abs.parent.mkdir(parents=True, exist_ok=True)
            print(f"[copy] {p} -> {dest_rel}")
            if not args.dry_run:
                shutil.copyfile(p, dest_abs)

    # 2) Inject blocks according to .meta
    if blocks_dir.exists():
        for p in sorted(blocks_dir.iterdir()):
            if p.suffix == ".meta" or not p.is_file():
                continue
            meta = (p.parent / (p.name + ".meta"))
            if not meta.exists():
                raise SystemExit(f"Missing .meta for block: {p}")
            m = read_yaml(meta)
            dest_file_rel = m.get("destination")
            block_name = m.get("block_name")
            if not dest_file_rel or not block_name:
                raise SystemExit(f"Meta for {p} must contain 'destination' and 'block_name': {meta}")
            dest_file = safe_join(repo_root, dest_file_rel)
            if not dest_file.exists():
                raise SystemExit(f"Destination file not found: {dest_file}")
            payload = p.read_text(encoding="utf-8")
            print(f"[inject] {p} -> {dest_file_rel} (block '{block_name}')")
            if not args.dry_run:
                inject_block(dest_file, block_name, payload)

    print("Done.")

if __name__ == "__main__":
    main()
