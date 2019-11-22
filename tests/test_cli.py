from click import BadParameter
from click.testing import CliRunner
import pytest

from mapchete_hub.cli import main
from mapchete_hub.config import host_options


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


def test_processes():
    """mhub processes"""
    result = CliRunner().invoke(main.mhub, "processes")
    assert result.exit_code == 0
    assert "no mhub server found" in result.output
    result = CliRunner().invoke(main.mhub, "processes", "--docstrings")
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_queues():
    """mhub queues"""
    result = CliRunner().invoke(main.mhub, "queues")
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_execute(example_mapchete):
    """mhub execute"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "execute",
            example_mapchete.path,
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_index(example_mapchete):
    """mhub index"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", "%s:%s" % (host_options["host_ip"], host_options["port"]),
            "index",
            example_mapchete.path,
        ]
    )
    assert result.exit_code == 0
    assert "no mhub server found" in result.output


def test_get_timestamp():
    assert main._get_timestamp(None, None, "2019-11-01T15:00:00.12")
    assert main._get_timestamp(None, None, "2019-11-01T15:00:00")
    assert main._get_timestamp(None, None, "2019-11-01")
    assert main._get_timestamp(None, None, "3d")
    assert main._get_timestamp(None, None, "3h")
    assert main._get_timestamp(None, None, "3m")
    assert main._get_timestamp(None, None, "3s")
    with pytest.raises(BadParameter):
        assert main._get_timestamp(None, None, "invalid")
    with pytest.raises(BadParameter):
        assert main._get_timestamp(None, None, "3k")
