from collections import OrderedDict
import fiona
import json
from json.decoder import JSONDecodeError
import logging
import os
from shapely.geometry import Polygon, mapping
from shapely import wkt
import spatialite
import sys

from mapchete_hub.config import main_options, flask_options

logger = logging.getLogger(__name__)


def status_monitor(celery_app):
    logger.debug("start status monitor")
    state = celery_app.events.State()
    logger.debug("state: %s", state)

    with StatusHandler(
        os.path.join(
           main_options.get("config_dir"), main_options.get("status_gpkg")
        ),
        mode='w',
        profile=main_options["status_gpkg_profile"]
    ) as status_handler:

        def announce_task_state(event):
            logger.debug("got event: %s", event)
            state.event(event)
            task = state.tasks.get(event['uuid'])
            try:
                logger.debug('task status: %s: %s', task.uuid, event["state"])
            except:
                logger.error('malformed task status: %s', event)
            status_handler.update(task.uuid, event)

        def announce_failed_task_state(event):
            # task name is sent only with -received event, and state
            # will keep track of this for us.
            state.event(event)
            task = state.tasks.get(event['uuid'])
            logger.error('task failed: %s: %s', task.uuid, event)
            status_handler.update(task.uuid, event)

        while True:
            try:
                with celery_app.connection(flask_options["broker_url"]) as connection:
                    logger.debug("connection: %s", connection)
                    recv = celery_app.events.Receiver(
                        connection,
                        handlers={
                            'task-sent': announce_task_state,
                            'task-received': announce_task_state,
                            'task-started': announce_task_state,
                            'task-succeeded': announce_task_state,
                            'task-failed': announce_failed_task_state,
                            'task-rejected': announce_task_state,
                            'task-revoked': announce_task_state,
                            'task-retried': announce_task_state,
                            'task-progress': announce_task_state,
                        }
                    )
                    logger.debug("ready to capture events")
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except ConnectionResetError as e:
                logger.error(e)
            except (KeyboardInterrupt, SystemExit):
                sys.exit()


class StatusHandler():

    def __init__(self, filename, mode='r', profile=None):
        logger.debug("mode: %s", mode)
        self.mode = mode
        if os.path.isfile(filename):
            logger.debug("GPKG file exists: %s", filename)
        else:
            logger.debug("create new status GPKG %s, %s", filename, profile)
            src = fiona.open(filename, 'w', **profile)
            src.close()

        if self.mode == 'w':
            logger.debug("open status handler in 'w' mode: %s", filename)
            self.connection = spatialite.connect(filename)

        elif self.mode == 'r':
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

    def all(self):
        logger.debug("get status of all jobs")
        c = self.connection.cursor()
        res = c.execute('SELECT * FROM %s;' % self.tablename)
        return [self._decode_row(row) for row in res]

    def job(self, job_id):
        logger.debug("get job %s status", job_id)
        c = self.connection.cursor()
        row = c.execute(
            'SELECT * FROM %s WHERE job_id=?;' % self.tablename, [job_id]
        ).fetchone()
        if row is None:
            logger.debug("no job found named %s", job_id)
            return {}
        else:
            return self._decode_row(row)

    def update(self, job_id, metadata={}):
        if self.mode == 'r':
            raise AttributeError('update not allowed in read mode')
        # logger.debug("update job %s status with: %s", job_id, metadata)
        c = self.connection.cursor()
        # update incoming metadata
        entry = dict(self._filtered_by_schema(metadata), job_id=metadata['uuid'])
        if 'kwargs' in metadata:
            # logger.debug("found kwargs: %s", metadata['kwargs'])
            kwargs = json.loads(metadata['kwargs'].replace("'", '"'))
            entry.update(
                geom=wkt.loads(kwargs['process_area']).wkt,
                config=kwargs['config']
            )
        encoded_values = self._encode_values(entry)

        # check if entry exists and insert new or update existing
        # TODO: there must be a better way!
        if c.execute(
            'SELECT * FROM %s WHERE job_id=?;' % self.tablename, [job_id]
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
        self.connection.close()

    def _filtered_by_schema(self, metadata):
        return {
            k: v
            for k, v in metadata.items()
            if k in self.fields
        }

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
                if k == 'geom':
                    if v is None:
                        yield (k, v)
                        # raise TypeError("geometry invalid")
                    else:
                        yield (k, mapping(wkt.loads(v)))
                elif isinstance(v, str):
                    try:
                        yield (k, json.loads(v))
                    except JSONDecodeError:
                        yield (k, v)
                else:
                    yield (k, v)
        decoded = dict(_decode())
        return dict(
            geometry=decoded['geom'],
            properties={k: v for k, v in decoded.items() if k != 'geom'}
        )

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.close()
