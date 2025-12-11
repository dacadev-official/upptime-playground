#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def _leading_spaces(s: str) -> str:
    return s[: len(s) - len(s.lstrip(" "))]


def patch_checkout_ref(text: str, branch: str) -> tuple[str, bool]:
    lines = text.splitlines(True)  # keep line endings
    changed = False

    i = 0
    while i < len(lines):
        line = lines[i]
        if "uses: actions/checkout@v" in line:
            uses_indent = _leading_spaces(line)

            # Find `with:` at same indentation as `uses:` (typical pattern)
            j = i + 1
            with_idx = None
            while j < len(lines):
                curr_line = lines[j]
                if curr_line.strip() == "":
                    j += 1
                    continue

                # End of this step block if indentation decreases below `uses_indent`
                if len(_leading_spaces(curr_line)) < len(uses_indent):
                    break

                if curr_line.startswith(f"{uses_indent}with:"):
                    with_idx = j
                    break
                j += 1

            if with_idx is None:
                i += 1
                continue

            inner_indent = uses_indent + "  "

            # Scan keys under with: until indentation drops back to uses_indent (or with ends)
            k = with_idx + 1
            ref_idx = None
            insert_before_idx = None
            while k < len(lines):
                curr_line = lines[k]
                if curr_line.strip() == "":
                    k += 1
                    continue

                if len(_leading_spaces(curr_line)) <= len(uses_indent):
                    break

                if curr_line.startswith(inner_indent + "ref:"):
                    ref_idx = k
                    break

                # Prefer inserting before token if present
                if insert_before_idx is None and curr_line.startswith(inner_indent + "token:"):
                    insert_before_idx = k

                k += 1

            desired = inner_indent + f"ref: {branch}\n"
            if ref_idx is not None:
                if lines[ref_idx] != desired:
                    lines[ref_idx] = desired
                    changed = True
            else:
                if insert_before_idx is None:
                    insert_before_idx = with_idx + 1
                lines.insert(insert_before_idx, desired)
                changed = True
                # Adjust cursor because we inserted
                i += 1
        i += 1

    return "".join(lines), changed


def main() -> int:
    branch = sys.argv[1] if len(sys.argv) > 1 else "status-monitoring"

    # Patch only the Upptime-managed workflows (avoid touching unrelated workflows).
    workflow_dir = Path(".github/workflows")
    targets = [
        workflow_dir / "graphs.yml",
        workflow_dir / "response-time.yml",
        workflow_dir / "setup.yml",
        workflow_dir / "site.yml",
        workflow_dir / "summary.yml",
        workflow_dir / "update-template.yml",
        workflow_dir / "updates.yml",
        workflow_dir / "uptime.yml",
    ]

    any_changed = False
    for path in targets:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated, changed = patch_checkout_ref(original, branch)
        if changed:
            path.write_text(updated, encoding="utf-8")
            any_changed = True

    print(f"Patched workflows to checkout ref: {branch}" if any_changed else "No workflow changes needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
