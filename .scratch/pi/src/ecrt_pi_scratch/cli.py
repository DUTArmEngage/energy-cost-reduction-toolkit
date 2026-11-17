"""`uv run ecrt-ui` starts the Streamlit UI (extra arguments go to `streamlit run`)."""
from __future__ import annotations

import sys
from pathlib import Path


def run_ui() -> None:
    from streamlit.web import cli as stcli

    # minimal toolbar (no Deploy button or menu), no usage stats, no welcome message or "install agent skills" toast.
    # Extra arguments from the command line are passed on.
    sys.argv = ["streamlit", "run", str(Path(__file__).with_name("app.py")), "--client.toolbarMode", "minimal",
                "--browser.gatherUsageStats", "false", "--logger.hideWelcomeMessage", "true", *sys.argv[1:]]
    sys.exit(stcli.main())
