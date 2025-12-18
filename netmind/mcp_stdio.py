from netmind.app import mcp

def main():
    # Run the MCP server over stdio.
    # IMPORTANT: Do not print anything to stdout here, as it will
    # corrupt the JSON-RPC protocol used by the MCP client.
    mcp.run()

if __name__ == "__main__":
    main()