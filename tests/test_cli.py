from click.testing import CliRunner

from mapchete_hub.cli import main
from mapchete_hub.config import host_options


def test_start(example_mapchete):
    """mhub start"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "start",
            "test_job",
            example_mapchete.path,
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_status():
    """mhub status"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "status",
            "test_job"
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_progress():
    """mhub progress"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "progress",
            "test_job"
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_jobs():
    """mhub jobs"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "jobs"
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_capabilities():
    """mhub capabilities"""
    result = CliRunner().invoke(main.mhub, "capabilities")
    assert result.exit_code == 0
