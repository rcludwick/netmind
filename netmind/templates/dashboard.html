<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetMind | TCP Debugger</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: 'Courier New', monospace; }
        .tx { color: #4ade80; } /* Green */
        .rx { color: #60a5fa; } /* Blue */
        .semantic { color: #fbbf24; font-weight: bold; }
        .scroll-container { height: calc(100vh - 200px); overflow-y: auto; }
        tr:hover { background-color: #1e293b; }
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto">
        <header class="flex justify-between items-center mb-6 border-b border-gray-700 pb-4">
            <div>
                <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">NetMind</h1>
                <p class="text-sm text-gray-400">Model Context Protocol & TCP Debugger</p>
            </div>
            <div class="flex gap-2">
                <span id="status" class="px-3 py-1 bg-red-900 text-red-200 rounded-full text-xs uppercase font-bold tracking-wider">Disconnected</span>
            </div>
        </header>

        <div class="grid grid-cols-12 gap-6">
            <!-- Sidebar: Active Proxies -->
            <div class="col-span-3 bg-slate-800 p-4 rounded-lg border border-slate-700 h-fit">
                <h2 class="text-xl font-semibold mb-4 text-white">Active Proxies</h2>
                <div id="proxy-list" class="space-y-3">
                    {% for proxy in proxies %}
                    <div class="p-3 bg-slate-900 rounded border border-slate-700">
                        <div class="font-bold text-cyan-400">{{ proxy.name }}</div>
                        <div class="text-xs text-gray-500">{{ proxy.local_port }} &rarr; {{ proxy.target_host }}:{{ proxy.target_port }}</div>
                        <div class="text-xs text-yellow-500 mt-1 uppercase">{{ proxy.protocol }}</div>
                    </div>
                    {% else %}
                    <p class="text-gray-500 italic text-sm">No active proxies. Use the MCP client to add one.</p>
                    {% endfor %}
                </div>
            </div>

            <!-- Main: Packet Log -->
            <div class="col-span-9 bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div class="flex justify-between mb-4">
                    <h2 class="text-xl font-semibold">Live Traffic</h2>
                    <button onclick="document.getElementById('log-body').innerHTML=''" class="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded">Clear Log</button>
                </div>
                
                <div class="scroll-container bg-slate-950 rounded border border-slate-800 p-2">
                    <table class="w-full text-left text-sm">
                        <thead class="text-gray-500 border-b border-gray-800 sticky top-0 bg-slate-950">
                            <tr>
                                <th class="p-2 w-24">Time</th>
                                <th class="p-2 w-32">Proxy</th>
                                <th class="p-2 w-16">Dir</th>
                                <th class="p-2">Payload (Text / Semantic)</th>
                                <th class="p-2 w-48 font-mono">Hex</th>
                            </tr>
                        </thead>
                        <tbody id="log-body">
                            <!-- Packets injected here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/monitor`);
        const statusEl = document.getElementById('status');
        const logBody = document.getElementById('log-body');

        ws.onopen = () => {
            statusEl.innerText = "Live";
            statusEl.className = "px-3 py-1 bg-green-900 text-green-200 rounded-full text-xs uppercase font-bold tracking-wider";
        };

        ws.onclose = () => {
            statusEl.innerText = "Offline";
            statusEl.className = "px-3 py-1 bg-red-900 text-red-200 rounded-full text-xs uppercase font-bold tracking-wider";
        };

        ws.onmessage = (event) => {
            const pkt = JSON.parse(event.data);
            const row = document.createElement('tr');
            
            const timeStr = new Date(pkt.timestamp * 1000).toLocaleTimeString().split(' ')[0];
            const dirClass = pkt.direction === 'TX' ? 'tx' : 'rx';
            const arrow = pkt.direction === 'TX' ? '→' : '←';
            
            // Highlight Hamlib commands
            let content = pkt.data_str;
            if (pkt.semantic) {
                content = `<span class="semantic">${pkt.semantic}</span> <span class="text-gray-600 text-xs">(${pkt.data_str.trim()})</span>`;
            }

            row.innerHTML = `
                <td class="p-2 text-gray-500 font-mono text-xs">${timeStr}</td>
                <td class="p-2 text-gray-300 font-semibold">${pkt.proxy_name}</td>
                <td class="p-2 ${dirClass} font-bold">${arrow} ${pkt.direction}</td>
                <td class="p-2 text-gray-300 font-mono whitespace-pre-wrap">${content}</td>
                <td class="p-2 text-gray-600 font-mono text-xs truncate max-w-xs" title="${pkt.data_hex}">${pkt.data_hex}</td>
            `;
            
            logBody.prepend(row); // Newest first
            
            // Limit DOM size
            if (logBody.children.length > 500) {
                logBody.removeChild(logBody.lastChild);
            }
        };
    </script>
</body>
</html>