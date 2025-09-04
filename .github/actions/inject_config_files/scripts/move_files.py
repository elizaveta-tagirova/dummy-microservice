import argparse, pathlib, shutil
import yaml


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="prod", help="Environment subfolder under .orchestrator-configs")
    ap.add_argument("--root", default=".", help="Repo root (for safety join)")
    ap.add_argument("--orchestrator-pushed-root", default=".orchestrator-configs", help="Where B pushed artifacts")
    args = ap.parse_args()

    repo_root = pathlib.Path(args.root).resolve()
    orchestrator_root  = (repo_root / args.orchestrator_pushed_root / args.env).resolve()
    files_dir = orchestrator_root / "files"

    if not orchestrator_root.exists():
        raise SystemExit(f"Orchestrator pushed folder not found: {orchestrator_root}")

    if not files_dir.exists():
        raise SystemExit(f"Orchestrator pushed files folder not found: {files_dir}")

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
        shutil.copyfile(p, dest_abs)


if __name__ == "__main__":
    main()
