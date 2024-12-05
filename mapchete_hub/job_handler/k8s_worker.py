from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import Any, List, Optional

from mapchete.commands.observer import Observers
from mapchete.enums import Status
import requests

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.k8s import (
    K8SJobAlreadyExists,
    K8SJobNotFound,
    KubernetesJobStatus,
    batch_client,
    get_job_status,
)
from mapchete_hub.models import JobEntry
from mapchete_hub.settings import JobWorkerResources, MHubSettings, mhub_settings
from mapchete_hub.timetools import passed_time_to_timestamp

logger = logging.getLogger(__name__)


class KubernetesWorkerJobHandler(JobHandlerBase):
    status_handler: BaseStatusHandler
    self_instance_name: str
    namespace: str
    image: str
    pod_resources: JobWorkerResources
    service_account_name: str
    image_pull_secret: str
    pod_env_vars: Optional[dict] = None
    backend_db_event_rate_limit: float
    retry_job_x_times: int
    remove_job_after_seconds: int

    _batch_v1_client: Optional[Any] = None

    def __init__(
        self,
        status_handler: BaseStatusHandler,
        self_instance_name: str,
        backend_db_event_rate_limit: float,
        namespace: str,
        image: str,
        pod_resources: JobWorkerResources,
        service_account_name: str,
        image_pull_secret: str,
        pod_env_vars: Optional[dict] = None,
        retry_job_x_times: int = 0,
        remove_job_after_seconds: int = 0,
    ):
        if not importlib.util.find_spec("kubernetes"):
            raise ImportError("please install the 'kubernetes' extra")

        self.status_handler = status_handler
        self.self_instance_name = self_instance_name
        self.backend_db_event_rate_limit = backend_db_event_rate_limit
        self.namespace = namespace
        self.image = image
        self.pod_resources = pod_resources
        self.service_account_name = service_account_name
        self.image_pull_secret = image_pull_secret
        self.pod_env_vars = pod_env_vars
        self.retry_job_x_times = retry_job_x_times
        self.remove_job_after_seconds = remove_job_after_seconds

    def submit(
        self, job_entry: JobEntry, observers: Optional[Observers] = None
    ) -> JobEntry:
        """Submit a job."""
        observers = observers or self.get_job_observers(job_entry)
        try:
            create_k8s_job(
                job_entry=job_entry,
                namespace=self.namespace,
                image=self.image,
                resources=self.pod_resources,
                service_account_name=self.service_account_name,
                image_pull_secret=self.image_pull_secret,
                pod_env_vars=self.pod_env_vars,
                retry_job_x_times=self.retry_job_x_times,
                remove_job_after_seconds=self.remove_job_after_seconds,
                batch_v1_client=self._batch_v1_client,
            )
            logger.debug(
                "job %s submitted and will be run as a kubernetes job"
                % job_entry.job_id
            )
            return self.status_handler.set(
                job_id=job_entry.job_id,
                submitted_to_k8s=True,
                k8s_attempts=job_entry.k8s_attempts + 1,
            )
        except K8SJobAlreadyExists:
            logger.error("kubernetes job %s already exists", job_entry.job_id)
            return job_entry
        except Exception as exc:
            observers.notify(status=Status.failed, exception=exc)
            raise

    def jobs(self, **kwargs) -> List[K8SJobEntry]:
        return [
            K8SJobEntry(**job_entry.model_dump(), k8s_job_handler=self)
            for job_entry in self.status_handler.jobs(**kwargs)
        ]

    def __enter__(self):
        """Enter context."""
        self._batch_v1_client = batch_client()
        return self

    def __exit__(self, *args):
        """Exit context."""
        return

    @staticmethod
    def from_settings(
        status_handler: BaseStatusHandler, settings: MHubSettings
    ) -> KubernetesWorkerJobHandler:
        if settings.k8s_namespace is None:
            raise ValueError(
                "MHUB_K8S_NAMESPACE has to be set when using 'k8s-job-worker'"
            )
        elif settings.k8s_service_account_name is None:
            raise ValueError(
                "MHUB_K8S_SERVICE_ACCOUNT_NAME has to be set when using 'k8s-job-worker'"
            )
        elif settings.k8s_image_pull_secret is None:
            raise ValueError(
                "MHUB_K8S_IMAGE_PULL_SECRET has to be set when using 'k8s-job-worker'"
            )
        return KubernetesWorkerJobHandler(
            status_handler=status_handler,
            self_instance_name=settings.self_instance_name,
            backend_db_event_rate_limit=settings.backend_db_event_rate_limit,
            namespace=settings.k8s_namespace,
            image=f"{settings.worker_default_image}:{settings.worker_image_tag}",
            pod_resources=settings.to_k8s_job_worker_resources(),
            service_account_name=settings.k8s_service_account_name,
            image_pull_secret=settings.k8s_image_pull_secret,
            pod_env_vars=settings.to_worker_env_vars(),
            retry_job_x_times=settings.k8s_retry_job_x_times,
            remove_job_after_seconds=settings.k8s_remove_job_after_seconds,
        )


