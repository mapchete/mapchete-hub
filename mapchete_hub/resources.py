from amqp.exceptions import ChannelError, NotFound
from collections import defaultdict
import celery
import fiona
from flask import abort, request
from flask_restful import Resource
import logging
import mapchete
import mapchete_satellite
import orgonite
import pkg_resources
import rasterio
from webargs import fields
from webargs.flaskparser import use_kwargs

from mapchete_hub import __version__
from mapchete_hub.api import job_states
from mapchete_hub.celery_app import celery_app
from mapchete_hub.commands import command_func
from mapchete_hub.config import get_mhub_config
from mapchete_hub.db import BackendDB
from mapchete_hub.utils import parse_jobs_for_backend


logger = logging.getLogger(__name__)


class Capabilities(Resource):
    """Resouce for capabilities.json."""

    def __init__(self):
        """Initialize resource."""
        processes = list(pkg_resources.iter_entry_points("mapchete.processes"))
        self._capabilities = {}
        self._capabilities["version"] = __version__
        self._capabilities["packages"] = {
            "fiona": fiona.__version__,
            "gdal": rasterio.__gdal_version__,
            "mapchete": mapchete.__version__,
            "mapchete_satellite": mapchete_satellite.__version__,
            "orgonite": orgonite.__version__,
            "rasterio": rasterio.__version__,
        }
        try:
            import eox_preprocessing
            self._capabilities["packages"].update(
                eox_preprocessing=eox_preprocessing.__version__
            )
        except ImportError:  # pragma: no cover
            self._capabilities["packages"].update(
                eox_preprocessing="not installed"
            )

        self._capabilities["processes"] = {}
        for v in processes:
            process_module = v.load()
            self._capabilities["processes"][process_module.__name__] = {
                "name": process_module.__name__,
                "docstring": process_module.execute.__doc__
            }

    def get(self):
        """Return /capabilities.json."""
        return self._capabilities


class QueuesOverview(Resource):
    """Resource for /queues."""

    def get(self):
        """Return queues."""
        try:
            insp = celery_app.control.inspect().active_queues() or {}
            queue_workers = defaultdict(list)
            for worker, queues in insp.items():  # pragma: no cover
                for queue in queues:
                    queue_workers[queue["name"]].append(worker)
            out_queues = {}
            with celery_app.connection_or_acquire() as conn:
                for queue_name, workers in queue_workers.items():  # pragma: no cover
                    queue_info = conn.default_channel.queue_declare(
                        queue=queue_name,
                        passive=True
                    )
                    out_queues[queue_name] = dict(
                        worker_count=queue_info.consumer_count,
                        job_count=queue_info.message_count
                    )
            return out_queues
        except Exception as e:  # pragma: no cover
            logger.error(e)
            return abort(500, str(e))


class Queues(Resource):
    """Resource for /queues/<queue_name>."""

    def get(self, queue_name):
        """
        Return queue metadata.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        response
        """
        def _extract_jobs(job_list):  # pragma: no cover
            return list(set((y["id"] for x in job_list for y in x)))

        try:
            inspect = celery_app.control.inspect()
            active_queues = inspect.active_queues() or {}
            queue_workers = defaultdict(list)
            for worker, queues in active_queues.items():  # pragma: no cover
                for queue in queues:
                    queue_workers[queue["name"]].append(worker)
            if queue_name not in queue_workers:
                raise NotFound("queue {} not found".format(queue_name))
            with celery_app.connection_or_acquire() as conn:  # pragma: no cover
                queue_info = conn.default_channel.queue_declare(
                    queue=queue_name,
                    passive=True
                )
                return dict(
                    workers=queue_workers[queue_name],
                    worker_count=queue_info.consumer_count,
                    job_count=queue_info.message_count,
                    jobs=dict(
                        active=_extract_jobs(inspect.active().values()),
                        reserved=_extract_jobs(inspect.reserved().values()),
                        scheduled=_extract_jobs(inspect.scheduled().values()),
                    )
                )
        except (ChannelError, NotFound):
            abort(404, "no queue found with name {}".format(queue_name))
        except Exception as e:  # pragma: no cover
            logger.error(e)
            return abort(500, str(e))


class JobsOverview(Resource):
    """Resource for /jobs."""

    get_kwargs = {
        "output_path": fields.Str(required=False),
        "state": fields.Str(required=False),
        "command": fields.Str(required=False),
        "queue": fields.Str(required=False),
        "bounds": fields.DelimitedList(fields.Float(), required=False),
        "from_date": fields.DateTime(required=False),
        "to_date": fields.DateTime(required=False),
    }

    def __init__(self, app=None):
        """Make sure Flask app is available."""
        self._backend = BackendDB(src=app.mongodb.cx)

    @use_kwargs(get_kwargs, location="query")
    def get(self, **kwargs):
        """
        Return jobs as list of GeoJSON features.

        Parameters
        ----------
        output_path : str
            Filter by output path.
        state : str
            Filter by job state.
        command : str
            Filter by mapchete Hub command.
        queue : str
            Filter by queue.
        job_name : str
            Filter by job name.
        bounds : list or tuple
            Filter by spatial bounds.
        from_date : str
            Filter by earliest date.
        to_date : str
            Filter by latest date.

        Returns
        -------
        GeoJSON features : list of dict
        """
        try:
            return list(self._backend.jobs(**kwargs))
        except Exception as e:  # pragma: no cover
            logger.error(e)
            return abort(500, str(e))


