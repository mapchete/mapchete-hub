"""
Convenience tools to communicate with mapchete Hub REST API.

This module wraps around the requests module for real-life usage and Flask's test_client()
in order to be able to test mhub CLI.
"""

import base64
from collections import namedtuple, OrderedDict
import geojson
import json
import logging
from mapchete.validate import validate_zooms
import os
import py_compile
import requests
from requests.exceptions import ConnectionError
import time
import uuid
import oyaml as yaml

from mapchete_hub.exceptions import JobFailed, JobNotFound, JobRejected
from mapchete_hub.utils import cleanup_datetime


logger = logging.getLogger(__name__)


default_timeout = 5
job_states = {
    "todo": ["PENDING"],
    "doing": ["PROGRESS", "RECEIVED", "STARTED"],
    "done": ["SUCCESS", "FAILURE", "TERMINATED", "REVOKED"]
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

    def __repr__(self):  # pragma: no cover
        """Print Job."""
        return "Job(status_code={}, state={}, job_id={}, json={}".format(
            self.status_code, self.state, self.job_id, self.json
        )


Response = namedtuple("Response", "status_code json")


class API():
    """API class which abstracts REST interface."""

    def __init__(self, host="localhost:5000", timeout=None, _test_client=None, **kwargs):
        """Initialize."""
        host = host if host.startswith("http") else "http://{}".format(host)
        host = host if host.endswith("/") else "{}/".format(host)
        self.host = host if host.endswith("/") else "{}/".format(host)
        self.timeout = timeout or default_timeout
        self._test_client = _test_client
        self._api = _test_client if _test_client else requests
        self._baseurl = "" if _test_client else host

    def get(self, url, **kwargs):
        """Make a GET request to _test_client or host."""
        try:
            get_url = self._baseurl + url
            get_kwargs = self._get_kwargs(kwargs)
            logger.debug("GET: {}, {}".format(get_url, get_kwargs))
            res = self._api.get(get_url, **get_kwargs)
            logger.debug(f"response: {res}")
            return Response(
                status_code=res.status_code,
                json=res.json if self._test_client else json.loads(res.text)
            )
        except ConnectionError:  # pragma: no cover
            raise ConnectionError("no mhub server found at {}".format(self.host))

    def post(self, url, **kwargs):
        """Make a POST request to _test_client or host."""
        try:
            post_url = self._baseurl + url
            post_kwargs = self._get_kwargs(kwargs)
            logger.debug("POST: {}, {}".format(post_url, post_kwargs))
            res = self._api.post(post_url, **post_kwargs)
            return Response(
                status_code=res.status_code,
                json=res.json if self._test_client else json.loads(res.text)
            )
        except ConnectionError:  # pragma: no cover
            raise ConnectionError("no mhub server found at {}".format(self.host))

    def put(self, url, **kwargs):
        """Make a PUT request to _test_client or host."""
        try:
            put_url = self._baseurl + url
            put_kwargs = self._get_kwargs(kwargs)
            logger.debug("PUT: {}, {}".format(put_url, put_kwargs))
            res = self._api.put(put_url, **put_kwargs)
            return Response(
                status_code=res.status_code,
                json=res.json if self._test_client else json.loads(res.text)
            )
        except ConnectionError:  # pragma: no cover
            raise ConnectionError("no mhub server found at {}".format(self.host))

    def start_job(
        self,
        mapchete_config=None,
        command=None,
        job_id=None,
        queue=None,
        **kwargs
    ):
        """
        Start a job and return job state.

        Sends HTTP POST to /jobs/<job_id> and appends mapchete configuration as well
        as processing parameters as JSON.

        Parameters
        ----------
        mapchete_config : path or dict
            Either path to .mapchete file or dictionary with mapchete parameters.
        command : str
            Either "execute" or "index".
        job_id : str (optional)
            Unique job ID.
        bounds : list
            Left, bottom, right, top coordinate of process area.
        point : list
            X and y coordinate of point over process tile.
        tile : list
            Zoom, row and column of process tile.
        geometry : str
            GeoJSON representaion of process area.
        zoom : list or int
            Minimum and maximum zoom level or single zoom level.

        Returns
        -------
        mapchete_hub.api.Job
        """
        job_id = job_id or uuid.uuid4().hex
        job = dict(
            command=command,
            config=load_mapchete_config(mapchete_config),
            params=kwargs
        )

        # make sure correct command is provided
        if command not in ["execute", "index"]:
            raise ValueError("invalid command given: {}".format(command))

        # add queue if necessary
        job["params"]["queue"] = (
            queue or job["params"].get("queue", "{}_queue".format(command))
        )

        logger.debug("send job {} to API".format(job_id))
        res = self.post(
            "jobs/{}".format(job_id),
            json=json.dumps(job),
            timeout=self.timeout
        )

        if res.status_code != 202:
            raise JobRejected(res.json)
        else:
            logger.debug("job {} sent".format(job_id))
            return Job(
                status_code=res.status_code,
                state="PENDING",
                job_id=job_id,
                json=res.json
            )

    def start_batch(
        self,
        batch=None,
        job_id=None,
        **kwargs
    ):
        """
        Start a batch of jobs and return job state of first job.

        Sends HTTP POST to /jobs/<job_id> and appends mapchete configuration as well
        as processing parameters as JSON.

        Parameters
        ----------
        batch : path or dict
            Either path to .mhub file or dictionary with batch parameters.
        job_id : str (optional)
            Unique job ID of first job.
        bounds : list
            Left, bottom, right, top coordinate of process area.
        point : list
            X and y coordinate of point over process tile.
        tile : list
            Zoom, row and column of process tile.
        geometry : str
            GeoJSON representaion of process area.

        Returns
        -------
        mapchete_hub.api.Job
        """
        job_id = job_id or uuid.uuid4().hex
        jobs = list(load_batch_config(batch, **kwargs)["jobs"].values())

        logger.debug("send batch job {} to API".format(job_id))
        res = self.post(
            "jobs/{}".format(job_id),
            json=json.dumps(jobs),
            timeout=self.timeout
        )

        if res.status_code != 202:
            raise JobRejected(res.json)
        else:
            logger.debug("job {} sent".format(job_id))
            return Job(
                status_code=res.status_code,
                state="PENDING",
                job_id=job_id,
                json=res.json
            )

    def cancel_job(self, job_id):
        """Cancel existing job."""
        res = self.put(
            "jobs/{}".format(job_id),
            json={"command": "cancel"},
            timeout=self.timeout
        )
        if res.status_code == 404:
            raise JobNotFound("job {} does not exist".format(job_id))
        return Job(
            status_code=res.status_code,
            state=self.job_state(job_id),
            job_id=job_id,
            json=res.json
        )

    def job(self, job_id, geojson=False):
        """Return job metadata."""
        res = self.get("jobs/{}".format(job_id), timeout=self.timeout)
        if res.status_code == 404:
            raise JobNotFound("job {} does not exist".format(job_id))
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
            "jobs",
            timeout=self.timeout,
            params=dict(
                kwargs,
                bounds=",".join(map(str, bounds)) if bounds else None
            )
        )
        if res.status_code != 200:
            raise Exception(res.json)
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
                "jobs",
                timeout=self.timeout,
                params=dict(output_path=output_path)
            ).json
        }

    def job_progress(self, job_id, interval=1, timeout=None):
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

            if timeout is not None and time.time() - updated > timeout:
                raise TimeoutError("no update since {} seconds".format(timeout))

            time.sleep(interval)

    def _get_kwargs(self, kwargs):
        """
        Clean up kwargs.

        For test client:
            - remove timeout kwarg
            - rename params kwarg to query_string
        """
        if self._test_client:  # pragma: no cover
            kwargs.pop("timeout", None)
            kwargs.update(query_string=kwargs.pop("params", {}))
        return kwargs


