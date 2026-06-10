"""Allow ``python -m logiq`` to run the Collector orchestration CLI."""

from .orchestrate import main

if __name__ == "__main__":
    raise SystemExit(main())
