# KubeDoctor

> **AI-Powered Kubernetes Troubleshooting & Diagnostic Platform built on the Model Context Protocol (MCP).**

[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-MCP-black?style=for-the-badge)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Helm](https://img.shields.io/badge/Helm-3+-0F1689?style=for-the-badge&logo=helm&logoColor=white)](https://helm.sh)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

---

## Overview

**KubeDoctor** bridges the gap between Kubernetes clusters and modern AI assistants. Built on the **Model Context Protocol (MCP)**, it exposes deep cluster diagnostics, real-time workload inspections, and automatic failure analysis as structured tools that can be consumed by:

- **AI Assistants & IDEs** (Claude Desktop, Antigravity, Cursor, Windsurf, custom LLM agents)
- **DevOps & SRE Engineers** via an interactive CLI diagnostic terminal
- **Automation pipelines, Slackbots, & internal developer platforms**

---

## Two Deployment Modes (100% Identical Troubleshooting Experience)

Regardless of which deployment mode you choose, **the user experience is 100% identical**:
- Same interactive CLI commands (`health`, `pods`, `doctor`, `crashes`, `scan`).
- Same output format and diagnostic reports.
- Same 16 MCP tools available to AI assistants.

The difference is only **where the server runs** and **how authentication is handled**:

```
+--------------------------------------------------------+
|             Mode 1: Local Developer Mode               |
|         (Zero-Cluster Installation / stdio)            |
+-------------------------------------------+------------+
                                            | stdio
                                     +------v------+
                                     |  Developer  |
                                     | Workstation |
                                     +------+------+
                                            | ~/.kube/config
                                     +------v------+
                                     | K8s Cluster |
                                     +-------------+

+--------------------------------------------------------+
|             Mode 2: In-Cluster Helm Mode               |
|      (Direct Ingress / Zero Credential Distribution)   |
+--------------------------------------------------------+
  Clients (Claude Desktop, Cursor, CLI, CI/CD)
             |
             | HTTP / SSE (Direct via Ingress - No port-forward!)
      +------v------+
      | K8s Ingress | (e.g. http://localhost/sse)
      +------+------+
             | port 8000
      +------v--------------+
      |  KubeDoctor Pod     |
      |  (Read-Only RBAC)   |
      +------+--------------+
             | In-Cluster ServiceAccount API
      +------v------+
      | K8s Cluster |
      +-------------+
```

### Quick Comparison

| Feature | Mode 1: Local Developer Mode | Mode 2: In-Cluster Helm Mode |
|---|---|---|
| **Best For** | Solo developers, local cluster testing | DevOps teams, enterprises, shared AI tools |
| **Cluster Footprint** | **Zero** — nothing installed in cluster | 1 Pod + Read-only RBAC in `kubedoctor` namespace |
| **Cluster Auth** | Uses your personal `~/.kube/config` | In-Cluster `ServiceAccount` (Read-only RBAC) |
| **Connection Transport**| Standard I/O (`stdio` subprocess) | Network HTTP (`SSE` stream via Ingress) |
| **Port-Forward Needed?**| No | **No** (Direct access via Ingress!) |
| **Team Credential Sharing**| Requires sharing admin kubeconfig | **Zero credential sharing** required |
| **Troubleshooting Tools**| All 16 MCP tools | All 16 MCP tools (Identical) |

---

## Installation & Usage

---

### Mode 1: Local Developer Mode (Quickstart)

Run KubeDoctor directly from your laptop without installing anything inside your Kubernetes cluster.

#### Prerequisites
- Python 3.13+ installed
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`
- Valid `~/.kube/config` with cluster access

#### Step 1: Clone & Setup
```bash
git clone https://github.com/rahuldan98/KubeDoctor.git
cd KubeDoctor
uv sync
```

#### Step 2: Launch the Diagnostic CLI
```bash
uv run python src/kubedoctor/client.py
```

#### Step 3: Connect to AI Tools (Claude Desktop / Cursor / Antigravity)
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "kubedoctor": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/KubeDoctor",
        "python",
        "src/kubedoctor/server.py"
      ]
    }
  }
}
```

---

### Mode 2: In-Cluster Helm Mode (Enterprise & Team Setup)

Deploy KubeDoctor inside the cluster as a centralized diagnostic server. With Ingress enabled, users and AI agents connect directly over HTTP with **zero port-forwarding required**.

#### Prerequisites
- Kubernetes cluster 1.24+
- `helm` 3.0+
- Ingress controller (e.g. `ingress-nginx`) installed in your cluster

#### Step 1: Install with Helm (Ingress Enabled)
```bash
helm install kubedoctor ./helm/kubedoctor \
  --namespace kubedoctor \
  --create-namespace \
  --set image.repository=rahuldan98/kubedoctor \
  --set image.tag=latest \
  --set ingress.enabled=true
```

#### Step 2: Verify the Deployment
```bash
kubectl get all,ingress -n kubedoctor
```
Expected output:
```text
NAME                              READY   STATUS    RESTARTS   AGE
pod/kubedoctor-xxxxxxxxxx-xxxxx   1/1     Running   0          30s

NAME                 TYPE        CLUSTER-IP     PORT(S)
service/kubedoctor   ClusterIP   10.96.250.94   8000/TCP

NAME                 CLASS   HOSTS                        ADDRESS   PORTS
ingress/kubedoctor   nginx   localhost,kubedoctor.local   ...       80
```

#### Step 3: Connect to KubeDoctor (No Port-Forward Needed!)

##### A. Connect via Interactive CLI
```bash
# Windows PowerShell
$env:KUBEDOCTOR_URL = "http://localhost/sse"
uv run python src/kubedoctor/client.py

# Linux / macOS
export KUBEDOCTOR_URL="http://localhost/sse"
uv run python src/kubedoctor/client.py
```

##### B. Connect via Claude Desktop / AI IDEs
Add directly to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "kubedoctor": {
      "url": "http://localhost/sse"
    }
  }
}
```

*(Note: If your cluster does not have an Ingress controller, you can still connect using `kubectl port-forward -n kubedoctor svc/kubedoctor 8000:8000` and setting `KUBEDOCTOR_URL=http://localhost:8000/sse`)*.