def format_as_geojson(inp, indent=4):
    """Return a pretty GeoJSON."""
    space = " " * indent
    out_gj = (
        '{{\n'
        '{}"type": "FeatureCollection",\n'
        '{}"features": [\n'
    ).format(space, space)
    features = (i for i in ([inp] if isinstance(inp, dict) else inp))
    try:
        feature = next(features)
        level = 2
        while True:
            feature_gj = (space * level).join(
                json.dumps(
                    json.loads('{}'.format(geojson.Feature(**feature))),
                    indent=indent,
                    sort_keys=True
                ).splitlines(True)
            )
            try:
                feature = next(features)
                out_gj += "{}{},\n".format(space * level, feature_gj)
            except StopIteration:
                out_gj += "{}{}\n".format(space * level, feature_gj)
                break
    except StopIteration:  # pragma: no cover
        pass
    out_gj += '{}]\n}}'.format(space)
    return out_gj


def load_mapchete_config(mapchete_config):
    """
    Return preprocessed mapchete config provided as dict or file.

    This function reads a mapchete config into an OrderedDict which keeps the item order
    stated in the .mapchete file.
    If the configuration is passed on via a .mapchete file and if a process file path
    instead of a process module path was given, it will also check the syntax and replace
    the process item with the python code as string.

    Parameters
    ----------
    mapchete_config : str or dict
        A valid mapchete configuration either as path or dictionary.

    Returns
    -------
    OrderedDict
        Preprocessed mapchete configuration.
    """
    if isinstance(mapchete_config, OrderedDict):
        return cleanup_datetime(mapchete_config)

    elif isinstance(mapchete_config, str):
        conf = cleanup_datetime(yaml.safe_load(open(mapchete_config, "r").read()))

        if not conf.get("process"):  # pragma: no cover
            raise KeyError("no or empty process in configuration")

        # local python file
        if conf.get("process").endswith(".py"):
            custom_process_path = os.path.join(
                os.path.dirname(mapchete_config),
                conf.get("process")
            )
            # check syntax
            py_compile.compile(custom_process_path, doraise=True)
            # assert file is not empty
            process_code = open(custom_process_path).read()
            if not process_code:  # pragma: no cover
                raise ValueError("process file is empty")
            conf.update(
                process=base64.standard_b64encode(
                    process_code.encode("utf-8")
                ).decode("utf-8")
            )

        return conf

    else:
        raise TypeError(
            "mapchete config must either be a path to an existing file or an OrderedDict"
        )


