from click import BadParameter
from click.testing import CliRunner
import pytest
import time
import uuid

from mapchete_hub.cli import main


JOB_ID = uuid.uuid4().hex


def test_remote_versions(wait_for_api, mhub_test_instance_uri):
    """mhub remote-versions"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "remote-versions",
        ]
    )
    assert result.exit_code == 0
    for p in ["mapchete_hub", "fiona", "rasterio", "gdal"]:
        assert p in result.output


def test_queues(wait_for_api, mhub_test_instance_uri):
    """mhub queues"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "queues"
        ]
    )
    assert result.exit_code == 0
    for queue in ["execute_queue", "index_queue", "overview_queue"]:
        assert queue in result.output


def test_queue(wait_for_api, mhub_test_instance_uri):
    """mhub queues -n execute_queue"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "queues",
            "-n", "execute_queue"
        ]
    )
    assert result.exit_code == 0
    assert "execute_worker@" in result.output

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "queues",
            "-n", "invalid_queue"
        ]
    )
    assert result.exit_code == 0
    assert "no queue" in result.output


def test_processes(wait_for_api, mhub_test_instance_uri):
    """mhub processes"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "processes"
        ]
    )
    assert result.exit_code == 0
    assert "mapchete.processes.examples.example_process" in result.output


def test_processes_docstrings(wait_for_api, mhub_test_instance_uri):
    """mhub processes"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "processes",
            "--docstrings"
        ]
    )
    assert result.exit_code == 0
    assert "Example process for testing." in result.output


def test_process(wait_for_api, mhub_test_instance_uri):
    """mhub processes"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "processes",
            "-n", "mapchete.processes.examples.example_process"
        ]
    )
    assert result.exit_code == 0
    assert "Example process for testing." in result.output


