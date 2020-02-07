"""Monitor module required to keep track on job statuses."""


from collections import OrderedDict
import fiona
import json
from json.decoder import JSONDecodeError
import logging
import os
from shapely.geometry import box, Polygon, mapping
from shapely import wkt
import spatialite
import sys

from mapchete_hub.api import job_states
from mapchete_hub.config import main_options, flask_options

logger = logging.getLogger(__name__)


def status_monitor(celery_app):
    """Run status monitor listening to task events."""
    logger.debug("start status monitor")
    state = celery_app.events.State()
    logger.debug("state: %s", state)

    with StatusHandler(
        os.path.join(main_options.get("config_dir"), main_options.get("status_gpkg")),
        mode="w",
        profile=main_options["status_gpkg_profile"]
    ) as status_handler:

        def announce_task_state(event):
            logger.debug("got event: %s", event)
            state.event(event)
            task = state.tasks.get(event["uuid"])
            try:
                logger.debug("task status: %s: %s", task.uuid, event["state"])
            except:
                logger.error("malformed task status: %s", event)
            status_handler.update(task.uuid, event)

        def announce_failed_task_state(event):
            # task name is sent only with -received event, and state
            # will keep track of this for us.
            state.event(event)
            task = state.tasks.get(event["uuid"])
            logger.error("task failed: %s: %s", task.uuid, event)
            status_handler.update(task.uuid, event)

        while True:
            try:
                logger.debug("try to establish connection for events...")
                with celery_app.connection(flask_options["broker_url"]) as connection:
                    logger.debug("connection: %s", connection)
                    recv = celery_app.events.Receiver(
                        connection,
                        handlers={
                            "task-sent": announce_task_state,
                            "task-received": announce_task_state,
                            "task-started": announce_task_state,
                            "task-succeeded": announce_task_state,
                            "task-failed": announce_failed_task_state,
                            "task-rejected": announce_task_state,
                            "task-revoked": announce_task_state,
                            "task-retried": announce_task_state,
                            "task-progress": announce_task_state,
                        }
                    )
                    logger.debug("ready to capture events")
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except ConnectionResetError as e:
                logger.error(e)
            except (KeyboardInterrupt, SystemExit):
                sys.exit()


