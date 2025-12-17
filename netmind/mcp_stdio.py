from watchfiles import run_process
from netmind.app import mcp

def run_mcp():
    """Target function to run the MCP server."""
    # We need to re-import or re-run mcp.run() in the new process
    mcp.run()

def main():
    print("Starting MCP server with file watching enabled...")
    run_process('.', target=run_mcp)

if __name__ == "__main__":
    main()
