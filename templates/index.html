<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Trend Engine Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-white min-h-screen">

<div class="max-w-3xl mx-auto px-6 py-10 flex flex-col space-y-6">

    <h1 class="text-3xl font-bold text-cyan-400">Trend Engine</h1>

    <!-- Symbol Select -->
    <select id="symbolSelect"
        class="bg-slate-800 border border-slate-700 px-4 py-2 rounded-lg text-white w-full">
        <option value="BTCUSDT">BTCUSDT</option>
        <option value="ETHUSDT">ETHUSDT</option>
        <option value="BNBUSDT">BNBUSDT</option>
        <option value="SOLUSDT">SOLUSDT</option>
    </select>

    <!-- Multi TF -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800">
        <h2 class="text-slate-400 mb-2">Multi TF Alignment</h2>
        <p id="tfMatch" class="text-2xl font-bold text-gray-400">Loading...</p>
    </div>

    <!-- Recent Price -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800">
        <h2 class="text-slate-400 mb-2">Recent Price</h2>
        <p id="recentCross" class="text-2xl font-bold text-gray-400">Loading...</p>
    </div>

    <!-- Trend Per TF -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-4">
        <h2 class="text-cyan-400 font-semibold">Trend Per Timeframe</h2>

        <div>
            <p class="text-slate-400">1m</p>
            <p id="trend1m" class="text-xl font-bold">--</p>
        </div>

        <div>
            <p class="text-slate-400">5m</p>
            <p id="trend5m" class="text-xl font-bold">--</p>
        </div>

        <div>
            <p class="text-slate-400">15m</p>
            <p id="trend15m" class="text-xl font-bold">--</p>
        </div>
    </div>
    <!-- ATR Per TF -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-4">
        <h2 class="text-cyan-400 font-semibold">ATR Per Timeframe</h2>

        <div>
            <p class="text-slate-400">1m</p>
            <p id="atr1m" class="text-xl font-bold">--</p>
        </div>

        <div>
            <p class="text-slate-400">5m</p>
            <p id="atr5m" class="text-xl font-bold">--</p>
        </div>

        <div>
            <p class="text-slate-400">15m</p>
            <p id="atr15m" class="text-xl font-bold">--</p>
        </div>
    </div>

    <!-- Times -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-3">
        <h2 class="text-slate-400 mb-2">Times</h2>

        <div>
            <p class="text-slate-400">UTC</p>
            <p id="timeUTC" class="text-xl font-mono">--</p>
        </div>

        <div>
            <p class="text-slate-400">London</p>
            <p id="timeLondon" class="text-xl font-mono">--</p>
        </div>

        <div>
            <p class="text-slate-400">New York</p>
            <p id="timeNY" class="text-xl font-mono">--</p>
        </div>

        <div>
            <p class="text-slate-400">Pakistan</p>
            <p id="timePK" class="text-xl font-mono">--</p>
        </div>

        <div>
            <p class="text-slate-400">Tokyo</p>
            <p id="timeTokyo" class="text-xl font-mono">--</p>
        </div>
    </div>

    <!-- Trade Status -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-2">
        <h2 class="text-cyan-400 font-semibold mb-2">Trade Status</h2>
        <p id="tradeAction" class="text-xl font-bold text-gray-400">Loading...</p>
        <p id="tradeSummary" class="text-gray-400 text-sm font-mono">Loading...</p>
    </div>

    <!-- Signal History -->
    <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-2">
        <h2 class="text-cyan-400 font-semibold mb-2">Signal History</h2>
        <div id="signalHistory" class="text-gray-400 text-sm font-mono max-h-64 overflow-y-auto"></div>
    </div>

</div>

<script>
const select = document.getElementById("symbolSelect");

/* ---------------- COOKIE HELPERS ---------------- */
function setCookie(name, value, days = 7) {
    const d = new Date();
    d.setTime(d.getTime() + (days*24*60*60*1000));
    document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
}

function getCookie(name) {
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        const [key, val] = c.trim().split('=');
        if (key === name) return val;
    }
    return null;
}

