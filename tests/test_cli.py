from click.testing import CliRunner

from mapchete_hub.cli import main as mhub_cli


def test_mhub_server():
    result = CliRunner(env=dict(MAPCHETE_TEST="TRUE"), mix_stderr=True).invoke(mhub_cli)
    assert result.exit_code == 0
