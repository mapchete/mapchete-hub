"""
Convenience tools to wrap API.

This module wraps around the requests module for real-life usage and Flask's test_client()
in order to be able to test mhub CLI.
"""

from collections import namedtuple
import geojson
import json
import logging
import requests
from requests.exceptions import ConnectionError
import time
import uuid
import yaml

from mapchete_hub.config import cleanup_datetime, timeout
from mapchete_hub.exceptions import JobFailed, JobNotFound, JobRejected


logger = logging.getLogger(__name__)


job_states = {
    "todo": ["PENDING"],
    "doing": ["PROGRESS", "RECEIVED", "STARTED"],
    "done": ["SUCCESS", "FAILURE"]
}


class Job():
    """Job metadata class."""

    def __init__(
        self, status_code=None, state=None, job_id=None, json=None
    ):
        """Initialize."""
        self.status_code = status_code
        self.state = state
        self.job_id = job_id
        self.exists = True if status_code == 409 else False
        self.json = json

    def __repr__(self):
        """Print Job."""
        return "Job(status_code=%s, state=%s, job_id=%s, json=%s" % (
            self.status_code, self.state, self.job_id, self.json
        )


Response = namedtuple("Response", "status_code json")


class API():
    """API class which abstracts REST interface."""

    def __init__(self, host=None, _test_client=None):
        """Initialize."""
        self.host = host
        self._test_client = _test_client
        self._api = _test_client if _test_client else requests
        self._baseurl = "" if _test_client else "http://%s/" % host

    def get(self, url, **kwargs):
        """Make a GET request to _test_client or host."""
        try:
            res = self._api.get(
                self._baseurl + url,
                **self._get_kwargs(kwargs)
            )
            return Response(
                status_code=res.status_code,
                json=res.json if self._test_client else json.loads(res.text)
            )
        except ConnectionError:
            raise ConnectionError("no mhub server found at %s" % self.host)

    def post(self, url, **kwargs):
        """Make a POST request to _test_client or host."""
        try:
            res = self._api.post(self._baseurl + url, **self._get_kwargs(kwargs))
            return Response(
                status_code=res.status_code,
                json=res.json if self._test_client else json.loads(res.text)
            )
        except ConnectionError:
            raise ConnectionError("no mhub server found at %s" % self.host)

    def start_job(
        self,
        mapchete_file,
        job_id=None,
        mhub_worker=None,
        mhub_queue=None,
        **kwargs
    ):
        """Start a job and return job state."""
        job_id = job_id or uuid.uuid4().hex
        data = cleanup_datetime(
            dict(
                mapchete_config=yaml.safe_load(open(mapchete_file, "r").read()),
                **kwargs
            )
        )
        mhub_worker = mhub_worker or data["mapchete_config"].get("mhub_worker")
        if not mhub_worker:
            raise ValueError("specify mhub_worker")
        mhub_queue = mhub_queue or data["mapchete_config"].get("mhub_queue")
        if not mhub_queue:
            raise ValueError("specify mhub_queue")
        data["mapchete_config"].update(mhub_worker=mhub_worker, mhub_queue=mhub_queue)

        logger.debug("send job %s to API", job_id)
        res = self.post("jobs/%s" % job_id, json=json.dumps(data), timeout=timeout)
        if res.status_code != 202:
            raise JobRejected(res.json)
        logger.debug("job %s sent", job_id)
        return Job(
            status_code=res.status_code,
            state=res.json["properties"]["state"],
            job_id=job_id,
            json=res.json
        )

    def job(self, job_id, geojson=False):
        """Return job metadata."""
        res = self.get("jobs/%s" % job_id, timeout=timeout)
        if res.status_code == 404:
            raise JobNotFound("job %s does not exist" % job_id)
        else:
            return (
                format_as_geojson(res.json)
                if geojson
                else Job(
                    status_code=res.status_code,
                    state=res.json["properties"]["state"],
                    job_id=job_id,
                    json=res.json
                )
            )

    def job_state(self, job_id):
        """Return job state."""
        return self.job(job_id).state

    def jobs(self, geojson=False, bounds=None, **kwargs):
        """Return jobs metadata."""
        res = self.get(
            "jobs/",
            timeout=timeout,
            params=dict(
                kwargs,
                bounds=",".join(map(str, bounds)) if bounds else None
            )
        )
        return (
            format_as_geojson(res.json)
            if geojson
            else {
                job["properties"]["job_id"]: Job(
                    status_code=200,
                    state=job["properties"]["state"],
                    job_id=job["properties"]["job_id"],
                    json=job
                )
                for job in res.json
            }
        )

    def jobs_states(self, output_path=None):
        """Return jobs states."""
        return {
            job["properties"]["job_id"]: job["properties"]["state"]
            for job in self.get(
                "jobs/",
                timeout=timeout,
                params=dict(output_path=output_path)
            ).json
        }

    def job_progress(self, job_id, interval=1, timeout=60):
        """Yield job progress information."""
        last = -1
        updated = time.time()
        while True:
            job = self.job(job_id)
            logger.debug(job.state)

            if job.state in job_states["todo"]:
                pass

            if job.state in job_states["doing"]:
                if job.state in ["RECEIVED", "STARTED"]:
                    pass
                if job.state in ["PROGRESS"]:
                    logger.debug(job.json)
                    x = job.json["properties"]["progress_data"].get("current", None)
                    current = -1 if x is None else x
                    if current > last:
                        last = job.json["properties"]["progress_data"]["current"]
                        updated = time.time()
                        yield job.json["properties"]

            if job.state in job_states["done"]:
                if job.state == "SUCCESS":
                    yield job.json["properties"]
                    return
                if job.state == "FAILURE":
                    raise JobFailed(job.json["properties"]["traceback"])

            if time.time() - updated > timeout:
                raise TimeoutError("no update since %s seconds" % timeout)
            time.sleep(interval)

    def _get_kwargs(self, kwargs):
        """
        Clean up kwargs.

        For test client:
            - remove timeout kwarg
            - rename params kwarg to query_string
        """
        if self._test_client:
            kwargs.pop("timeout", None)
            kwargs.update(query_string=kwargs.pop("params", {}))
        return kwargs


def format_as_geojson(inp, indent=4):
    """Return a pretty GeoJSON."""
    space = " " * indent
    out_gj = (
        '{\n'
        '%s"type": "FeatureCollection",\n'
        '%s"features": [\n'
    ) % (space, space)
    features = (i for i in ([inp] if isinstance(inp, dict) else inp))
    try:
        feature = next(features)
        level = 2
        while True:
            feature_gj = (space * level).join(
                json.dumps(
                    json.loads('%s' % geojson.Feature(**feature)),
                    indent=indent,
                    sort_keys=True
                ).splitlines(True)
            )
            try:
                feature = next(features)
                out_gj += "%s%s,\n" % (space * level, feature_gj)
            except StopIteration:
                out_gj += "%s%s\n" % (space * level, feature_gj)
                break
    except StopIteration:
        pass
    out_gj += '%s]\n}' % space
    return out_gj
