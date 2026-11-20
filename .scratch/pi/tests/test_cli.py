import sys

from ecrt_pi_scratch import cli


def test_streamlit_args_turn_development_mode_off_and_pass_extras_on():
    args = cli.streamlit_args(["--server.port", "9000"])
    assert args[:2] == ["streamlit", "run"] and args[2].endswith("app.py")
    flags = dict(zip(args[3:-2:2], args[4:-2:2], strict=False))
    assert flags["--global.developmentMode"] == "false"       # the .deb is not under site-packages: Streamlit would turn it on
    assert flags["--client.toolbarMode"] == "minimal"
    assert args[-2:] == ["--server.port", "9000"]


def test_run_ui_hands_the_arguments_to_streamlit(monkeypatch):
    seen = {}

    def fake_main():
        seen["argv"] = list(sys.argv)
        return 0

    monkeypatch.setattr("streamlit.web.cli.main", fake_main)
    monkeypatch.setattr(sys, "argv", ["ecrt-ui", "--server.port", "9000"])
    try:
        cli.run_ui()
    except SystemExit as e:
        assert e.code == 0
    assert seen["argv"][-2:] == ["--server.port", "9000"] and "--global.developmentMode" in seen["argv"]
