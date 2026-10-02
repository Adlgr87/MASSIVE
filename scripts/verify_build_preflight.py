#!/usr/bin/env python3
"""Static preflight for the Docker image and the Rust extension.

Catches the classes of defect that only ever surface during a real
``docker compose build`` / ``cargo build`` — in an environment where neither
toolchain is available. It is not a substitute for running the build, but
every check here corresponds to a failure that actually occurred in this
repository:

* ``setcap`` invoked without installing ``libcap2-bin`` → image build aborts.
* ``nginx.conf`` / ``supervisord.conf`` living outside the build context →
  ``COPY`` fails (this was finding C-09).
* ``Cargo.toml`` pointing ``[lib] path`` at a file that does not exist →
  ``cargo build`` fails before compiling anything.
* A fail-closed ``MASSIVE_ALLOWED_HOSTS`` with no default in Compose →
  healthcheck gets 400, container restarts forever.

Exit code 0 = ready to build. Run with ``--verbose`` to list passing checks.

Usage:
    python scripts/verify_build_preflight.py [--verbose]
"""

from __future__ import annotations

import argparse
import configparser
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Commands that need a package installed before they can be invoked in a
# Debian-based image. Maps command -> apt package providing it.
_COMMAND_PACKAGES = {
    "setcap": "libcap2-bin",
    "getcap": "libcap2-bin",
    "curl": "curl",
    "git": "git",
    "gcc": "build-essential",
    "make": "build-essential",
    "nginx": "nginx",
    "supervisord": "supervisor",
}


class Report:
    def __init__(self, verbose: bool = False) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.verbose = verbose

    def ok(self, msg: str) -> None:
        if self.verbose:
            print(f"  OK    {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  WARN  {msg}")

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"  FAIL  {msg}")


# --------------------------------------------------------------------------
# .dockerignore handling
# --------------------------------------------------------------------------


def _dockerignore_patterns() -> list[str]:
    path = ROOT / ".dockerignore"
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _excluded_by(rel: str, patterns: list[str]) -> str | None:
    """Return the pattern excluding ``rel``, or None.

    Negations (``!pattern``) re-include, matching Docker's last-match-wins
    semantics.
    """
    hit: str | None = None
    for pattern in patterns:
        negated = pattern.startswith("!")
        body = pattern[1:] if negated else pattern
        body = body.rstrip("/")
        if (
            fnmatch.fnmatch(rel, body)
            or fnmatch.fnmatch(rel, body + "/*")
            or rel.startswith(body + "/")
        ):
            hit = None if negated else pattern
    return hit


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_dockerfile(report: Report) -> None:
    print("Dockerfile")
    path = ROOT / "Dockerfile"
    if not path.exists():
        report.fail("Dockerfile not found")
        return
    raw_text = path.read_text(encoding="utf-8")
    # Join backslash-continued lines so a multi-line `RUN apt-get install ... \`
    # is seen as one instruction. Without this, package names sitting on
    # continuation lines are invisible and every command looks uninstalled.
    text = re.sub(r"\\\s*\n\s*", " ", raw_text)
    lines = text.splitlines()
    patterns = _dockerignore_patterns()

    # 1. Every COPY source from the build context must exist and be included.
    stage_names = set(re.findall(r"^FROM\s+\S+\s+AS\s+(\S+)", text, re.MULTILINE | re.IGNORECASE))
    for raw in lines:
        line = raw.strip()
        match = re.match(r"^COPY\s+(.*)$", line, re.IGNORECASE)
        if not match:
            continue
        parts = match.group(1).split()
        from_stage = None
        while parts and parts[0].startswith("--"):
            flag = parts.pop(0)
            if flag.startswith("--from="):
                from_stage = flag.split("=", 1)[1]
        if from_stage is not None:
            if from_stage not in stage_names and not from_stage.isdigit():
                report.fail(f"COPY --from={from_stage} references an unknown stage")
            else:
                report.ok(f"COPY --from={from_stage} (inter-stage, not from context)")
            continue
        for src in parts[:-1]:
            if src == ".":
                report.ok("COPY . (whole context)")
                continue
            if not (ROOT / src).exists():
                report.fail(f"COPY source does not exist in the repo: {src}")
                continue
            excluded = _excluded_by(src, patterns)
            if excluded:
                report.fail(f"COPY source {src} is excluded by .dockerignore rule '{excluded}'")
            else:
                report.ok(f"COPY {src}")

    # 2. Commands used in RUN must have their providing package installed.
    installed: set[str] = set()
    for raw in lines:
        if re.match(r"^\s*(RUN\s+)?.*apt-get\s+install", raw, re.IGNORECASE):
            installed.update(re.findall(r"[a-z0-9][a-z0-9.+-]+", raw.lower()))
    for command, package in _COMMAND_PACKAGES.items():
        used = re.search(rf"^\s*RUN\s+.*\b{re.escape(command)}\b", text, re.MULTILINE)
        if not used:
            continue
        if package.lower() in installed:
            report.ok(f"`{command}` used in RUN and `{package}` is installed")
        else:
            report.fail(
                f"`{command}` is used in a RUN layer but the package providing it "
                f"(`{package}`) is never apt-installed — the build will abort"
            )

    # 3. The entrypoint/command target must exist.
    if "supervisord" in text:
        if (ROOT / "supervisord.conf").exists():
            report.ok("supervisord.conf present for CMD")
        else:
            report.fail("CMD runs supervisord but supervisord.conf is missing")


