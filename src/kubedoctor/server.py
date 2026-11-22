import os

from mcp.server.fastmcp import FastMCP
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# ============================================================
# Transport mode
#
#   KUBEDOCTOR_TRANSPORT=stdio  (default) - local subprocess mode
#   KUBEDOCTOR_TRANSPORT=http            - in-cluster HTTP/SSE mode
#
# When deployed via Helm, the Deployment sets this to "http"
# automatically. No code changes needed between environments.
# ============================================================

TRANSPORT = os.getenv("KUBEDOCTOR_TRANSPORT", "stdio")
HTTP_HOST = os.getenv("KUBEDOCTOR_HOST", "0.0.0.0")
# NOTE: Avoid KUBEDOCTOR_PORT — Kubernetes injects that automatically for
# services named "kubedoctor" (e.g. tcp://10.x.x.x:8000), which breaks int().
HTTP_PORT = int(os.getenv("KUBEDOCTOR_HTTP_PORT", "8000"))

mcp = FastMCP("KubeDoctor", host=HTTP_HOST, port=HTTP_PORT)


# ============================================================
# Kubernetes API helpers
# ============================================================

def load_kubernetes_config():
    """
    Load Kubernetes configuration.

    Local development:
        Uses ~/.kube/config

    Inside Kubernetes:
        Uses in-cluster configuration.
    """
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()


def get_core_api():
    """Return Kubernetes CoreV1 API client."""
    load_kubernetes_config()
    return client.CoreV1Api()


def get_apps_api():
    """Return Kubernetes AppsV1 API client."""
    load_kubernetes_config()
    return client.AppsV1Api()


def get_networking_api():
    """Return Kubernetes NetworkingV1 API client."""
    load_kubernetes_config()
    return client.NetworkingV1Api()


# ============================================================
# 1. Cluster Health
# ============================================================

@mcp.tool()
def cluster_health() -> str:
    """
    Check basic Kubernetes cluster health.
    Returns node readiness and pressure conditions.
    """

    try:
        v1 = get_core_api()
        nodes = v1.list_node()

        if not nodes.items:
            return "No Kubernetes nodes found."

        result = [
            "================================",
            "       KUBERNETES HEALTH",
            "================================",
        ]

        for node in nodes.items:
            name = node.metadata.name

            conditions = {
                condition.type: condition.status
                for condition in node.status.conditions or []
            }

            ready = conditions.get("Ready", "Unknown")
            memory = conditions.get("MemoryPressure", "Unknown")
            disk = conditions.get("DiskPressure", "Unknown")
            pid = conditions.get("PIDPressure", "Unknown")

            result.append("")
            result.append(f"Node: {name}")
            result.append(f"  Ready: {ready}")
            result.append(f"  MemoryPressure: {memory}")
            result.append(f"  DiskPressure: {disk}")
            result.append(f"  PIDPressure: {pid}")

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error connecting to Kubernetes: {e}"


# ============================================================
# 2. List Pods
# ============================================================

@mcp.tool()
def list_pods(namespace: str = "default") -> str:
    """
    List pods in a Kubernetes namespace.
    """

    try:
        v1 = get_core_api()

        pods = v1.list_namespaced_pod(namespace)

        if not pods.items:
            return f"No pods found in namespace '{namespace}'."

        result = [
            f"Pods in namespace '{namespace}':"
        ]

        for pod in pods.items:

            result.append(
                f"- {pod.metadata.name} | "
                f"Status: {pod.status.phase}"
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error: {e}"


# ============================================================
# 3. Pod Logs
# ============================================================

@mcp.tool()
def get_pod_logs(
    pod_name: str,
    namespace: str = "default",
    tail_lines: int = 100,
) -> str:
    """
    Retrieve logs from a Kubernetes pod.
    """

    try:
        v1 = get_core_api()

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
        )

        return logs or "Pod has no logs."

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error retrieving logs: {e}"


# ============================================================
# 4. Pod Diagnosis
# ============================================================

