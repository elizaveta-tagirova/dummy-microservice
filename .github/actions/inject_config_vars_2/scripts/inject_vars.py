import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

# Case-insensitive match for placeholders like {{ vars.NAME }}
PLACEHOLDER_RE = re.compile(r"\{\{\s*vars\.([A-Za-z0-9_]+)\s*\}\}", flags=re.IGNORECASE)


def load_map(map_path: Optional[Path]) -> List[dict]:
    if not map_path:
        return []
    if not map_path.exists():
        return []
    try:
        doc = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise SystemExit(f"Failed to read vars map {map_path}: {e}")

    targets = doc.get("targets", [])
    if not isinstance(targets, list):
        raise SystemExit("vars-map.yaml: 'targets' must be a list")
    for t in targets:
        if "path" not in t:
            raise SystemExit("Each target must have a 'path'")
        if "vars" in t and not isinstance(t["vars"], list):
            raise SystemExit("'vars' must be a list of variable names")
    return targets


def replace_in_text(
    text: str,
    var_values_ci: Dict[str, str],
    allow_vars_ci: Optional[Set[str]],
) -> Tuple[str, int, List[str]]:
    missing: Set[str] = set()
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        name = m.group(1).lower()  # normalize to lowercase
        if allow_vars_ci is not None and name not in allow_vars_ci:
            return m.group(0)  # leave as-is
        if name not in var_values_ci:
            missing.add(name)
            return m.group(0)
        count += 1
        return str(var_values_ci[name])  # file controls quoting

    new_text = PLACEHOLDER_RE.sub(repl, text)
    return new_text, count, sorted(missing)


def collect_placeholders_ci(text: str) -> Set[str]:
    # Lower-cased set of placeholder names present
    return {m.group(1).lower() for m in PLACEHOLDER_RE.finditer(text)}


def main() -> None:
    p = argparse.ArgumentParser(
        description="Inject variables by replacing {{ vars.NAME }} in mapped files."
    )
    p.add_argument(
        "--vars-json",
        type=json.loads,
        required=True,
        help="Inline JSON object with {name: value}",
    )
    p.add_argument(
        "--map",
        default="vars-map.yaml",
        help="Path to vars-map.yaml (optional). Format: {targets:[{path:<file>, vars:[<name>...]}]}",
    )
    args = p.parse_args()

    # Normalize variables case-insensitively
    var_values_ci = {str(k).lower(): str(v) for k, v in dict(args.vars_json).items()}

    targets = load_map(Path(args.map) if args.map else None)

    total_changes = 0
    missing_any: Set[str] = set()

    for t in targets:
        path = Path(t["path"])
        if not path.is_file():
            print(f"[skip] {path} (not found)", file=sys.stderr)
            continue

        allow_vars_ci: Optional[Set[str]] = None
        if "vars" in t and t["vars"] is not None:
            allow_vars_ci = {str(x).lower() for x in t["vars"]}

        text = path.read_text(encoding="utf-8")

        # If mapping restricts vars and none are present in the file, skip quickly
        if allow_vars_ci is not None:
            present = collect_placeholders_ci(text)
            if present.isdisjoint(allow_vars_ci):
                continue

        new_text, n, missing = replace_in_text(text, var_values_ci, allow_vars_ci)
        if n > 0:
            path.write_text(new_text, encoding="utf-8")
            print(f"[ok] {path} → {n} replacement(s)")
            total_changes += n
        if missing:
            print(f"[warn] {path}: missing vars referenced: {', '.join(missing)}", file=sys.stderr)
            missing_any.update(missing)

    if total_changes == 0:
        print("[info] no replacements performed")
    if missing_any:
        # non-fatal; emit summary on stderr
        print(f"[warn] missing variables overall: {', '.join(sorted(missing_any))}", file=sys.stderr)


if __name__ == "__main__":
    main()
