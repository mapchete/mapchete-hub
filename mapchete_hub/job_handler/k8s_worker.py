from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import Any, Optional

from mapchete.enums import Status

from mapchete_hub.db.base import BaseStatusHandler
from mapchete_hub.job_handler.base import JobHandlerBase
from mapchete_hub.k8s import KubernetesJobStatus, batch_client
from mapchete_hub.models import JobEntry
from mapchete_hub.settings import JobWorkerResources, MHubSettings

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

    def submit(self, job_entry: JobEntry) -> None:
        """Submit a job."""
        observers = self.get_job_observers(job_entry)
        try:
            create_k8s_job(
                job_entry=job_entry,
                namespace=self.namespace,
                image=self.image,
                resources=self.pod_resources,
                service_account_name=self.service_account_name,
                image_pull_secret=self.image_pull_secret,
                pod_env_vars=self.pod_env_vars,
                remove_job_after_seconds=40,
                batch_v1_client=self._batch_v1_client,
            )
            self.status_handler.set(job_id=job_entry.job_id, submitted_to_k8s=True)
            logger.debug(
                "job %s submitted and will be run as a kubernetes job"
                % job_entry.job_id
            )
        except Exception as exc:
            observers.notify(status=Status.failed, exception=exc)
            raise

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
        )


# Define the Kubernetes Job specification
def create_k8s_job(
    job_entry: JobEntry,
    namespace: str,
    image: str,
    resources: JobWorkerResources,
    service_account_name: str,
    image_pull_secret: str,
    pod_env_vars: Optional[dict] = None,
    remove_job_after_seconds: int = 20,
    batch_v1_client: Optional[Any] = None,
) -> KubernetesJobStatus:
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    # Set up the Kubernetes client
    batch_v1: client.BatchV1Api = batch_v1_client or batch_client()
    logger.debug("Connected to k8s cluster as %s", batch_v1)

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
    )

    # Define Pod template spec
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(name=job_entry.job_id), spec=pod_spec
    )

    # Define Job spec
    job_spec = client.V1JobSpec(
        template=template,
        backoff_limit=1,  # Retry the job x times on failure
        ttl_seconds_after_finished=remove_job_after_seconds,  # Remove job from k8s after 100 seconds
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
        logger.exception(exc)
        raise RuntimeError(f"could not sent job to kubernetes cluster: {exc}")

    logger.debug(
        "Job %s created in namespace %s with status %s",
        job_entry.job_id,
        namespace,
        k8s_job.status,
    )
    status: client.V1JobStatus = k8s_job.status  # type: ignore
    return KubernetesJobStatus(**status.to_dict())
