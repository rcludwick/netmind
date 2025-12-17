
try:
    import mcp.client.sse
    print("mcp.client.sse found")
except ImportError:
    print("mcp.client.sse NOT found")

try:
    from mcp.client.sse import sse_client
    print("sse_client found")
except ImportError:
    print("sse_client NOT found")
