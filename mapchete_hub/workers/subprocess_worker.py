from celery.utils.log import get_task_logger
import logging
from multiprocessing import cpu_count
import os
from shapely import wkt
from subprocess import Popen, PIPE, STDOUT
import time
from time import gmtime, strftime
import yaml

from mapchete_hub import cleanup_config
from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import main_options


logger = get_task_logger(__name__)
# suppress spam loggers
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("boto3").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)
logging.getLogger("smart_open").setLevel(logging.ERROR)


# ignore_result=True important, otherwise it will be stored in broker
@celery_app.task(bind=True, ignore_result=True)
def run(self, *args, **kwargs):
    config = kwargs["config"]
    process_area = kwargs["process_area"]
    logger.debug("initialize process")
    self.send_event('task-progress', progress_data=dict(current=None, total=None))
    mapchete_config = cleanup_config(config['mapchete_config'])

    run_mapchete(mapchete_config, bounds=wkt.loads(process_area).bounds)

    logger.debug("processing successful.")


def run_mapchete(
    mapchete_config, bounds=None, mapchete_mode="continue", overload=1
):
    mapchete_file = os.path.join(
        main_options['config_dir'], '%s_%s.mapchete' % (
            "_".join(map(str, bounds)),
            strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        )
    )
    if os.path.isfile(mapchete_file):
        os.remove(mapchete_file)
    with open(mapchete_file, 'w') as dst:
        logger.debug("dump mapchete file to %s", mapchete_file)
        yaml.safe_dump(
            mapchete_config, dst, default_flow_style=False, allow_unicode=True
        )

    multi = str(int(cpu_count() * overload))

    """Execute mapchete in subprocess & collect output."""
    logfile = os.environ.get('LOGFILE', None)
    process_logfile = os.path.join(
        os.path.dirname(logfile) if logfile else main_options['config_dir'],
        os.path.basename(mapchete_file)
    ) + ".log"

    start = time.time()
    cmd = [
        "mapchete", "execute", mapchete_file,
        "--logfile", process_logfile,
        "-m", multi,
        "--no_pbar"
    ]
    if bounds:
        cmd.append("--bounds")
        cmd.extend(map(str, bounds))
    if mapchete_mode == "overwrite":
        cmd.append("--overwrite")
    if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
        cmd.append("--debug")
    logger.debug(" ".join(cmd))
    returncode, output = _execute(cmd)
    if returncode:
        tb = output[:min([30, len(output)])]
        for line in tb:
            logger.error(line)
        raise RuntimeError("Subprocess failed: %s" % "\n".join(tb))
    logger.debug(
        "subprocess ran %s %s without errors in %s minutes", mapchete_file,
        " ".join(map(str, bounds)),
        round((time.time() - start) / 60, 1))


def _execute(command):
    with Popen(
        command, stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True
    ) as p:
        lines = []
        for line in p.stdout:
            logger.debug(line.strip())
            lines.append(line.strip())
    return p.returncode, lines
