import argparse, json, os, re, sys
from pathlib import Path
import yaml

PLACEHOLDER_RE = re.compile(r"\{\{\s*vars\.([A-Za-z0-9_]+)\s*\}\}")

def load_vars(vars_json_path: Path) -> dict:
    with vars_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect {"VAR_NAME": "value", ...}
    return {str(k): str(v) for k, v in data.items()}

def load_map(map_path: Path | None) -> list[dict]:
    if not map_path:
        return []
    with map_path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    targets = doc.get("targets", [])
    if not isinstance(targets, list):
        raise SystemExit("vars-map.yaml: 'targets' must be a list")
    for t in targets:
        if "path" not in t:
            raise SystemExit("Each target must have a 'path'")
        if "vars" in t and not isinstance(t["vars"], list):
            raise SystemExit("'vars' must be a list of variable names")
    return targets

def replace_in_text(text: str, var_values: dict, allow_vars: set[str] | None) -> tuple[str, int, list[str]]:
    missing = set()
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        name = m.group(1)
        if allow_vars is not None and name not in allow_vars:
            return m.group(0)  # leave as-is
        if name not in var_values:
            missing.add(name)
            return m.group(0)
        count += 1
        return var_values[name]  # no quoting; file decides quoting

    new_text = PLACEHOLDER_RE.sub(repl, text)
    return new_text, count, sorted(missing)

def collect_placeholders(text: str) -> set[str]:
    return set(m.group(1) for m in PLACEHOLDER_RE.finditer(text))

def main():
    p = argparse.ArgumentParser(description="Inject GitHub Variables into files by replacing {{ vars.NAME }}")
    p.add_argument("--vars-json", type=json.loads, required=True, help="JSON with {name: value}")
    p.add_argument("--map", default="vars-map.yaml", help="Path to vars-map.yaml (optional)")
    args = p.parse_args()

    var_values = load_vars(Path(args.vars_json))
    targets = load_map(Path(args.map))

    total_changes = 0
    missing_any = set()

    for t in targets:
        path = Path(t["path"])
        if not path.exists() or not path.is_file():
            print(f"[skip] {path} (not found)", file=sys.stderr)
            continue
        allow_vars = set(t.get("vars")) if "vars" in t else None

        text = path.read_text(encoding="utf-8")
        # If mapping restricts vars, but file has none of them, skip fast
        if allow_vars is not None:
            present = collect_placeholders(text)
            if present.isdisjoint(allow_vars):
                continue

        new_text, n, missing = replace_in_text(text, var_values, allow_vars)
        if n > 0:
            path.write_text(new_text, encoding="utf-8")
            print(f"[ok] {path} → {n} replacement(s)")
            total_changes += n
        if missing:
            print(f"[warn] {path}: missing vars referenced: {', '.join(missing)}", file=sys.stderr)
            missing_any.update(missing)


if __name__ == "__main__":
    main()
