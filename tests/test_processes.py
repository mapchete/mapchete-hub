from mapchete_hub import get_next_jobs


def test_submit(example_config):
    jobs = get_next_jobs(
        job_id="first_job",
        config=example_config,
        process_area=None,
    )
    assert len(jobs) == 1
