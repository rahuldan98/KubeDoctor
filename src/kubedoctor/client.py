import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================================================
# Connection mode
#
#   Local (default):
#       No env var needed. Spawns server.py as a subprocess via stdio.
#
#   In-cluster (Helm):
#       Set KUBEDOCTOR_URL to the server SSE endpoint, e.g.:
#           $env:KUBEDOCTOR_URL = "http://localhost:8000/sse"
#       (after: kubectl port-forward svc/kubedoctor 8000:8000 -n kubedoctor)
# ============================================================

KUBEDOCTOR_URL = os.getenv("KUBEDOCTOR_URL")

server_params = StdioServerParameters(
    command="uv",
    args=[
        "run",
        "python",
        "src/kubedoctor/server.py",
    ],
    cwd=str(PROJECT_ROOT),
)


async def call_tool(session, tool_name, arguments=None):

    if arguments is None:
        arguments = {}

    try:

        result = await session.call_tool(
            tool_name,
            arguments,
        )

        for content in result.content:

            if hasattr(content, "text"):
                print(content.text)

    except Exception as e:

        print(f"\nError calling tool: {e}")


def print_help():
    print("""
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
  help                            Show this help message
  exit                            Quit KubeDoctor
""")


def parse_namespace(parts, index=1, default="default"):
    """Extract namespace from command parts, falling back to default."""
    return parts[index] if len(parts) > index else default


async def _run_repl(session: ClientSession) -> None:
    """Shared REPL loop - works identically for both stdio and HTTP modes."""

    await session.initialize()

    print("\n================================")
    print("       KUBEDOCTOR")
    print("================================")
    print("MCP server connected.")
    print_help()

    while True:

        command = input("KubeDoctor> ").strip()

        if not command:
            continue

        parts = command.split()
        cmd = parts[0]

        # ------------------------------------------------
        # exit
        # ------------------------------------------------

        if cmd == "exit":
            print("Goodbye!")
            break

        # ------------------------------------------------
        # help
        # ------------------------------------------------

        elif cmd == "help":
            print_help()

        # ------------------------------------------------
        # health
        # ------------------------------------------------

        elif cmd == "health":

            await call_tool(session, "cluster_health")

        # ------------------------------------------------
        # node-health
        # ------------------------------------------------

        elif cmd == "node-health":

            await call_tool(session, "node_health")

        # ------------------------------------------------
        # pods [namespace]
        # ------------------------------------------------

        elif cmd == "pods":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "list_pods",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # scan [namespace]
        # ------------------------------------------------

        elif cmd == "scan":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "namespace_health_scan",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # crashes [namespace]
        # ------------------------------------------------

        elif cmd == "crashes":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "detect_crashloops",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # pending [namespace]
        # ------------------------------------------------

        elif cmd == "pending":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "detect_pending_pods",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # images [namespace]
        # ------------------------------------------------

        elif cmd == "images":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "detect_image_pull_errors",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # logs <pod> [namespace]
        # ------------------------------------------------

        elif cmd == "logs":

            if len(parts) < 2:
                print("Usage: logs <pod> [namespace]")
                continue

            pod_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "get_pod_logs",
                {
                    "pod_name": pod_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # events <pod> [namespace]
        # ------------------------------------------------

        elif cmd == "events":

            if len(parts) < 2:
                print("Usage: events <pod> [namespace]")
                continue

            pod_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "pod_events",
                {
                    "pod_name": pod_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # doctor <pod> [namespace]
        # ------------------------------------------------

        elif cmd == "doctor":

            if len(parts) < 2:
                print("Usage: doctor <pod> [namespace]")
                continue

            pod_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "doctor",
                {
                    "pod_name": pod_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # deployment <name> [namespace]
        # ------------------------------------------------

        elif cmd == "deployment":

            if len(parts) < 2:
                print("Usage: deployment <name> [namespace]")
                continue

            deployment_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "diagnose_deployment",
                {
                    "deployment_name": deployment_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # service <name> [namespace]
        # ------------------------------------------------

        elif cmd == "service":

            if len(parts) < 2:
                print("Usage: service <name> [namespace]")
                continue

            service_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "diagnose_service",
                {
                    "service_name": service_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # ingress <name> [namespace]
        # ------------------------------------------------

        elif cmd == "ingress":

            if len(parts) < 2:
                print("Usage: ingress <name> [namespace]")
                continue

            ingress_name = parts[1]
            namespace = parse_namespace(parts, index=2)

            await call_tool(
                session,
                "diagnose_ingress",
                {
                    "ingress_name": ingress_name,
                    "namespace": namespace,
                },
            )

        # ------------------------------------------------
        # overview [namespace]
        # ------------------------------------------------

        elif cmd == "overview":

            namespace = parse_namespace(parts)

            await call_tool(
                session,
                "namespace_overview",
                {"namespace": namespace},
            )

        # ------------------------------------------------
        # tools
        # ------------------------------------------------

        elif cmd == "tools":

            tools = await session.list_tools()

            print("\nAvailable MCP tools:")

            for tool in tools.tools:
                print(f"  - {tool.name}")

            print()

        # ------------------------------------------------
        # unknown
        # ------------------------------------------------

        else:

            print(
                f"Unknown command: '{cmd}'. "
                "Type 'help' to see all commands."
            )


async def main():

    if KUBEDOCTOR_URL:

        # ------------------------------------------------
        # HTTP/SSE mode — connect to in-cluster server
        # ------------------------------------------------

        print(f"Connecting to KubeDoctor server at {KUBEDOCTOR_URL} ...")

        async with sse_client(KUBEDOCTOR_URL) as (read, write):

            async with ClientSession(read, write) as session:

                await _run_repl(session)

    else:

        # ------------------------------------------------
        # stdio mode — spawn server locally (default)
        # ------------------------------------------------

        print("Starting KubeDoctor MCP server...")

        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await _run_repl(session)


if __name__ == "__main__":
    asyncio.run(main())
