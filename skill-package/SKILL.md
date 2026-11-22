---
name: kubedoctor
description: AI-powered Kubernetes troubleshooting and diagnostic assistant. Inspects cluster health, detects CrashLoopBackOff, ImagePullBackOff, and pending pods, analyzes deployments, services, and ingress, and provides evidence-based root-cause analysis.
---

# KubeDoctor: AI-Powered Kubernetes Troubleshooting Skill

KubeDoctor equips AI assistants with deep Kubernetes diagnostic capabilities via the Model Context Protocol (MCP). It enables an AI agent to inspect live cluster state, correlate logs and events, diagnose failing workloads, and provide evidence-based remediation advice without making destructive changes.

---

## When to Activate This Skill

Activate this skill whenever the user asks to:
- Troubleshoot, diagnose, or debug any Kubernetes workload, pod, or cluster issue.
- Identify why a pod is stuck in `CrashLoopBackOff`, `ImagePullBackOff`, `ErrImagePull`, or `Pending`.
- Check overall cluster or node health (readiness, CPU/memory pressure, disk pressure).
- Investigate broken Services, missing endpoints, or Ingress routing errors.
- Run a namespace-wide health scan or summarize cluster resource distribution.
- Retrieve and correlate container logs, exit codes, and Kubernetes events.

---

## Diagnostic Workflows

Follow these standard operational procedures when investigating Kubernetes issues:

### 1. General Cluster & Namespace Triage
1. When asked about general cluster health or starting an investigation:
   - Run `cluster_health` to ensure all nodes are `Ready` and have no memory/disk pressures.
   - Run `namespace_health_scan` on the target namespace to detect all unhealthy pods in one pass.
2. Provide an executive summary of healthy vs unhealthy workloads.

### 2. Deep Pod Diagnosis (The "Doctor" Workflow)
1. When a specific pod is failing or crashing:
   - Call `doctor(pod_name, namespace)` to gather:
     - Current lifecycle phase (`Pending`, `Running`, `Failed`).
     - Container waiting/terminated states and exit codes.
     - Recent container logs (last 50 lines).
     - Recent Kubernetes events matching the pod.
2. Interpret the exit code:
   - **Exit code 137**: Process killed by `OOMKilled` (Out of Memory). Recommend increasing memory requests/limits.
   - **Exit code 1 / 2**: Application error or missing configuration/secret. Check application logs.
   - **Exit code 0 with high restart count**: Container process completed and exited; container may be missing a long-running foreground daemon.

### 3. CrashLoopBackOff Investigation
1. Run `detect_crashloops(namespace)`.
2. For each identified pod:
   - Fetch recent logs via `get_pod_logs(pod_name, namespace, tail_lines=100)`.
   - Check restart count and terminated reasons via `diagnose_pod(pod_name, namespace)`.
3. Provide the root cause from the application stack trace.

### 4. Image Pull Error Investigation
1. Run `detect_image_pull_errors(namespace)`.
2. Inspect the failure reason (`ImagePullBackOff` vs `ErrImagePull`).
3. Check the error message in the events via `get_pod_events(pod_name, namespace)`:
   - *Repository does not exist / not found*: Typo in image name or tag.
   - *Authorization failed / access denied*: Missing `imagePullSecrets` or invalid container registry credentials.

### 5. Pending Pods (Scheduling Failures)
1. Run `detect_pending_pods(namespace)`.
2. Query the pod events via `get_pod_events(pod_name, namespace)`.
3. Identify the scheduling constraint:
   - *Insufficient memory / cpu*: Cluster nodes lack allocatable resources.
   - *Untolerated taints*: Workload lacks tolerations for dedicated node taints.
   - *FailedAttachVolume / FailedMount*: PVC is unbound or volume is attached to another node.

### 6. Networking, Service & Ingress Validation
1. If a service cannot be reached:
   - Call `diagnose_service(service_name, namespace)` to inspect ports and **ready endpoints**.
   - If `Ready endpoints: 0`, verify that the Service `selector` matches the Pod `labels`.
2. If HTTP/HTTPS traffic is failing at the gateway:
   - Call `diagnose_ingress(ingress_name, namespace)` to inspect hostnames, paths, and backend service mappings.

---

## MCP Tools Reference

| Tool Name | Parameters | Description |
|---|---|---|
| `cluster_health` | None | Evaluates node readiness and pressure conditions (Memory, Disk, PID). |
| `node_health` | None | Checks detailed conditions of all cluster nodes. |
| `list_pods` | `namespace: str = "default"` | Lists all pods in the namespace with their phase. |
| `namespace_overview` | `namespace: str = "default"` | High-level count of Pods, Services, and Deployments. |
| `namespace_health_scan`| `namespace: str = "default"` | Comprehensive health scan across all pods in a namespace. |
| `diagnose_pod` | `pod_name: str, namespace: str = "default"` | Deep container inspection, state messages, and exit codes. |
| `doctor` | `pod_name: str, namespace: str = "default"` | Master diagnostic engine: combines container state, logs, and events. |
| `get_pod_logs` | `pod_name: str, namespace: str = "default", tail_lines: int = 100` | Retrieves container logs. |
| `get_pod_events` | `pod_name: str, namespace: str = "default"` | Fetches events matching a pod name. |
| `detect_crashloops` | `namespace: str = "default"` | Finds all pods in `CrashLoopBackOff` or high restart count. |
| `detect_image_pull_errors` | `namespace: str = "default"` | Detects `ImagePullBackOff` and `ErrImagePull` errors. |
| `detect_pending_pods` | `namespace: str = "default"` | Detects pods stuck in `Pending` state. |
| `diagnose_deployment` | `deployment_name: str, namespace: str = "default"` | Checks desired vs available vs ready replicas and rollout status. |
| `diagnose_service` | `service_name: str, namespace: str = "default"` | Inspects ports, cluster IP, and ready backend endpoints. |
| `diagnose_ingress` | `ingress_name: str, namespace: str = "default"` | Inspects ingress class, host routing rules, and backends. |
| `pod_events` | `pod_name: str, namespace: str = "default"` | Detailed event timeline with occurrence counts. |

---

## Safety & Boundaries

- **Read-Only**: This skill only performs non-destructive read operations.
- **Never Mutate**: Never attempt to delete pods, scale deployments, or modify configurations directly unless explicitly confirmed and instructed by the user.
- **Evidence-Based Recommendations**: Always show the exact event, log excerpt, or container exit code that justifies your root-cause diagnosis.