@mcp.tool()
def diagnose_pod(
    pod_name: str,
    namespace: str = "default",
) -> str:
    """
    Diagnose common Kubernetes pod problems.
    """

    try:
        v1 = get_core_api()

        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        result = [
            "================================",
            "       KUBEDOCTOR DIAGNOSIS",
            "================================",
            f"Pod: {pod_name}",
            f"Namespace: {namespace}",
            f"Phase: {pod.status.phase}",
        ]

        # ----------------------------------------------------
        # Containers
        # ----------------------------------------------------

        if pod.status.container_statuses:

            result.append("")
            result.append("Containers:")

            for container in pod.status.container_statuses:

                result.append("")
                result.append(
                    f"Container: {container.name}"
                )

                result.append(
                    f"  Ready: {container.ready}"
                )

                result.append(
                    f"  Restart Count: "
                    f"{container.restart_count}"
                )

                state = container.state

                if state.waiting:

                    result.append(
                        f"  Waiting Reason: "
                        f"{state.waiting.reason}"
                    )

                    if state.waiting.message:
                        result.append(
                            f"  Message: "
                            f"{state.waiting.message}"
                        )

                if state.running:

                    result.append(
                        "  State: Running"
                    )

                if state.terminated:

                    result.append(
                        f"  Terminated Reason: "
                        f"{state.terminated.reason}"
                    )

                    result.append(
                        f"  Exit Code: "
                        f"{state.terminated.exit_code}"
                    )

        # ----------------------------------------------------
        # Pod conditions
        # ----------------------------------------------------

        if pod.status.conditions:

            result.append("")
            result.append("Conditions:")

            for condition in pod.status.conditions:

                result.append(
                    f"- {condition.type}: "
                    f"{condition.status}"
                )

        # ----------------------------------------------------
        # Diagnosis
        # ----------------------------------------------------

        result.append("")
        result.append("Diagnosis:")

        phase = pod.status.phase

        if phase == "Running":

            result.append(
                "Pod is currently running."
            )

        elif phase == "Pending":

            result.append(
                "WARNING: Pod is Pending."
            )

            result.append(
                "Check scheduling, resources, "
                "volumes, node availability and events."
            )

        elif phase == "Failed":

            result.append(
                "CRITICAL: Pod has failed."
            )

            result.append(
                "Check container termination "
                "reason and pod events."
            )

        elif phase == "Succeeded":

            result.append(
                "Pod completed successfully."
            )

        else:

            result.append(
                f"Pod is in phase: {phase}"
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error diagnosing pod: {e}"


# ============================================================
# 5. Pod Events
# ============================================================

@mcp.tool()
def get_pod_events(
    pod_name: str,
    namespace: str = "default",
) -> str:
    """
    Get Kubernetes events associated with a pod.
    """

    try:
        v1 = get_core_api()

        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=(
                f"involvedObject.name={pod_name}"
            ),
        )

        if not events.items:
            return (
                f"No events found for pod "
                f"'{pod_name}'."
            )

        result = [
            f"Events for pod '{pod_name}':"
        ]

        for event in events.items:

            result.append(
                f"- [{event.type}] "
                f"{event.reason}: "
                f"{event.message}"
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error retrieving events: {e}"


# ============================================================
# 6. CrashLoopBackOff Detection
# ============================================================

@mcp.tool()
def detect_crashloops(
    namespace: str = "default",
) -> str:
    """
    Detect CrashLoopBackOff and frequently restarting containers.
    """

    try:
        v1 = get_core_api()

        pods = v1.list_namespaced_pod(namespace)

        findings = []

        for pod in pods.items:

            for container in pod.status.container_statuses or []:

                waiting = container.state.waiting

                if (
                    waiting
                    and waiting.reason == "CrashLoopBackOff"
                ):

                    findings.append(
                        f"CRITICAL | "
                        f"Pod={pod.metadata.name} | "
                        f"Container={container.name} | "
                        f"Restarts={container.restart_count}"
                    )

                elif container.restart_count >= 5:

                    findings.append(
                        f"WARNING | "
                        f"Pod={pod.metadata.name} | "
                        f"Container={container.name} | "
                        f"Restarts={container.restart_count}"
                    )

        if not findings:

            return (
                "No CrashLoopBackOff or "
                "high restart containers detected."
            )

        return (
            "KubeDoctor CrashLoop Findings:\n"
            + "\n".join(findings)
        )

    except Exception as e:
        return f"Error detecting crashloops: {e}"


# ============================================================
# 7. Image Pull Error Detection
# ============================================================

@mcp.tool()
def detect_image_pull_errors(
    namespace: str = "default",
) -> str:
    """
    Detect ImagePullBackOff and ErrImagePull errors.
    """

    try:
        v1 = get_core_api()

        pods = v1.list_namespaced_pod(namespace)

        findings = []

        for pod in pods.items:

            for container in pod.status.container_statuses or []:

                waiting = container.state.waiting

                if (
                    waiting
                    and waiting.reason
                    in ["ImagePullBackOff", "ErrImagePull"]
                ):

                    findings.append(
                        f"CRITICAL | "
                        f"Pod={pod.metadata.name} | "
                        f"Container={container.name} | "
                        f"Reason={waiting.reason} | "
                        f"Message={waiting.message}"
                    )

        if not findings:

            return "No image pull errors detected."

        return (
            "KubeDoctor Image Pull Findings:\n"
            + "\n".join(findings)
        )

    except Exception as e:
        return (
            f"Error detecting image pull errors: {e}"
        )


# ============================================================
# 8. Pending Pod Detection
# ============================================================

@mcp.tool()
def detect_pending_pods(
    namespace: str = "default",
) -> str:
    """
    Detect pods stuck in Pending state.
    """

    try:
        v1 = get_core_api()

        pods = v1.list_namespaced_pod(namespace)

        pending = [
            pod.metadata.name
            for pod in pods.items
            if pod.status.phase == "Pending"
        ]

        if not pending:

            return "No Pending pods detected."

        result = [
            "KubeDoctor Pending Pods:"
        ]

        for pod_name in pending:

            result.append(
                f"- WARNING | {pod_name}"
            )

        result.append("")
        result.append(
            "Check pod events to determine "
            "the scheduling problem."
        )

        return "\n".join(result)

    except Exception as e:
        return f"Error detecting Pending pods: {e}"


# ============================================================
# 9. Node Health
# ============================================================

@mcp.tool()
def node_health() -> str:
    """
    Check Kubernetes node readiness and pressure.
    """

    try:
        v1 = get_core_api()

        nodes = v1.list_node()

        result = [
            "KubeDoctor Node Health"
        ]

        for node in nodes.items:

            result.append("")
            result.append(
                f"Node: {node.metadata.name}"
            )

            for condition in node.status.conditions or []:

                if condition.type in [
                    "Ready",
                    "MemoryPressure",
                    "DiskPressure",
                    "PIDPressure",
                ]:

                    result.append(
                        f"  {condition.type}: "
                        f"{condition.status}"
                    )

        return "\n".join(result)

    except Exception as e:
        return f"Error checking nodes: {e}"


# ============================================================
# 10. Deployment Diagnosis
# ============================================================

@mcp.tool()
def diagnose_deployment(
    deployment_name: str,
    namespace: str = "default",
) -> str:
    """
    Diagnose Kubernetes Deployment health.
    """

    try:
        apps = get_apps_api()

        deployment = apps.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
        )

        desired = deployment.spec.replicas or 0
        available = (
            deployment.status.available_replicas or 0
        )
        ready = (
            deployment.status.ready_replicas or 0
        )
        updated = (
            deployment.status.updated_replicas or 0
        )

        result = [
            "================================",
            "   DEPLOYMENT DIAGNOSIS",
            "================================",
            f"Deployment: {deployment_name}",
            f"Namespace: {namespace}",
            "",
            f"Desired: {desired}",
            f"Available: {available}",
            f"Ready: {ready}",
            f"Updated: {updated}",
            "",
        ]

        if available < desired:

            result.append(
                "WARNING: Not all replicas are available."
            )

        if ready < desired:

            result.append(
                "WARNING: Not all replicas are ready."
            )

        if updated < desired:

            result.append(
                "WARNING: Rollout is incomplete."
            )

        if (
            available == desired
            and ready == desired
            and updated == desired
        ):

            result.append(
                "Deployment appears healthy."
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error diagnosing deployment: {e}"


# ============================================================
# 11. Service Diagnosis
# ============================================================

@mcp.tool()
def diagnose_service(
    service_name: str,
    namespace: str = "default",
) -> str:
    """
    Diagnose a Kubernetes Service and its endpoints.
    """

    try:
        v1 = get_core_api()

        service = v1.read_namespaced_service(
            name=service_name,
            namespace=namespace,
        )

        endpoints = v1.read_namespaced_endpoints(
            name=service_name,
            namespace=namespace,
        )

        result = [
            "================================",
            "     SERVICE DIAGNOSIS",
            "================================",
            f"Service: {service_name}",
            f"Namespace: {namespace}",
            "",
            f"Type: {service.spec.type}",
            f"Cluster IP: {service.spec.cluster_ip}",
            "",
            "Ports:",
        ]

        for port in service.spec.ports or []:

            result.append(
                f"- {port.port} -> "
                f"{port.target_port}"
            )

        endpoint_count = 0

        for subset in endpoints.subsets or []:

            endpoint_count += len(
                subset.addresses or []
            )

        result.append("")
        result.append(
            f"Ready endpoints: {endpoint_count}"
        )

        if endpoint_count == 0:

            result.append(
                "CRITICAL: Service has no ready endpoints."
            )

        else:

            result.append(
                "Service has ready endpoints."
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error diagnosing service: {e}"


# ============================================================
# 12. Ingress Diagnosis
# ============================================================

@mcp.tool()
def diagnose_ingress(
    ingress_name: str,
    namespace: str = "default",
) -> str:
    """
    Diagnose a Kubernetes Ingress.
    """

    try:
        networking = get_networking_api()

        ingress = networking.read_namespaced_ingress(
            name=ingress_name,
            namespace=namespace,
        )

        result = [
            "================================",
            "     INGRESS DIAGNOSIS",
            "================================",
            f"Ingress: {ingress_name}",
            f"Namespace: {namespace}",
            "",
        ]

        ingress_class = (
            ingress.spec.ingress_class_name
        )

        result.append(
            f"Ingress Class: "
            f"{ingress_class or 'Not specified'}"
        )

        result.append("")
        result.append("Rules:")

        if not ingress.spec.rules:

            result.append(
                "No ingress rules configured."
            )

        for rule in ingress.spec.rules:

            result.append(
                f"- Host: {rule.host or '*'}"
            )

            if rule.http:

                for path in rule.http.paths:

                    service_name = (
                        path.backend.service.name
                        if path.backend.service
                        else "Unknown"
                    )

                    result.append(
                        f"  Path: {path.path}"
                    )

                    result.append(
                        f"  Service: {service_name}"
                    )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error diagnosing ingress: {e}"


# ============================================================
# 13. Namespace Overview
# ============================================================

@mcp.tool()
def namespace_overview(
    namespace: str = "default",
) -> str:
    """
    Provide a high-level overview of a namespace.
    """

    try:
        v1 = get_core_api()
        apps = get_apps_api()

        pods = v1.list_namespaced_pod(namespace)
        services = v1.list_namespaced_service(namespace)
        deployments = apps.list_namespaced_deployment(
            namespace
        )

        running = 0
        pending = 0
        failed = 0

        for pod in pods.items:

            if pod.status.phase == "Running":
                running += 1

            elif pod.status.phase == "Pending":
                pending += 1

            elif pod.status.phase == "Failed":
                failed += 1

        result = [
            "================================",
            "     NAMESPACE OVERVIEW",
            "================================",
            f"Namespace: {namespace}",
            "",
            f"Pods: {len(pods.items)}",
            f"  Running: {running}",
            f"  Pending: {pending}",
            f"  Failed: {failed}",
            "",
            f"Services: {len(services.items)}",
            f"Deployments: {len(deployments.items)}",
        ]

        return "\n".join(result)

    except Exception as e:
        return f"Error: {e}"


# ============================================================
# 14. MASTER KUBEDOCTOR
# ============================================================

@mcp.tool()
def namespace_health_scan(
    namespace: str = "default",
) -> str:
    """
    Run a comprehensive read-only Kubernetes health scan across all pods in a namespace.
    """

    try:
        v1 = get_core_api()

        pods = v1.list_namespaced_pod(namespace)

        findings = []

        for pod in pods.items:

            pod_name = pod.metadata.name

            # ----------------------------------------------
            # Pending
            # ----------------------------------------------

            if pod.status.phase == "Pending":

                findings.append(
                    f"WARNING | {pod_name} | "
                    f"Pod is Pending"
                )

            # ----------------------------------------------
            # Failed
            # ----------------------------------------------

            if pod.status.phase == "Failed":

                findings.append(
                    f"CRITICAL | {pod_name} | "
                    f"Pod has Failed"
                )

            # ----------------------------------------------
            # Container analysis
            # ----------------------------------------------

            for container in (
                pod.status.container_statuses or []
            ):

                waiting = container.state.waiting

                # CrashLoop
                if (
                    waiting
                    and waiting.reason
                    == "CrashLoopBackOff"
                ):

                    findings.append(
                        f"CRITICAL | "
                        f"{pod_name} | "
                        f"{container.name} | "
                        f"CrashLoopBackOff"
                    )

                # Image pull
                if (
                    waiting
                    and waiting.reason
                    in [
                        "ImagePullBackOff",
                        "ErrImagePull",
                    ]
                ):

                    findings.append(
                        f"CRITICAL | "
                        f"{pod_name} | "
                        f"{container.name} | "
                        f"{waiting.reason}"
                    )

                # Restart count
                if container.restart_count >= 5:

                    findings.append(
                        f"WARNING | "
                        f"{pod_name} | "
                        f"{container.name} | "
                        f"Restarts="
                        f"{container.restart_count}"
                    )

                # Not ready
                if not container.ready:

                    findings.append(
                        f"WARNING | "
                        f"{pod_name} | "
                        f"{container.name} | "
                        f"Container not ready"
                    )

        # ----------------------------------------------
        # Build report
        # ----------------------------------------------

        result = [
            "==========================================",
            "             KUBEDOCTOR",
            "          HEALTH REPORT",
            "==========================================",
            f"Namespace: {namespace}",
            "",
        ]

        if not findings:

            result.append(
                "STATUS: HEALTHY"
            )

            result.append(
                "No obvious pod-level problems detected."
            )

        else:

            result.append(
                f"STATUS: {len(findings)} FINDING(S)"
            )

            result.append("")

            result.extend(
                f"- {finding}"
                for finding in findings
            )

        result.append("")
        result.append(
            "KubeDoctor performs read-only diagnostics."
        )

        return "\n".join(result)

    except Exception as e:
        return f"KubeDoctor error: {e}"

@mcp.tool()
def pod_events(
    pod_name: str,
    namespace: str = "default",
) -> str:
    """
    Get Kubernetes events related to a specific pod.
    Useful for diagnosing scheduling, image pulling,
    volume mounting and container startup problems.
    """

    try:
        v1 = get_core_api()

        events = v1.list_namespaced_event(
            namespace=namespace
        )

        matched_events = []

        for event in events.items:
            involved = event.involved_object

            if (
                involved.name == pod_name
                and involved.kind == "Pod"
            ):
                matched_events.append(
                    {
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "count": event.count,
                        "timestamp": (
                            event.last_timestamp
                            or event.event_time
                        ),
                    }
                )

        if not matched_events:
            return (
                f"No events found for pod "
                f"'{pod_name}'."
            )

        result = [
            f"Events for pod '{pod_name}':"
        ]

        for event in matched_events:
            result.append(
                f"- Type: {event['type']} | "
                f"Reason: {event['reason']} | "
                f"Message: {event['message']} | "
                f"Count: {event['count']}"
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Error retrieving events: {e}"

@mcp.tool()
def doctor(
    pod_name: str,
    namespace: str = "default",
) -> str:
    """
    Perform a complete Kubernetes diagnosis for a pod.
    Collects pod status, container status, logs and events.
    """

    try:
        v1 = get_core_api()

        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        result = []

        result.append("=== KUBEDOCTOR REPORT ===")
        result.append(
            f"Pod: {pod_name}"
        )
        result.append(
            f"Namespace: {namespace}"
        )
        result.append(
            f"Phase: {pod.status.phase}"
        )

        # -------------------------
        # Container information
        # -------------------------

        result.append("\n=== CONTAINERS ===")

        if pod.status.container_statuses:

            for container in pod.status.container_statuses:

                result.append(
                    f"\nContainer: {container.name}"
                )

                result.append(
                    f"Ready: {container.ready}"
                )

                result.append(
                    f"Restart Count: "
                    f"{container.restart_count}"
                )

                state = container.state

                if state.waiting:

                    result.append(
                        f"Waiting Reason: "
                        f"{state.waiting.reason}"
                    )

                    if state.waiting.message:
                        result.append(
                            f"Waiting Message: "
                            f"{state.waiting.message}"
                        )

                if state.terminated:

                    result.append(
                        f"Terminated Reason: "
                        f"{state.terminated.reason}"
                    )

                    result.append(
                        f"Exit Code: "
                        f"{state.terminated.exit_code}"
                    )

        # -------------------------
        # Logs
        # -------------------------

        result.append("\n=== LOGS ===")

        try:

            logs = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=50,
            )

            result.append(logs)

        except Exception as e:

            result.append(
                f"Unable to retrieve logs: {e}"
            )

        # -------------------------
        # Events
        # -------------------------

        result.append("\n=== EVENTS ===")

        try:

            events = v1.list_namespaced_event(
                namespace=namespace
            )

            for event in events.items:

                if (
                    event.involved_object.name
                    == pod_name
                    and event.involved_object.kind
                    == "Pod"
                ):

                    result.append(
                        f"- {event.type} | "
                        f"{event.reason} | "
                        f"{event.message}"
                    )

        except Exception as e:

            result.append(
                f"Unable to retrieve events: {e}"
            )

        # -------------------------
        # Basic diagnosis
        # -------------------------

        result.append("\n=== INITIAL DIAGNOSIS ===")

        phase = pod.status.phase

        if phase == "Pending":

            result.append(
                "Pod is Pending. "
                "Investigate scheduling, "
                "resources, volumes or image pulling."
            )

        elif phase == "Running":

            result.append(
                "Pod is running. "
                "Check readiness, logs and "
                "application behaviour."
            )

        elif phase == "Failed":

            result.append(
                "Pod has failed. "
                "Inspect container termination "
                "reason and events."
            )

        elif phase == "Succeeded":

            result.append(
                "Pod completed successfully."
            )

        return "\n".join(result)

    except ApiException as e:
        return f"Kubernetes API error: {e}"

    except Exception as e:
        return f"Doctor error: {e}"

# ============================================================
# MCP Server
# ============================================================

if __name__ == "__main__":
    if TRANSPORT == "http":
        # In-cluster mode: HTTP/SSE transport
        # Helm sets KUBEDOCTOR_TRANSPORT=http via the Deployment env var
        print(
            f"Starting KubeDoctor MCP server "
            f"[HTTP/SSE] on {HTTP_HOST}:{HTTP_PORT}"
        )
        mcp.run(transport="sse")
    else:
        # Local mode: stdio transport (default, unchanged behaviour)
        mcp.run()