/* ---------------- FETCH DATA ---------------- */
async function fetchTrend() {
    try {
        const symbol = getCookie("symbol") || "BTCUSDT";
        const res = await fetch(`/api/trend?symbol=${symbol}`);
        const data = await res.json();

        // Multi-TF Alignment
        update("tfMatch", data.tf_match);

        // Trends per timeframe
        update("trend1m", data.trends?.["1m"]);
        update("trend5m", data.trends?.["5m"]);
        update("trend15m", data.trends?.["15m"]);

        // ATR per timeframe
        update("atr1m", data.atr_strength?.["1m"]);
        update("atr5m", data.atr_strength?.["5m"]);
        update("atr15m", data.atr_strength?.["15m"]);



        // Times
        if (data.times) {
            // Times
            update("timeUTC", data.times.UTC);
            update("timeLondon", data.times.London);
            update("timeNY", data.times?.New_York);
            update("timePK", data.times?.PK);
            update("timeTokyo", data.times?.Tokyo);
        }

        // Trade action & summary
        updateColored("tradeAction", data.trade_action);
        updateText("tradeSummary", formatSummary(data.summary));


        // Save signal history (only 1m crosses)
        addToHistory(data.recent_cross, data.symbol, data.price);

        // Current price
        update("recentCross", data.price);

    } catch (err) {
        console.log("API Error:", err);
    }
}

/* ---------------- UPDATE ELEMENTS ---------------- */
function update(id, value) {
    const el = document.getElementById(id);
    el.textContent = value || "NO DATA";
    el.className = getColor(value);
}

function updateText(id, value) {
    const el = document.getElementById(id);
    el.textContent = value || "--";
}

function updateColored(id, value) {
    const el = document.getElementById(id);
    el.textContent = value || "--";
    el.className = getColor(value);
}

function getColor(signal) {
    if (!signal) return "text-gray-400 text-xl font-bold";
    if (signal.includes("LONG") || signal.includes("BULL")) return "text-green-400 text-xl font-bold";
    if (signal.includes("SHORT") || signal.includes("BEAR")) return "text-red-400 text-xl font-bold";
    if (signal.includes("Closed")) return "text-gray-400 text-xl font-bold";
    return "text-gray-400 text-xl font-bold";
}

function formatSummary(summary) {
    if (!summary) return "--";
    return `Position: ${summary.current_position}, Size: ${summary.position_size}, Signal: ${summary.signal}`;
}

/* ---------------- SIGNAL HISTORY ---------------- */
function addToHistory(recent1m, symbol, price) {
    if (recent1m == null) return;

    const log = `${recent1m} ${symbol} ${price}`;
    let history = JSON.parse(localStorage.getItem("signalHistory") || "[]");

    const now = new Date();
    const timestamp = `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;

    history.push({ "1m Cross": log, time: timestamp });
    if (history.length > 50) history.shift();

    localStorage.setItem("signalHistory", JSON.stringify(history));
    renderHistory();
}

function renderHistory() {
    const historyDiv = document.getElementById("signalHistory");
    const history = JSON.parse(localStorage.getItem("signalHistory") || "[]");

    historyDiv.innerHTML = history
        .map(h => `[${h.time}] 1m Cross: ${h["1m Cross"]}`)
        .map(line => `<div>${line}</div>`)
        .join("");
}

/* ---------------- INIT ---------------- */
window.addEventListener("load", () => {
    const saved = getCookie("symbol");
    if (saved) select.value = saved;
    else setCookie("symbol", select.value);

    renderHistory();
    fetchTrend();
});

/* Change symbol -> update cookie */
select.addEventListener("change", () => setCookie("symbol", select.value));

/* Watch cookie and reload if changed */
let lastSymbol = getCookie("symbol");
setInterval(() => {
    const current = getCookie("symbol");
    if (current !== lastSymbol) location.reload();
}, 1000);

/* Auto refresh data */
setInterval(fetchTrend, 30000);
</script>

</body>
</html>