def check_compose(report: Report) -> None:
    print("docker-compose.yml")
    path = ROOT / "docker-compose.yml"
    if not path.exists():
        report.fail("docker-compose.yml not found")
        return
    try:
        import yaml
    except ImportError:
        report.warn("pyyaml not installed — skipping Compose schema checks")
        return

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = data.get("services") or {}
    if not services:
        report.fail("docker-compose.yml declares no services")
        return

    for name, svc in services.items():
        # A required env_file that does not exist breaks `docker compose up`.
        for entry in svc.get("env_file") or []:
            if isinstance(entry, str):
                if not (ROOT / entry).exists():
                    report.fail(
                        f"service '{name}': env_file '{entry}' is required but missing — "
                        f"`docker compose up` will fail on a clean checkout. Use "
                        f"`- path: {entry}` + `required: false`."
                    )
                else:
                    report.ok(f"service '{name}': env_file '{entry}' present")
            elif isinstance(entry, dict):
                target = entry.get("path", "")
                if entry.get("required", True) and not (ROOT / target).exists():
                    report.fail(f"service '{name}': env_file '{target}' required but missing")
                else:
                    report.ok(f"service '{name}': env_file '{target}' optional or present")

        # Bind-mounting a non-existent host file makes Docker create a DIRECTORY.
        for vol in svc.get("volumes") or []:
            if not isinstance(vol, str) or ":" not in vol:
                continue
            source = vol.split(":", 1)[0]
            if not source.startswith((".", "/")):
                continue  # named volume
            if not (ROOT / source.lstrip("./")).exists():
                report.fail(
                    f"service '{name}': bind-mount source '{source}' does not exist — "
                    f"Docker will silently create a DIRECTORY there"
                )
            else:
                report.ok(f"service '{name}': bind-mount '{source}' exists")

        # The API fails closed without a Host allow-list; the healthcheck
        # would then get 400 and the container would restart forever.
        env = svc.get("environment") or []
        env_text = (
            " ".join(env) if isinstance(env, list) else " ".join(f"{k}={v}" for k, v in env.items())
        )
        if "MASSIVE_ALLOWED_HOSTS" in env_text:
            report.ok(f"service '{name}': MASSIVE_ALLOWED_HOSTS has a default")
        else:
            report.warn(
                f"service '{name}': no MASSIVE_ALLOWED_HOSTS default. The API fails "
                f"closed outside development, so every request (including the "
                f"healthcheck) would return 400 unless .env supplies it."
            )


def check_nginx(report: Report) -> None:
    print("nginx.conf")
    path = ROOT / "nginx.conf"
    if not path.exists():
        report.fail("nginx.conf not found")
        return
    text = path.read_text(encoding="utf-8")

    if text.count("{") != text.count("}"):
        report.fail(f"unbalanced braces ({text.count('{')} open, {text.count('}')} close)")
    else:
        report.ok("braces balanced")

    # Running as non-root: pid and temp paths must be writable.
    for directive in (
        "pid",
        "client_body_temp_path",
        "proxy_temp_path",
        "fastcgi_temp_path",
        "uwsgi_temp_path",
        "scgi_temp_path",
    ):
        match = re.search(rf"^\s*{directive}\s+(\S+);", text, re.MULTILINE)
        if not match:
            report.warn(f"`{directive}` not set — defaults may be unwritable for non-root nginx")
            continue
        value = match.group(1)
        if value.startswith(("/tmp", "/dev/shm", "/var/tmp")):
            report.ok(f"{directive} -> {value} (writable by non-root)")
        else:
            report.warn(f"{directive} -> {value} may not be writable by the non-root user")

    # The upstream must match the port uvicorn actually binds.
    upstream_ports = set(re.findall(r"server\s+127\.0\.0\.1:(\d+)", text))
    supervisord = ROOT / "supervisord.conf"
    if upstream_ports and supervisord.exists():
        sup_ports = set(re.findall(r"--port\s+(\d+)", supervisord.read_text(encoding="utf-8")))
        if sup_ports and not (upstream_ports & sup_ports):
            report.fail(
                f"nginx upstream ports {sorted(upstream_ports)} do not match the "
                f"uvicorn port(s) {sorted(sup_ports)} in supervisord.conf"
            )
        else:
            report.ok(f"nginx upstream port matches uvicorn ({sorted(upstream_ports)})")


