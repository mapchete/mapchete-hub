import logging
import pickledb

logger = logging.getLogger(__name__)


def status_monitor(celery_app):
    state_store = get_main_options().get("state_store_file")
    states = pickledb.load(state_store)
    logger.debug("status monitor")
    state = celery_app.events.State()
    logger.debug("state: %s", state)

    def announce_failed_tasks(event):
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        state.event(event)
        task = state.tasks.get(event['uuid'])
        logger.error('TASK FAILED: %s: %s', task.uuid, event)

    def announce_progress_tasks(event):
        state.event(event)
        task = state.tasks.get(event['uuid'])
        logger.debug('TASK IN PROGRESS: %s: %s', task.uuid, event)

    with celery_app.connection() as connection:
        logger.debug("connection: %s", connection)
        recv = celery_app.events.Receiver(
            connection,
            handlers={
                'task-failed': announce_failed_tasks,
                'task-progress': announce_progress_tasks,
            }
        )
        logger.debug("ready to capture events")
        recv.capture(limit=None, timeout=None, wakeup=True)
