import importlib.util
import logging

from fastapi import HTTPException


logger = logging.getLogger(__name__)


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

    v1_api = core_client()
    try:
        # List the namespaces to check if the client is connected properly
        namespaces = v1_api.list_namespace()
        logger.debug(
            f"Connected to Kubernetes. Found {len(namespaces.items)} namespaces."
        )
    except ApiException as e:
        logger.debug(f"Failed to connect to Kubernetes API: {e}")


# Function to get the status of the Kubernetes Job
def get_job_status(job_name: str, namespace: str):
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    batch_v1 = batch_client()
    try:
        # Get the Job status
        job: client.V1Job = batch_v1.read_namespaced_job(
            name=job_name, namespace=namespace
        )  # type: ignore
        status: client.V1JobStatus = job.status  # type: ignore

        if status.succeeded:
            return {"status": "Job completed", "succeeded": status.succeeded}
        elif status.failed:
            return {"status": "Job failed", "failed": status.failed}
        else:
            return {"status": "Job is still running", "active": status.active}

    except client.ApiException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job status: {e}")


# Function to list Pods created by the Job and get their logs
def get_job_pods_and_logs(job_name: str, namespace: str):
    if not importlib.util.find_spec("kubernetes"):
        raise ImportError("please install the 'kubernetes' extra")
    from kubernetes import client

    core_v1 = core_client()

    try:
        # List Pods created by the Job
        pod_list = core_v1.list_namespaced_pod(
            namespace=namespace, label_selector=f"job-name={job_name}"
        )

        pods_info = []
        for pod in pod_list.items:
            pod_name = pod.metadata.name
            pod_status = pod.status.phase

            # Fetch logs for the Pod
            logs = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)

            pods_info.append(
                {"pod_name": pod_name, "pod_status": pod_status, "logs": logs}
            )

        return pods_info

    except client.ApiException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pods or logs: {e}")
