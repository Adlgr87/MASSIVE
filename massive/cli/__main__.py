"""Allow ``python -m massive.cli`` invocation."""

from massive.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
