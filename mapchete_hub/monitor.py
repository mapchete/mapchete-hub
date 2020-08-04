"""Monitor module required to keep track on job statuses."""


import logging
import sys

from mapchete_hub.config import get_flask_config
from mapchete_hub.db import BackendDB

logger = logging.getLogger(__name__)


# monitor cannot be tested using coverage
def status_monitor(celery_app):  # pragma: no cover
    """Run status monitor listening to task events."""
    logger.debug("start status monitor")
    state = celery_app.events.State()
    logger.debug("state: %s", state)
    config = get_flask_config()

    def announce_task_state(event):
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        logger.debug("got event: %s", event)
        state.event(event)
        task = state.tasks.get(event["uuid"])

        if task.uuid:
            logger.debug("task {} status: {}".format(task.uuid, event.get("state")))
            # Special case to handle workaround for celery error.
            # https://github.com/celery/celery/issues/2727#issuecomment-571990240
            # see https://gitlab.eox.at/maps/mapchete_hub/-/issues/108
            if "SoftTimeLimitExceeded()" in event.get("traceback", ""):
                event.update(
                    exception=None,
                    traceback=None,
                    type="task-revoked",
                    state="TERMINATED"
                )
            status_handler.update(job_id=task.uuid, metadata=event)

    with BackendDB(src=config.MONGO_URI) as status_handler:
        while True:
            try:
                logger.debug("try to establish connection for events...")
                logger.debug('broker: {}'.format(celery_app.pool.connection.as_uri()))
                logger.debug('backend: {}'.format(celery_app.backend.as_uri()))
                with celery_app.connection() as connection:
                    logger.debug("connection: %s", connection)
                    celery_app.events.Receiver(connection)
                    recv = celery_app.events.Receiver(
                        connection,
                        handlers={
                            "task-sent": announce_task_state,
                            "task-received": announce_task_state,
                            "task-started": announce_task_state,
                            "task-succeeded": announce_task_state,
                            "task-failed": announce_task_state,
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