class Jobs(Resource):
    """Resource for /jobs/<job_id>."""

    def __init__(self, app=None):
        """Make sure Flask app is available."""
        self.app = app
        self._backend = BackendDB(src=self.app.mongodb.cx)

    def get(self, job_id):
        """
        Return job metadata.

        Parameters
        ----------
        job_id : str
            Unique job ID.

        Returns
        -------
        GeoJSON feature
        """
        result = self._backend.job(job_id)
        if result is None:
            abort(404, "no job found with ID {}".format(job_id))
        else:
            return result

    def post(self, job_id):
        """
        Receive new job or batch job. A batch job is simply a list of jobs.

        Parameters
        ----------
        job_id : str
            Unique job ID.


        The configuration has to be appended as JSON to the request. If the configuration
        is a list, it will be handled as a batch job, if it is a dictionary it will be
        handled as a single job.

        A job configuration has to contain the following items:
        - command : str
            One of the mapchete_hub.commands items (execute or index)
        - params : dict
            A dictionary of optional command parameters.

            A job configuration has to contain one of the spatial subset items. In
            a batch job, only the first job needs to have a spatial subset item as all of
            the subsequent jobs inherit this:
            - bounds : list
                Left, bottom, right, top coordinate of process area.
            - point : list
                X and y coordinate of point over process tile.
            - tile : list
                Zoom, row and column of process tile.
            - geometry : GeoJSON
                Process area as GeoJSON.

            - queue : str
                Queue the job will be added to. If no queue is provided, it will be
                appended to the commmands default queue (i.e. execute_queue or
                index_queue.)
            - zoom : list or int
                Minimum and maximum zoom level or single zoom level.
            - job_name : str
                Only required for batch jobs, otherwise it is optional. Has to be unique
                within batch job.
            - job : str
                In batch jobs this references to a mapchete configuration of a prior job
                and can be used as an alternative to mapchete_config.
            - mode : str
                One of "continue" or "overwrite". (default: "continue")
            - announce_on_slack : bool
                Send message to Slack when job finished.

        - config : dict
            A valid mapchete configuration. In batch jobs either this or job has to be
            provided.


        Returns
        -------
        response
            202: If job was accepted.
            400: If JSON does not contain required or does contain malformed data.
            409: If job under this ID already exists.
            500: If an internal server error occured.
        """
        res = self._backend.job(job_id)
        # job exists
        if res:
            return abort(409, "job already exists: {}".format(job_id))
        try:
            jobs = list(
                parse_jobs_for_backend(
                    request.get_json(),
                    init_job_id=job_id,
                    dst_crs=get_mhub_config().BACKEND_CRS
                )
            )
        except Exception as e:  # pragma: no cover
            logger.error(e)
            return abort(400, str(e))

        try:
            # pass on to celery cluster
            logger.debug("job is new: {}".format(job_id))
            process_area = jobs[0]["kwargs"]["process_area"]

            logger.debug("process area: {}".format(process_area))
            logger.debug("job {} has {} follow-up jobs".format(job_id, len(jobs[1:])))

            # chain jobs sequentially
            logger.debug("send job {} to queue {}".format(job_id, jobs[0]["queue"]))
            celery.chain(
                command_func(j["command"]).signature(**j) for j in jobs
            ).apply_async()

            # add jobs to backend DB
            for j in jobs:
                logger.debug("add job {} to backend DB".format(j["kwargs"]["job_id"]))
                self._backend.new(
                    job_id=j["kwargs"]["job_id"],
                    metadata=j["kwargs"]
                )

            return dict(message="{} job(s) submitted".format(len(jobs))), 202

        except Exception as e:  # pragma: no cover
            logger.error(e)
            return abort(500, str(e))

    def put(self, job_id):
        """Cancel a job."""
        # cancel job
        data = request.get_json()
        if data.get("command") == "cancel":
            revoked = []
            jobs = self._get_jobs(job_id, append_next_jobs=True)
            for job in jobs:
                job_id = job["id"]
                self.app.logger.debug("got command to cancel job {}".format(job_id))
                if job["properties"]["state"] not in job_states["done"]:
                    # send signal to celery worker to terminate running job
                    celery_app.control.revoke(job_id, terminate=True)
                    revoked.append(job_id)
                    # update database
                    self._backend.update(job_id=job_id, metadata={"state": "REVOKED"})
                else:
                    logger.debug("job {} already in 'done' state".format(job_id))

            return dict(
                message=(
                    "revoke signal for job {} sent".format(job_id)
                    if len(revoked) == 1 else
                    "revoke signal for jobs {} sent".format(", ".join(revoked))
                )
            )

        else:
            return abort(
                400,
                "please explicitly add a '{\"command\": \"cancel\"}' JSON to the request"
            )

    def _get_jobs(self, job_id, append_next_jobs=True):
        job_meta = self.get(job_id)

        def _next_jobs(meta):
            next_job_id = meta["properties"].get("next_job_id")
            if next_job_id:
                next_meta = self.get(next_job_id)
                yield next_meta
                yield from _next_jobs(next_meta)
            else:
                return

        return [job_meta, *list(_next_jobs(job_meta))]
