from shapely.geometry import box

from mapchete_hub.monitor import StatusHandler


def test_statushandler(status_gpkg, status_profile):
    test_job = "test_job"
    another_test_job = "another_test_job"
    geom = box(0, 1, 2, 3).wkt

    progress = {
        'geom': geom,
        'clock': 112,
        'timestamp': 1527938160.7215874,
        'type': 'task-progress',
        'uuid': test_job,
        'utcoffset': -2,
        'state': 'PROGRESS',
    }

    success = {
        'geom': geom,
        'clock': 64,
        'pid': 20106,
        'uuid': test_job,
        'runtime': 40.91311929101357,
        'state': 'SUCCESS',
        'timestamp': 1527938183.97571,
        'hostname': 'zone_worker@tycho2',
        'utcoffset': -2,
        'local_received': 1527938183.9801202,
        'result': 'None',
        'type': 'task-succeeded'
    }

    failure = {
        'utcoffset': -2,
        'pid': 16322,
        'local_received': 1527934867.8697965,
        'traceback': 'Traceback (most recent call last):  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 382, in trace_task\n    R = retval = fun(*args, **kwargs)\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 641, in __protected_call__\n    return self.run(*args, **kwargs)\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/workers/zone_worker.py", line 24, in run\n    for i, _ in enumerate(executor):\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 39, in mapchete_execute\n    chunksize=min([max([total_tiles // multi, 1]), max_chunksize])\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 1920, in next\n    raise Exception(value)\nException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 358, in workloop\n    result = (True, prepare_result(fun(*args, **kwargs)))\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 79, in _process_worker\n    output = process.execute(process_tile, raise_nodata=True)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 268, in execute\n    return self._execute(process_tile, raise_nodata=raise_nodata)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 507, in _execute\n    raise MapcheteProcessException(format_exc())\nmapchete.errors.MapcheteProcessException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\n\n', 'exception': 'Exception(<ExceptionInfo: MapcheteProcessException(\'Traceback (most recent call last):\\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\\n    process_data = self.config.process_func(tile_process)\\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\\n    assert randint(0, 500)\\nAssertionError\\n\',)>,)',
        'uuid': 'herbert',
        'type': 'task-failed',
        'hostname': 'zone_worker@tycho2',
        'timestamp': 1527934867.8687088,
        'clock': 10,
        'state': 'FAILURE'
    }

    another_progress = dict(progress, uuid=another_test_job)

    with StatusHandler(status_gpkg, 'w', profile=status_profile) as status_w:
        with StatusHandler(status_gpkg, 'r') as status_r:
            # write progress event
            status_w.update(test_job, progress)

            # get current state
            current = status_r.job(test_job)
            for k in progress.keys():
                if k in status_profile['schema']:
                    assert progress[k] == current[k]

            # write success event
            status_w.update(test_job, success)
            current = status_r.job(test_job)
            for k in success.keys():
                if k in status_profile['schema']:
                    assert success[k] == current[k]

            # write fail event
            status_w.update(test_job, failure)
            current = status_r.job(test_job)
            for k in failure.keys():
                if k in status_profile['schema']:
                    assert failure[k] == current[k]

            # write another job
            status_w.update(another_test_job, another_progress)
            all_jobs = status_r.all()
            assert len(all_jobs) == 2