def test_workers(wait_for_api, mhub_test_instance_uri):
    """mhub workers"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "workers"
        ]
    )
    assert result.exit_code == 0
    assert "execute_worker" in result.output
    assert "index_worker" in result.output


def test_job_not_found(wait_for_api, mhub_test_instance_uri):
    """mhub status <job_id>"""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "status", JOB_ID
        ]
    )
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_start_new_job(wait_for_api, mhub_test_instance_uri, test_mapchete):
    """Start job and get job state."""
    # let's create a new job
    # mhub execute testdata/test.mapchete -b -1 0 0 1
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "execute",
            test_mapchete.path,
            "--bounds", "-1", "0", "0", "1"
        ]
    )
    assert result.exit_code == 0
    job_id = result.output.strip()

    time.sleep(2)
    # voilá, a new job with this ID is there
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "status", job_id
        ]
    )
    assert result.exit_code == 0
    assert "command: execute" in result.output

    # let's get the job state until it is finished
    # don't do it more than 10 times
    max_requests = 60
    request_count = 0
    while True:
        request_count += 1
        if request_count > max_requests:
            raise RuntimeError("mhub did not process job")
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "status", job_id
            ]
        )
        if "SUCCESS" in result.output:
            break
        elif "FAILURE" in result.output:
            raise ValueError("job failed")
        time.sleep(1)


def test_start_cancel_job_ids(wait_for_api, mhub_test_instance_uri, test_mapchete):
    """Start jobs and cancel."""
    # let's create two new jobs
    job_ids = []
    for i in range(2):
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "execute",
                test_mapchete.path,
                "--bounds", "-1", "0", "0", "1"
            ]
        )
        assert result.exit_code == 0
        job_ids.append(result.output.strip())

    # wait a couple of seconds
    time.sleep(1)

    # send revoke signals
    for job_id in job_ids:
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "cancel",
                "--force",
                "--job-ids", job_id
            ]
        )
        assert "Revoke signal" in result.output
        assert job_id in result.output

    # wait until job state is changed to TERMINATED
    for job_id in job_ids:
        max_requests = 100
        request_count = 0
        while True:
            request_count += 1
            if request_count > max_requests:
                raise RuntimeError("mhub did not process job")
            result = CliRunner().invoke(
                main.mhub,
                [
                    "-h", mhub_test_instance_uri,
                    "status", job_id
                ]
            )
            if "TERMINATED" in result.output or "REVOKED" in result.output:
                break
            elif "SUCCESS" in result.output:
                raise ValueError("job not terminated")
            elif "FAILURE" in result.output:
                raise ValueError("job failed")
            time.sleep(1)


def test_start_cancel_job_search(wait_for_api, mhub_test_instance_uri, test_mapchete):
    """Start jobs and cancel."""
    # let's create two new jobs
    job_ids = []
    for i in range(2):
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "execute",
                test_mapchete.path,
                "--bounds", "-1", "0", "0", "1"
            ]
        )
        assert result.exit_code == 0
        job_ids.append(result.output.strip())

    # wait a couple of seconds
    time.sleep(1)

    # send revoke signals
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "cancel",
            "--force",
            "--since", "1m"
        ]
    )
    assert "Revoke signal" in result.output
    for job_id in job_ids:
        assert job_id in result.output

    # wait until job state is changed to TERMINATED
    for job_id in job_ids:
        max_requests = 100
        request_count = 0
        while True:
            request_count += 1
            if request_count > max_requests:
                raise RuntimeError("mhub did not process job")
            result = CliRunner().invoke(
                main.mhub,
                [
                    "-h", mhub_test_instance_uri,
                    "status", job_id
                ]
            )
            if "TERMINATED" in result.output or "REVOKED" in result.output:
                break
            elif "SUCCESS" in result.output:
                raise ValueError("job not terminated")
            elif "FAILURE" in result.output:
                raise ValueError("job failed")
            time.sleep(1)


def test_start_new_index_job(wait_for_api, mhub_test_instance_uri, test_mapchete):
    """Start index job and get job state."""
    # let's create a new job
    # mhub execute testdata/test.mapchete -b -1 0 0 1
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "index",
            test_mapchete.path,
            "--bounds", "-1", "0", "0", "1"
        ]
    )
    assert result.exit_code == 0
    job_id = result.output.strip()

    time.sleep(2)
    # voilá, a new job with this ID is there
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "status", job_id
        ]
    )
    assert result.exit_code == 0
    assert "command: index" in result.output

    # let's get the job state until it is finished
    # don't do it more than 10 times
    max_requests = 60
    request_count = 0
    while True:
        request_count += 1
        if request_count > max_requests:
            raise RuntimeError("mhub did not process job")
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "status", job_id
            ]
        )
        if "SUCCESS" in result.output:
            break
        elif "FAILURE" in result.output:
            raise ValueError("job failed")
        time.sleep(1)


def test_start_cancel_batch(wait_for_api, mhub_test_instance_uri, batch_example):
    """Start a new batch process."""
    # start
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "batch",
            batch_example.path,
            "--bounds", "1", "2", "3", "4"
        ]
    )
    assert result.exit_code == 0
    job_id = result.output.strip()

    # cancel
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "cancel",
            "--force",
            "--job-ids", job_id
        ]
    )
    assert "Revoke signal for jobs" in result.output
    assert job_id in result.output


def test_job_progress(wait_for_api, mhub_test_instance_uri, test_mapchete):
    """Start job and get job state."""
    # let's create a new job
    # mhub execute testdata/test.mapchete -b -1 0 0 1
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "execute",
            test_mapchete.path,
            "--bounds", "-0.5", "0", "0", "0.5"
        ]
    )
    assert result.exit_code == 0
    job_id = result.output.strip()

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "progress",
            job_id,
        ]
    )
    assert result.exit_code == 0


def test_jobs(wait_for_api, mhub_test_instance_uri):
    """Start job and get job state."""
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "jobs",
        ]
    )
    assert result.exit_code == 0

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "jobs",
            "-v"
        ]
    )
    assert result.exit_code == 0

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "jobs",
            "--geojson"
        ]
    )
    assert result.exit_code == 0

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "jobs",
            "--sort-by", "started"
        ]
    )
    assert result.exit_code == 0

    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "jobs",
            "--sort-by", "progress"
        ]
    )
    assert result.exit_code == 0


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


def test_retry_single_job(wait_for_api, test_mapchete, mhub_test_instance_uri):
    """Start jobs, cancel and retry."""
    # let's create two new jobs
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "execute",
            test_mapchete.path,
            "--bounds", "-1", "0", "0", "1"
        ]
    )
    assert result.exit_code == 0
    job_id = result.output.strip()

    # wait a couple of seconds
    time.sleep(1)

    # send revoke signals
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "cancel",
            "--force",
            "--since", "1m"
        ]
    )
    assert "Revoke signal" in result.output
    assert job_id in result.output

    # wait until job state is changed to TERMINATED
    max_requests = 100
    request_count = 0
    while True:
        request_count += 1
        if request_count > max_requests:
            raise RuntimeError("mhub did not process job")
        result = CliRunner().invoke(
            main.mhub,
            [
                "-h", mhub_test_instance_uri,
                "status", job_id
            ]
        )
        if "TERMINATED" in result.output or "REVOKED" in result.output:
            break
        elif "SUCCESS" in result.output:
            raise ValueError("job not terminated")
        elif "FAILURE" in result.output:
            raise ValueError("job failed")
        time.sleep(1)

    # retry job by search
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "retry",
            "--force",
            "--since", "5s",
            "--state", "terminated"
        ]
    )

    # retry job by job id
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "retry",
            "--force",
            "--no-children",
            "--job_ids", job_id,
        ]
    )


def test_retry_batch(wait_for_api, batch_example, mhub_test_instance_uri):
    # start
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "batch",
            batch_example.path,
            "--bounds", "1", "2", "3", "4"
        ]
    )
    job_id = result.output.strip()

    # cancel
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "cancel",
            "--force",
            "--job-ids", job_id
        ]
    )

    # retry
    result = CliRunner().invoke(
        main.mhub,
        [
            "-h", mhub_test_instance_uri,
            "retry",
            "--force",
            "--job-ids", job_id
        ]
    )
