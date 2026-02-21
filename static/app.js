const select = document.getElementById("symbolSelect");

function setCookie(name, value, days = 7) {
  const d = new Date();
  d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
}

function getCookie(name) {
  const cookies = document.cookie.split(";");
  for (let c of cookies) {
    const [key, val] = c.trim().split("=");
    if (key === name) return val;
  }
  return null;
}

function formatSummary(summary) {
  if (!summary) return "--";
  return `Position: ${summary.current_position}, Size: ${summary.position_size}, Signal: ${summary.signal}`;
}

function formatTimeSummary(data) {
    if (!data || typeof data !== "object") return "--";

    const times = data.current_times ?? {};
    const sessions = data.sessions ?? {};

    const utc = times.UTC ?? "--";
    const pk = times.PK ?? "--";
    const tokyoTime = times.Tokyo ?? "--";
    const londonTime = times.London ?? "--";
    const newYorkTime = times.New_York ?? "--";

    // Helper function to format session info
    const formatSession = (session) => {
        if (!session) return "--";
        if (typeof session === "string") return session;
        if (typeof session === "object") return `High: ${session.high}, Low: ${session.low}`;
        return "--";
    };

    return `
      <div class="bg-slate-900 text-white p-6 rounded-xl shadow-lg space-y-4 w-80">
        <div class="text-sm">
          <strong>UTC:</strong> <span class="text-indigo-400">${utc}</span>
        </div>
        <div class="text-sm">
          <strong>PK:</strong> <span class="text-green-400">${pk}</span>
        </div>

        <hr class="border-slate-700">

        <div class="text-sm">
          <strong>Tokyo:</strong> <span class="text-yellow-300">${tokyoTime}</span>
          <br/>
          <span class="text-slate-400">(${formatSession(sessions.Tokyo)})</span>
        </div>

        <div class="text-sm">
          <strong>London:</strong> <span class="text-blue-400">${londonTime}</span>
          <br/>
          <span class="text-slate-400">(${formatSession(sessions.London)})</span>
        </div>

        <div class="text-sm">
          <strong>New York:</strong> <span class="text-red-400">${newYorkTime}</span>
          <br/>
          <span class="text-slate-400">(${formatSession(sessions.New_York)})</span>
        </div>
      </div>
    `;
}
function updateText(id, value) {
  const el = document.getElementById(id);
  if (!el) return; // element not found, do nothing
  el.innerHTML = value ?? "--"; // use nullish coalescing to handle null/undefined
}

async function fetchTrend() {
  try {
    const symbol = getCookie("symbol") || "BTCUSDT";
    const res = await fetch(`/api/trend?symbol=${symbol}`);
    const data = await res.json();

    // update("tfMatch", data.tf_match);
    update("tradeDecision", data.trade_decision);
    update("trend1m", data.trends?.["1m"]);
    update("trend5m", data.trends?.["5m"]);
    update("trend15m", data.trends?.["15m"]);

    update("adx1m", data.adx_strength?.["1m"]);
    // update("adx5m", data.adx_strength?.["5m"]);
    // update("adx15m", data.adx_strength?.["15m"]);

    update("ema1m", data.ema_strength?.["1m"]);
    update("vwap1m", data.vwap_strength?.["1m"]);

    update("atr1m", data.atr_strength?.["1m"]);
    // update("atr5m", data.atr_strength?.["5m"]);
    update("atr15m", data.atr_strength?.["15m"]);

    // update("rsi1m", data.rsi_strength?.["1m"]);
    // update("rsi5m", data.rsi_strength?.["5m"]);
    update("rsi15m", data.rsi_strength?.["15m"]);

    updateColored("tradeAction", data.trade_action);
    updateText("timeSummary", formatTimeSummary(data.btc_sessions));
    updateText("tradeSummary", formatSummary(data.summary));
    update("shortAtrTrail", data.ATR_TRAIL_SHORT);
    update("longAtrTrail", data.ATR_TRAIL_LONG);
    update("recentPrice", data.price.toString());
  } catch (err) {
    console.log("API Error:", err);
  }
}

function update(id, value) {
  const el = document.getElementById(id);
  el.textContent = value || "NO DATA";
  el.className = getColor(value);
}

function updateColored(id, value) {
  const el = document.getElementById(id);
  el.textContent = value || "--";
  el.className = getColor(value);
}

function getColor(signal) {
  if (!signal) return "text-slate-400 font-medium";

  if (
    signal.includes("LONG") ||
    signal.includes("BULL") ||
    signal.includes("BULLISH") ||
    signal.includes("STRONG") ||
    signal.includes("ABOVE") ||
    signal.includes("HIGH") ||
    signal.includes("UP") ||
    signal.includes("TRAIL") ||
    signal.includes("OVERSOLD")
  )
    return "text-emerald-400 font-semibold";

  if (
    signal.includes("SHORT") ||
    signal.includes("BEAR") ||
    signal.includes("BEARISH") ||
    signal.includes("WEAK") ||
    signal.includes("BELOW") ||
    signal.includes("LOW") ||
    signal.includes("DOWN") ||
    signal.includes("HIT") ||
    signal.includes("OVERBOUGHT")
  )
    return "text-rose-400 font-semibold";

  return "text-slate-400 font-medium";
}

window.addEventListener("load", () => {
  const saved = getCookie("symbol");
  if (saved) select.value = saved;
  else setCookie("symbol", select.value);

  fetchTrend();
});

select.addEventListener("change", () => {
  setCookie("symbol", select.value);
  fetchTrend();
});

setInterval(fetchTrend, 20000);
