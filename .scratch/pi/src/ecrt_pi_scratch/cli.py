"""`uv run ecrt-ui` starts the Streamlit UI (extra arguments go to `streamlit run`)."""
from __future__ import annotations

import sys
from pathlib import Path


def run_ui() -> None:
    from streamlit.web import cli as stcli

    sys.argv = streamlit_args(sys.argv[1:])
    sys.exit(stcli.main())


def streamlit_args(extra: list[str]) -> list[str]:
    """The `streamlit run` command line: minimal toolbar (no Deploy button or menu), no usage stats, no welcome message or
    "install agent skills" toast. developmentMode is off explicitly: Streamlit switches it on whenever its own folder is not
    called site-packages, as in the .deb, and then rejects --server.port. Extra arguments from the command line are passed on."""
    app = str(Path(__file__).with_name("app.py"))
    return ["streamlit", "run", app, "--client.toolbarMode", "minimal", "--browser.gatherUsageStats", "false",
            "--logger.hideWelcomeMessage", "true", "--global.developmentMode", "false", *extra]