---

## Diagnostic Capabilities (16 MCP Tools)

Both modes provide the exact same full suite of 16 diagnostic tools:

| Tool Name | Scope | Description |
|---|---|---|
| `cluster_health` | Cluster | Evaluates all nodes for Readiness, MemoryPressure, DiskPressure, and PIDPressure. |
| `node_health` | Cluster | Detailed condition breakdown for every node in the cluster. |
| `list_pods` | Namespace | Lists all pods in the target namespace with their current phase. |
| `namespace_overview` | Namespace | High-level summary of Pod counts, Services, and Deployments. |
| `namespace_health_scan`| Namespace | **Full cluster scan**: detects crashing, failing, pending, and unready workloads. |
| `diagnose_pod` | Workload | Deep inspection of pod containers, termination codes, waiting reasons, and conditions. |
| `doctor` | Workload | **Master Diagnostic Engine**: aggregates container state, logs, and events into a root-cause summary. |
| `get_pod_logs` | Workload | Fetches real-time tail logs for any container. |
| `get_pod_events` | Workload | Retrieves filtered Kubernetes events associated with a pod. |
| `detect_crashloops` | Workload | Pinpoints containers stuck in `CrashLoopBackOff` or high restart frequencies. |
| `detect_image_pull_errors` | Workload | Detects `ImagePullBackOff` and `ErrImagePull` registry/secret failures. |
| `detect_pending_pods` | Workload | Identifies unscheduled pods and missing node resources. |
| `diagnose_deployment` | Workload | Analyzes desired vs. available vs. ready replicas and detects stuck rollouts. |
| `diagnose_service` | Network | Inspects service ports and checks for active backend endpoints. |
| `diagnose_ingress` | Network | Validates ingress rules, hostnames, and routing backends. |
| `pod_events` | Workload | Detailed event timeline with occurrence counts and timestamps. |