class StatusHandler():
    """Class to communicate with backend database."""

    def __init__(self, filename, mode="r", profile=None):
        """Initialize."""
        logger.debug("mode: %s", mode)
        self.mode = mode
        if os.path.isfile(filename):
            logger.debug("GPKG file exists: %s", filename)
        else:
            logger.debug("create new status GPKG %s, %s", filename, profile)
            src = fiona.open(filename, "w", **profile)
            src.close()

        if self.mode == "w":
            logger.debug("open status handler in 'w' mode: %s", filename)
            self.connection = spatialite.connect(filename)

        elif self.mode == "r":
            if os.path.isfile(filename):
                logger.debug("open status handler in 'r' mode: %s", filename)
                self.connection = spatialite.connect(filename, check_same_thread=False)
            else:
                raise IOError("no GPKG file found: %s", filename)

        else:
            raise ValueError("unknown mode '%s'", mode)

        logger.debug("connect to GPKG %s", filename)
        self.tablename = os.path.splitext(os.path.basename(filename))[0]

        def _get_f_type(f_type):
            if f_type == "REAL":
                return float
            elif f_type == "INTEGER":
                return int
            elif f_type.startswith("TEXT"):
                return str
            elif f_type == "POLYGON":
                return Polygon
            else:
                raise TypeError("unknown field type")

        c = self.connection.cursor()
        self.fields = OrderedDict(
            (column[1], _get_f_type(column[2]))
            for column in c.execute("PRAGMA table_info(%s);" % self.tablename)
        )
        logger.debug(self.fields)

    def all(
        self,
        output_path=None,
        state=None,
        command=None,
        queue=None,
        bounds=None,
        from_date=None,
        to_date=None
    ):
        """Return all jobs."""
        c = self.connection.cursor()

        # build SQL query
        query = "SELECT * FROM %s" % self.tablename

        # add filter by job states
        if state:
            # for todo, doing and done state groups
            if state in job_states:
                query += " WHERE state IN (%s)" % (
                    ", ".join(["'%s'" % i.upper() for i in job_states[state]])
                )
            # for all Celery task states
            else:
                query += " WHERE state='%s'" % state.upper()

        # add spatial filter
        if bounds:
            connect = " AND" if "WHERE" in query else " WHERE"
            query += "%s ST_Intersects(GeomFromText(geom), GeomFromText('%s', 4326))" % (
                connect, box(*bounds).wkt
            )

        # add temporal filter
        if from_date:
            connect = " AND" if "WHERE" in query else " WHERE"
            query += "%s timestamp>=%s" % (connect, from_date.timestamp())
        if to_date:
            connect = " AND" if "WHERE" in query else " WHERE"
            query += "%s timestamp<=%s" % (connect, to_date.timestamp())

        # add command filter
        if command:
            connect = " AND" if "WHERE" in query else " WHERE"
            query += "%s command='%s'" % (connect, command.lower())

        # add queue filter
        if queue:
            connect = " AND" if "WHERE" in query else " WHERE"
            query += "%s queue='%s'" % (connect, queue.lower())

        query += ";"
        logger.debug(query)

        def _mapchete_config_filter(row):
            """Filter out by mapchete config properties."""
            properties = row.get("properties") or dict()
            config = properties.get("config") or dict()
            mapchete_config = config.get("mapchete_config") or dict()
            if (
                output_path and
                mapchete_config.get("output", {}).get("path") != output_path
            ):
                return False
            else:
                return True

        # return result
        return [
            i for i in map(self._decode_row, c.execute(query).fetchall())
            if _mapchete_config_filter(i)
        ]

    def job(self, job_id):
        """Return job."""
        logger.debug("get job %s status", job_id)
        c = self.connection.cursor()
        row = c.execute(
            "SELECT * FROM %s WHERE job_id=?;" % self.tablename, [job_id]
        ).fetchone()
        if row is None:
            logger.debug("no job found named %s", job_id)
            return {}
        else:
            return self._decode_row(row)

    def update(self, job_id, metadata={}):
        """Update job."""
        if self.mode == "r":
            raise AttributeError("update not allowed in read mode")

        # get cursor
        c = self.connection.cursor()

        # remember timestamp when process started
        if metadata.get("type") in ["task-started", "task-received"]:
            metadata.update(started=metadata.get("timestamp"))

        logger.debug("got metadata: %s", metadata)

        # update incoming metadata
        entry = dict(self._filtered_by_schema(metadata))

        logger.debug("filtered by schema: %s", entry)

        if "kwargs" in metadata:
            kwargs = json.loads(metadata["kwargs"].replace("'", '"'))
            entry.update(
                geom=wkt.loads(kwargs["process_area"]).wkt,
                command=kwargs.get("command"),
                config=dict(
                    mapchete_config=kwargs["mapchete_config"],
                    mode=kwargs.get("mode"),
                    bounds=kwargs.get("bounds"),
                    tile=kwargs.get("tile"),
                    point=kwargs.get("point"),
                    wkt_geometry=kwargs.get("wkt_geometry")
                ),
                job_id=metadata["uuid"],
                job_name=kwargs.get("job_name"),
                parent_job_id=kwargs.get("parent_job_id"),
                child_job_id=kwargs.get("child_job_id"),
            )

        encoded_values = self._encode_values(entry)

        logger.debug("encoded keys: %s", entry.keys())
        logger.debug("encoded entry: %s", encoded_values)

        # check if entry exists and insert new or update existing
        # TODO: there must be a better way!
        if c.execute(
            "SELECT * FROM %s WHERE job_id=?;" % self.tablename, [job_id]
        ).fetchone() is None:
            # insert new entry
            insert = "INSERT INTO %s (%s) VALUES (%s);" % (
                self.tablename,
                ", ".join(entry.keys()),
                ", ".join(["?" for _ in entry])
            )
            c.execute(insert, encoded_values)
        else:
            # update existing entry
            update = "UPDATE %s SET %s WHERE job_id=?;" % (
                self.tablename,
                ", ".join([
                    "%s=%s" % (column, value)
                    for column, value in zip(entry.keys(), ["?" for _ in entry])
                ])
            )
            encoded_values.append(job_id)
            c.execute(update, encoded_values)

        # commit changes
        self.connection.commit()

    def close(self):
        """Close database connection."""
        self.connection.close()

    def _filtered_by_schema(self, metadata):
        return {k: v for k, v in metadata.items() if k in self.fields}

    def _encode_values(self, entry):

        def _encode():
            for v in entry.values():
                if isinstance(v, dict):
                    yield json.dumps(v)
                else:
                    yield v

        return list(_encode())

    def _decode_row(self, row):

        def _decode():
            for k, v in zip(self.fields, row):
                if k == "geom":
                    if v is None:
                        yield (k, v)
                    else:
                        yield (k, wkt.loads(v))
                elif isinstance(v, str):
                    try:
                        yield (k, json.loads(v))
                    except JSONDecodeError:
                        yield (k, v)
                else:
                    yield (k, v)

        decoded = dict(_decode())
        return dict(
            bounds=decoded["geom"].bounds,
            geometry=mapping(decoded["geom"]),
            id=decoded["job_id"],
            properties={k: v for k, v in decoded.items() if k != "geom"}
        )

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, *args):
        """Exit context."""
        self.close()
