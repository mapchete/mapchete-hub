from tempfile import NamedTemporaryFile

from mapchete_hub import log


def test_log():
    log.set_log_level("DEBUG")
    with NamedTemporaryFile() as tempfile:
        log.setup_logfile(tempfile.name)
