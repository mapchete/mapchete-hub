from datetime import datetime
import importlib.util
import logging
from typing import List, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class V1JobCondition(BaseModel):
    # Last time the condition was checked.
    # [optional]
    last_probe_time: Optional[datetime]
    # Last time the condition transit from one status to another.
    # [optional]
    last_transition_time: Optional[datetime]
    # Human readable message indicating details about last transition.
    # [optional]
    message: Optional[str]
    # (brief) reason for the condition's last transition.
    # [optional]
    reason: Optional[str]
    # Status of the condition, one of True, False, Unknown.
    status: Literal["True", "False", "Unknown"]
    # Type of job condition, Complete or Failed.
    type: Literal["Complete", "Failed"]


class KubernetesJobStatus(BaseModel):
    # this is a selection of V1JobStatus metadata
    # from https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1JobStatus.md

    # The number of pending and running pods which are not terminating (without a deletionTimestamp).
    # The value is zero for finished jobs. [optional]
    active: Optional[int]

    # Represents time when the job was completed. It is not guaranteed to be set in happens-before
    # order across separate operations. It is represented in RFC3339 form and is in UTC. The
    # completion time is set when the job finishes successfully, and only then. The value cannot be
    # updated or removed. The value indicates the same or later point in time as the startTime field.
    # [optional]
    completion_time: Optional[datetime]

    # The latest available observations of an object's current state. When a Job fails, one of the
    # conditions will have type "Failed" and status true. When a Job is suspended, one
    # of the conditions will have type "Suspended" and status true; when the Job is
    # resumed, the status of this condition will become false. When a Job is completed, one of the
    # conditions will have type "Complete" and status true. A job is considered finished
    # when it is in a terminal condition, either "Complete" or "Failed". A Job
    # cannot have both the "Complete" and "Failed" conditions. Additionally, it
    # cannot be in the "Complete" and "FailureTarget" conditions. The
    # "Complete", "Failed" and "FailureTarget" conditions cannot be
    # disabled.
    # More info: https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/
    # [optional]
    conditions: Optional[list[V1JobCondition]]

    # The number of pods which reached phase Failed. The value increases monotonically.
    # [optional]
    failed: Optional[int]

    # The number of active pods which have a Ready condition and are not terminating (without a
    # deletionTimestamp).
    # [optional]
    ready: Optional[int]

    # Represents time when the job controller started processing a job. When a Job is created in
    # the suspended state, this field is not set until the first time it is resumed. This field is
    # reset every time a Job is resumed from suspension. It is represented in RFC3339 form and is
    # in UTC. Once set, the field can only be removed when the job is suspended. The field cannot
    # be modified while the job is unsuspended or finished.
    # [optional]
    start_time: Optional[datetime]

    # The number of pods which reached phase Succeeded. The value increases monotonically for a
    # given spec. However, it may decrease in reaction to scale down of elastic indexed jobs.
    # [optional]
    succeeded: Optional[int]

    # The number of pods which are terminating (in phase Pending or Running and have a
    # deletionTimestamp). This field is beta-level. The job controller populates the field when the
    # feature gate JobPodReplacementPolicy is enabled (enabled by default).
    # [optional]
    terminating: Optional[int]


class PodInfo(BaseModel):
    name: str
    status: str
    logs: str


def batch_client():
    """
    This function sets up the Kubernetes client based on whether the code
    is running inside or outside a Kubernetes cluster.
    """
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import config, client

    try:
        # Try to load in-cluster configuration
        config.load_incluster_config()
        logger.debug("In-cluster configuration loaded")
    except Exception as e:
        # If not running inside the cluster, fall back to kubeconfig
        logger.debug("In-cluster config failed. Trying kubeconfig:", e)
        logger.debug("Kubeconfig loaded")

    # Return a configured Kubernetes client
    return client.BatchV1Api()


def core_client():
    """
    Sets up the Kubernetes client based on the environment (in-cluster or kubeconfig).
    """
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import config, client

    try:
        config.load_incluster_config()
        logger.debug("In-cluster configuration loaded")
    except Exception as e:
        logger.debug("In-cluster config failed, loading kubeconfig:", e)
        config.load_kube_config()
        logger.debug("Kubeconfig loaded")
    return client.CoreV1Api()


def check_k8s_connection():
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes.client import ApiException

    try:
        # List the namespaces to check if the client is connected properly
        namespaces = core_client().list_namespace()
        logger.debug(
            f"Connected to Kubernetes. Found {len(namespaces.items)} namespaces."
        )
    except ApiException as e:
        logger.debug(f"Failed to connect to Kubernetes API: {e}")


# Function to get the status of the Kubernetes Job
def get_job_status(job_name: str, namespace: str) -> KubernetesJobStatus:
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    batch_v1 = batch_client()
    try:
        # Get the Job status
        k8s_job: client.V1Job = batch_v1.read_namespaced_job(
            name=job_name, namespace=namespace
        )  # type: ignore

        return KubernetesJobStatus(**k8s_job.to_dict())

        # just kept that here for future reference
        # status: client.V1JobStatus = job.status  # type: ignore
        # if status.succeeded:
        #     return {"status": "Job completed", "succeeded": status.succeeded}
        # elif status.failed:
        #     return {"status": "Job failed", "failed": status.failed}
        # else:
        #     return {"status": "Job is still running", "active": status.active}

    except client.ApiException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job status: {e}")


# Function to list Pods created by the Job and get their logs
def get_job_pods_and_logs(job_name: str, namespace: str) -> List[PodInfo]:
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    core_v1 = core_client()

    try:
        # List Pods created by the Job
        pod_list = core_v1.list_namespaced_pod(
            namespace=namespace, label_selector=f"job-name={job_name}"
        )
        return [
            PodInfo(
                name=pod.metadata.name,
                status=pod.status.phase,
                logs=core_v1.read_namespaced_pod_log(
                    name=pod.metadata.name, namespace=namespace
                ),
            )
            for pod in pod_list.items
        ]

    except client.ApiException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pods or logs: {e}")