def check_supervisord(report: Report) -> None:
    print("supervisord.conf")
    path = ROOT / "supervisord.conf"
    if not path.exists():
        report.fail("supervisord.conf not found")
        return
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read_string(path.read_text(encoding="utf-8"))
    except configparser.Error as exc:
        report.fail(f"not parseable as INI: {exc}")
        return
    report.ok("parses as INI")

    programs = [s for s in parser.sections() if s.startswith("program:")]
    if not programs:
        report.fail("declares no [program:*] sections — the container would start nothing")
        return
    for section in programs:
        command = parser.get(section, "command", fallback="")
        if not command:
            report.fail(f"{section}: no command")
            continue
        report.ok(f"{section}: {command.split()[0]}")

        # A uvicorn target must be importable from the repo.
        target = re.search(r"uvicorn\s+([\w.]+):(\w+)", command)
        if target:
            module_path = ROOT / (target.group(1).replace(".", "/") + ".py")
            if module_path.exists():
                report.ok(f"{section}: ASGI module {target.group(1)} exists")
            else:
                report.fail(f"{section}: ASGI module {target.group(1)} not found")


def check_rust(report: Report) -> None:
    print("rust_core")
    manifest = ROOT / "rust_core" / "Cargo.toml"
    if not manifest.exists():
        report.warn("rust_core/Cargo.toml not found — Rust acceleration unavailable")
        return
    text = manifest.read_text(encoding="utf-8")

    # [lib] path is relative to the manifest directory, a classic trap.
    match = re.search(r'^\s*path\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match:
        lib_path = manifest.parent / match.group(1)
        if lib_path.exists():
            report.ok(f"[lib] path -> {lib_path.relative_to(ROOT)}")
        else:
            report.fail(
                f"[lib] path '{match.group(1)}' resolves to "
                f"{lib_path.relative_to(ROOT) if ROOT in lib_path.parents else lib_path}, "
                f"which does not exist (paths are relative to Cargo.toml's directory)"
            )
    else:
        report.warn("[lib] path not declared; cargo will assume src/lib.rs")

    # The PyO3 module name must equal what Python imports.
    module = (
        re.search(
            r"#\[pymodule\]\s*\n\s*fn\s+(\w+)",
            (manifest.parent / "src" / "lib.rs").read_text(encoding="utf-8"),
        )
        if (manifest.parent / "src" / "lib.rs").exists()
        else None
    )
    lib_name = re.search(r'^\s*name\s*=\s*"(\w+)"', text.split("[lib]", 1)[-1], re.MULTILINE)
    if module and lib_name:
        if module.group(1) == lib_name.group(1):
            report.ok(f"#[pymodule] `{module.group(1)}` matches [lib] name")
        else:
            report.fail(
                f"#[pymodule] is `{module.group(1)}` but [lib] name is "
                f"`{lib_name.group(1)}` — the extension would not be importable"
            )

    # Python must tolerate the extension being absent.
    wrapper = ROOT / "massive_core" / "rust_core.py"
    if wrapper.exists():
        src = wrapper.read_text(encoding="utf-8")
        if "find_spec" in src or "ImportError" in src:
            report.ok("Python wrapper degrades gracefully when the extension is absent")
        else:
            report.fail("massive_core/rust_core.py has no import guard for the optional extension")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", "-v", action="store_true", help="list passing checks too")
    args = parser.parse_args()

    report = Report(verbose=args.verbose)
    for check in (
        check_dockerfile,
        check_compose,
        check_nginx,
        check_supervisord,
        check_rust,
    ):
        check(report)

    print()
    if report.failures:
        print(
            f"PREFLIGHT FAILED: {len(report.failures)} blocking issue(s), {len(report.warnings)} warning(s)"
        )
        return 1
    print(f"PREFLIGHT OK: 0 blocking issues, {len(report.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
