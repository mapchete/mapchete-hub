from click.testing import CliRunner

from mapchete_hub.cli.server import main as mhub_server


def test_mhub_server():
    result = CliRunner(env=dict(MAPCHETE_TEST="TRUE")).invoke(mhub_server, ["--help"])
    assert result.exit_code == 0
