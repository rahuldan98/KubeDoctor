import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]


server_params = StdioServerParameters(
    command="uv",
    args=[
        "run",
        "mcp",
        "run",
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


async def main():

    print("Starting KubeDoctor MCP server...")

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\n================================")
            print("       KUBEDOCTOR")
            print("================================")
            print("MCP server connected.")
            print()
            print("Commands:")
            print("  health")
            print("  pods")
            print("  node-health")
            print("  doctor <pod> <namespace>")
            print("  tools")
            print("  exit")
            print()

            while True:

                command = input("KubeDoctor> ").strip()

                if not command:
                    continue

                if command == "exit":
                    print("Goodbye!")
                    break

                elif command == "health":

                    await call_tool(
                        session,
                        "cluster_health",
                    )

                elif command == "pods":

                    namespace = input(
                        "Namespace [default]: "
                    ).strip()

                    if not namespace:
                        namespace = "default"

                    await call_tool(
                        session,
                        "list_pods",
                        {
                            "namespace": namespace
                        },
                    )

                elif command == "node-health":

                    await call_tool(
                        session,
                        "node_health",
                    )

                elif command.startswith("doctor "):

                    parts = command.split()

                    if len(parts) < 2:

                        print(
                            "Usage: doctor <pod> [namespace]"
                        )
                        continue

                    pod_name = parts[1]

                    namespace = (
                        parts[2]
                        if len(parts) > 2
                        else "default"
                    )

                    await call_tool(
                        session,
                        "doctor",
                        {
                            "pod_name": pod_name,
                            "namespace": namespace,
                        },
                    )

                elif command == "tools":

                    tools = await session.list_tools()

                    print("\nAvailable tools:")

                    for tool in tools.tools:
                        print(
                            f"- {tool.name}"
                        )

                    print()

                else:

                    print(
                        "Unknown command. "
                        "Type 'tools' or use one of the commands above."
                    )


if __name__ == "__main__":
    asyncio.run(main())