class K8SJobEntry(JobEntry):
    """Special JobEntry class helping to interface with kubernetes."""

    k8s_job_handler: KubernetesWorkerJobHandler

    def k8s_submit(self):
        self.update(
            **self.k8s_job_handler.submit(JobEntry(**self.model_dump())).model_dump()
        )

    def k8s_retry(self):
        observers = self.k8s_job_handler.get_job_observers(self)
        remaining_retries = (
            mhub_settings.k8s_retry_job_x_times + 1
        ) - self.k8s_attempts

        # set job finally to failed if no retries are left
        if remaining_retries <= 0:
            logger.debug(
                "maximum retries (%s) already met (%s)",
                mhub_settings.k8s_retry_job_x_times,
                self.k8s_attempts,
            )
            observers.notify(
                status=Status.failed,
                exception=RuntimeError(
                    f"too many kubernetes job attempts ({self.k8s_attempts}) failed"
                ),
            )
            self.update(status=Status.failed)
            return

        # attempt a further retry
        logger.info(
            "%s: kubernetes job has failed, resubmitting to cluster ...", self.job_id
        )
        observers.notify(
            status=Status.retrying,
            message=f"kubernetes job run failed (remaining retries: {remaining_retries})",
        )
        self.k8s_submit()

    def k8s_job_status(self) -> KubernetesJobStatus:
        return get_job_status(
            self.job_id,
            namespace=self.k8s_job_handler.namespace,
            batch_v1=self.k8s_job_handler._batch_v1_client,
        )

    def k8s_is_failed(self) -> bool:
        return self.k8s_job_status().is_failed()

    def k8s_is_failed_or_gone(self) -> bool:
        try:
            k8s_job_status = self.k8s_job_status()
            failed_or_gone = k8s_job_status.is_failed()
        except K8SJobNotFound as exc:
            logger.debug(
                "job status cannot be fetched (%s), assuming job has failed...",
                str(exc),
            )
            failed_or_gone = self.submitted_to_k8s
        return failed_or_gone

    def has_active_status(self) -> bool:
        return self.status in [
            Status.initializing,
            Status.parsing,
            Status.running,
            Status.post_processing,
            Status.retrying,
        ] or (self.status == Status.pending and self.submitted_to_k8s)

    def is_queued(self) -> bool:
        return self.status == Status.pending and not self.submitted_to_k8s

    def is_stalled(
        self, inactive_since: str = "5h", check_inactive_dashboard: bool = True
    ) -> bool:
        # check if inactive for too long
        if self.has_active_status():
            if self.updated and passed_time_to_timestamp(inactive_since) > self.updated:
                logger.debug(
                    "%s: %s but has been inactive since %s",
                    self.job_id,
                    self.status,
                    self.updated,
                )
                return True
            elif (
                check_inactive_dashboard
                and self.dask_dashboard_link
                and requests.get(self.dask_dashboard_link).status_code != 200
            ):
                logger.debug(
                    "%s: %s but dashboard %s does not have a status code of 200",
                    self.job_id,
                    self.status,
                    self.dask_dashboard_link,
                )
                return True

        return False


# Define the Kubernetes Job specification
def create_k8s_job(
    job_entry: JobEntry,
    namespace: str,
    image: str,
    resources: JobWorkerResources,
    service_account_name: str,
    image_pull_secret: str,
    pod_env_vars: Optional[dict] = None,
    retry_job_x_times: int = 0,
    remove_job_after_seconds: int = 0,
    batch_v1_client: Optional[Any] = None,
) -> KubernetesJobStatus:
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    # Set up the Kubernetes client
    batch_v1: client.BatchV1Api = batch_v1_client or batch_client()

    if pod_env_vars:
        env_list = [
            client.V1EnvVar(name=key, value=value)
            for key, value in pod_env_vars.items()
        ]
    else:
        env_list = []

    # Define container spec
    container = client.V1Container(
        name=job_entry.job_id,
        image=image,
        command=["mhub-worker", "run-job", job_entry.job_id],
        env=env_list,
        resources=client.V1ResourceRequirements(
            limits=resources.get("limits"), requests=resources.get("requests")
        ),
    )

    # Define Pod spec with imagePullSecret
    pod_spec = client.V1PodSpec(
        containers=[container],
        restart_policy="Never",
        image_pull_secrets=[client.V1LocalObjectReference(name=image_pull_secret)],
        service_account_name=service_account_name,
        active_deadline_seconds=mhub_settings.k8s_worker_active_deadline_seconds,
    )

    # Define Pod template spec
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(name=job_entry.job_id), spec=pod_spec
    )

    # Define Job spec
    job_spec = client.V1JobSpec(
        template=template,
        backoff_limit=retry_job_x_times,
        ttl_seconds_after_finished=remove_job_after_seconds,
    )

    # Define the Job manifest
    request_body = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_entry.job_id),
        spec=job_spec,
    )

    # Create the job in the specified namespace
    try:
        k8s_job: client.V1Job = batch_v1.create_namespaced_job(
            namespace=namespace, body=request_body
        )  # type: ignore
    except Exception as exc:
        if "AlreadyExists" in str(exc):
            raise K8SJobAlreadyExists(
                f"a job with name {job_entry.job_id} already exists on cluster"
            )
        logger.exception(exc)
        raise RuntimeError(f"could not sent job to kubernetes cluster: {exc}")

    logger.debug("Job %s created in namespace %s", job_entry.job_id, namespace)
    status: client.V1JobStatus = k8s_job.status  # type: ignore
    return KubernetesJobStatus(**status.to_dict())