def load_batch_config(batch_config, **kwargs):
    """
    Return preprocessed batch config.

    This function verifies a batch configuration and loads and preprocesses all given
    jobs mapchete configurations (see ``load_mapchete_config()`` for details).

    Parameters
    ----------
    batch_config : str
        Path to .mhub batch configuration file.

    Returns
    -------
    OrderedDict
        Preprocessed mhub batch configuration.
    """
    loaded_mapchete_configs = {}

    def _get_mapchete_config(mapchete_config):
        if mapchete_config not in loaded_mapchete_configs:
            loaded_mapchete_configs[mapchete_config] = load_mapchete_config(
                os.path.join(
                    os.path.dirname(batch_config),
                    mapchete_config
                )
            )
        return loaded_mapchete_configs[mapchete_config]

    def _parse_and_verify(batch_config):
        if isinstance(batch_config, str) and batch_config.endswith(".mhub"):
            raw = yaml.safe_load(open(batch_config, "r").read())
            if raw is None or not raw.get("jobs", {}):
                raise ValueError("no jobs given")
            parent_zoom = None
            for job_name, params in raw.get("jobs", {}).items():
                if "command" not in params:
                    raise ValueError("no command provided for job {}".format(job_name))
                if "mapchete" in params:
                    mapchete = _get_mapchete_config(params["mapchete"])
                elif "job" in params:
                    if params["job"] not in raw["jobs"]:
                        raise ValueError(
                            "job {} points to invalid other job {}".format(
                                job_name, params["job"]
                            )
                        )
                    else:
                        mapchete = _get_mapchete_config(
                            raw["jobs"][params["job"]]["mapchete"]
                        )
                else:
                    raise ValueError(
                        "job {} must either provide a mapchete file or point other "
                        "job".format(job_name)
                    )
                if "zoom" in params:
                    zoom = validate_zooms(params["zoom"], expand=False)
                else:
                    zoom = parent_zoom
                yield (
                    job_name,
                    dict(
                        command=params["command"],
                        config=mapchete,
                        params=dict(
                            job_name=job_name,
                            mode=params.get("mode", "continue"),
                            queue=params.get("queue", None),
                            zoom=zoom,
                            bounds=kwargs.get("bounds"),
                            point=kwargs.get("point"),
                            tile=kwargs.get("tile"),
                            geometry=kwargs.get("geometry"),
                            announce_on_slack=params.get("announce_on_slack", False)
                        )
                    )
                )
        else:
            raise TypeError("batch_config must be a .mhub file")

    return OrderedDict(jobs=OrderedDict(list(_parse_and_verify(batch_config))))