---

## Interactive CLI Commands Reference

When running `python src/kubedoctor/client.py`, the following commands are available:

```text
Commands:
  health                          Check overall cluster health
  node-health                     Check node readiness and pressure
  pods [namespace]                List pods in a namespace
  scan [namespace]                Full health scan across all pods
  crashes [namespace]             Detect CrashLoopBackOff pods
  pending [namespace]             Detect pods stuck in Pending
  images [namespace]              Detect image pull errors
  logs <pod> [namespace]          Get pod logs (last 100 lines)
  events <pod> [namespace]        Get events for a pod
  doctor <pod> [namespace]        Full diagnosis for a specific pod
  deployment <name> [namespace]   Diagnose a deployment
  service <name> [namespace]      Diagnose a service and its endpoints
  ingress <name> [namespace]      Diagnose an ingress resource
  overview [namespace]            Namespace-level resource overview
  tools                           List all available MCP tools
  help                            Show help message
  exit                            Quit KubeDoctor
```

---

## Security & RBAC

KubeDoctor is built following the **Principle of Least Privilege**:

- **Strictly Read-Only**: Permissions are restricted to `["get", "list", "watch"]`. KubeDoctor **cannot** create, modify, or delete any cluster resources.
- **Audited Access**: Every query executes through standard Kubernetes API audit logs under the `kubedoctor` ServiceAccount.
- **Safe for AI Assistants**: LLMs interacting with KubeDoctor cannot perform accidental destructive changes.

```yaml
# Helm RBAC specification
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "nodes", "services", "endpoints", "events", "namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses"]
    verbs: ["get", "list", "watch"]
```

---

## Helm Configuration Parameters

The following table lists the configurable parameters in `values.yaml`:

| Parameter | Description | Default |
|---|---|---|
| `replicaCount` | Number of KubeDoctor server replicas | `1` |
| `image.repository` | Docker image repository | `rahuldan98/kubedoctor` |
| `image.tag` | Docker image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service HTTP/SSE port | `8000` |
| `ingress.enabled` | Enable ingress controller record (zero port-forwarding) | `false` |
| `ingress.className`| Ingress controller class name | `nginx` |
| `rbac.create` | Create ClusterRole & Binding | `true` |
| `serviceAccount.create` | Create ServiceAccount | `true` |
| `resources.limits.cpu` | Container CPU limit | `200m` |
| `resources.limits.memory` | Container memory limit | `256Mi` |
| `resources.requests.cpu` | Container CPU request | `100m` |
| `resources.requests.memory`| Container memory request | `128Mi` |

---

## Architecture

```
+-------------------------------------------------------------+
|                       MCP Clients                           |
|     Claude Desktop  |  Cursor  |  CLI  |  Slackbot / CI     |
+------------------------------+------------------------------+
                               |  JSON-RPC 2.0 (stdio or SSE)
+------------------------------v------------------------------+
|                  KubeDoctor Server (FastMCP)                 |
|  +--------------------+ +------------------+ +-----------+  |
|  | Cluster Diagnostics| |Workload Analysis | | Networking|  |
|  +--------------------+ +------------------+ +-----------+  |
+------------------------------+------------------------------+
                               |  In-Cluster / Kubeconfig Auth
+------------------------------v------------------------------+
|                   Kubernetes API Server                     |
+-------------------------------------------------------------+
```

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.

---

## Author & Maintainer

**Rahul Dan**  
Cloud Platform & DevOps Engineer  
Email: [rahuldan98@gmail.com](mailto:rahuldan98@gmail.com)