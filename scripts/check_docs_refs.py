#!/usr/bin/env python3
"""Check documentation references — detect broken internal links in markdown.

Scans all tracked `.md` files (excluding `docs/archive/` historical documents and
vendored directories) for references to local files that don't exist.

Excludes `docs/archive/` which contains historical documents with intentionally
stale links (they carry the ⚠️ HISTÓRICO banner).

Usage:
    python scripts/check_docs_refs.py

Exit code:
    0 — no broken references found
    1 — at least one broken reference found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Directories to skip entirely (vendored, build artifacts, VCS metadata)
SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "site",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "target",
        "dist",
        "build",
    }
)

# docs/archive/ contains historical documents whose links are intentionally stale
ARCHIVE_DIR = Path("docs/archive")

VALID_EXTENSIONS = frozenset(
    {
        ".md",
        ".py",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".csv",
        ".sh",
        ".cfg",
        ".ini",
        ".txt",
        ".env",
        ".lock",
        ".conf",
        ".sql",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".rs",
        ".png",
        ".svg",
        ".jpg",
        ".jpeg",
        ".gif",
        ".pdf",
        ".xml",
        ".db",
        ".wasm",
    }
)

# Files/dirs that are acceptable to reference as non-existent (CI-generated artifacts)
ALLOWED_MISSING = frozenset(
    {
        "reports/audit_baseline.json",
        "reports/validation/ci",
    }
)


def find_md_files(root: Path) -> list[Path]:
    """Recursively find all .md files, skipping vendored directories."""
    results: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        results.append(path)
    return sorted(results)


def strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks and inline code from markdown content."""
    lines = content.split("\n")
    result: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            result.append("")
            continue
        if in_fence:
            result.append("")
            continue
        # Remove inline code spans
        line = re.sub(r"`[^`]*`", "", line)
        result.append(line)
    return "\n".join(result)


def extract_link_targets(text: str) -> list[tuple[str, int]]:
    """Extract file paths from markdown link syntax.

    Checks both inline links [text](url) and reference-style [text]: url.
    Skips URLs (http/https), anchors (#), images, and non-file links.
    """
    refs: list[tuple[str, int]] = []
    lines = text.split("\n")
    for lineno, line in enumerate(lines, 1):
        # Inline links: [text](url) or [text](url "title")
        for m in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", line):
            target = m.group(1).strip()
            # Skip URLs, anchors, mailto, data URIs
            if (
                target.startswith("#")
                or target.startswith("http://")
                or target.startswith("https://")
                or target.startswith("mailto:")
                or target.startswith("data:")
                or target.startswith("attachment:")
            ):
                continue
            # Strip title: [text](url "title")
            target = target.split('"')[0].strip()
            if not target:
                continue
            refs.append((target, lineno))

        # Reference-style: [text]: url
        for m in re.finditer(r"^\s*\[[^\]]+\]:\s*(\S+)", line):
            target = m.group(1).strip()
            if target.startswith("#") or target.startswith("http"):
                continue
            refs.append((target, lineno))

    return refs


def extract_bare_paths(text: str) -> list[tuple[str, int]]:
    """Extract bare file path references from markdown text.

    Only matches paths that:
    - Contain a slash (relative paths like docs/foo.md)
    - Start with known directory prefixes or relative markers (./, ../)
    - Have a valid file extension
    """
    refs: list[tuple[str, int]] = []
    lines = text.split("\n")

    # Known directory prefixes that indicate real file paths
    known_prefixes = (
        "docs/",
        "src/",
        "tests/",
        "backend/",
        "frontend/",
        "massive/",
        "services/",
        "datasets/",
        "configs/",
        "data/",
        "models/",
        "reports/",
        "scripts/",
        "experiments/",
        "schemas/",
        "monitoring/",
        "benchmarks/",
        "rust_core/",
        "target/",
        ".github/",
        "site/",
    )

    for lineno, line in enumerate(lines, 1):
        for m in re.finditer(
            r"(?<![\w/`])((?:\.\./|\./)?(?:[^\s`<>(){}|\\]+/)+[^\s`<>(){}|\\]+\.[a-z]{2,4})",
            line,
            re.IGNORECASE,
        ):
            path = m.group(1)
            # Skip URLs
            if "://" in path or path.startswith("http"):
                continue
            # Skip paths with special chars
            if any(c in path for c in "(){}|"):
                continue
            # Only accept if starts with known prefix or relative marker
            if path.startswith("../") or path.startswith("./"):
                pass  # relative path, accept
            elif path.startswith(known_prefixes):
                pass  # known directory prefix
            else:
                # Check if first component is a known directory
                first_component = path.split("/")[0]
                if not any(
                    kp.startswith(first_component + "/") for kp in known_prefixes
                ) and first_component not in {kp.rstrip("/") for kp in known_prefixes}:
                    continue  # not a known directory, likely false positive
            refs.append((path, lineno))

    return refs


def resolve_reference(ref: str, source: Path, root: Path) -> Path | None:
    """Try to resolve a reference relative to source file or repo root."""
    ref = ref.strip().strip("'\"")

    # Skip if it contains URL-like elements
    if "://" in ref or ref.startswith("http") or ref.startswith("file:"):
        return None  # not a local path, skip

    # Skip absolute URL paths (like /openapi/v1.json)
    if ref.startswith("/"):
        return None  # treat as URL path, not a local file

    # Try relative to the referencing file's directory
    source_dir = source.parent
    candidate = (source_dir / ref).resolve()
    if candidate.exists():
        return candidate

    # Try relative to repo root
    candidate = (root / ref).resolve()
    if candidate.exists():
        return candidate

    # Try relative to docs/ directory (common pattern in markdown)
    candidate = (root / "docs" / ref).resolve()
    if candidate.exists():
        return candidate

    # Try basename match (search by filename)
    base = Path(ref).name
    for found in root.rglob(base):
        if found.is_file() and not any(part in SKIP_DIRS for part in found.parts):
            return found

    return None


def main() -> int:
    root = Path.cwd()
    md_files = find_md_files(root)

    broken_refs: list[tuple[str, str, int]] = []

    for md_file in md_files:
        try:
            rel = md_file.relative_to(root)
        except ValueError:
            continue

        # Skip docs/archive/ — historical documents with intentionally stale links
        if ARCHIVE_DIR in rel.parents or rel == ARCHIVE_DIR:
            continue

        try:
            raw_content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Strip code blocks for reference checking
        text = strip_code_blocks(raw_content)

        # Extract references
        all_refs: set[tuple[str, int]] = set()
        for ref, lineno in extract_link_targets(text):
            all_refs.add((ref, lineno))
        for ref, lineno in extract_bare_paths(text):
            all_refs.add((ref, lineno))

        for ref, lineno in sorted(all_refs, key=lambda x: (x[1], x[0])):
            # Skip allowed missing paths
            if ref in ALLOWED_MISSING:
                continue
            # Skip paths with fragments/queries
            if "?" in ref or "#" in ref:
                continue
            # Skip URL-like paths (file://, http://, etc.) — not local file refs
            if "://" in ref or ref.startswith("file:"):
                continue

            resolved = resolve_reference(ref, md_file, root)
            if resolved is None:
                broken_refs.append((str(rel), ref, lineno))

    # Report
    if broken_refs:
        print(f"🔗 {len(broken_refs)} rutas inexistentes:")
        for source, ref, lineno in sorted(broken_refs):
            print(f"  {source}:{lineno} → {ref}")
    else:
        print("0 rutas inexistentes")

    return 1 if broken_refs else 0


if __name__ == "__main__":
    sys.exit(main())
