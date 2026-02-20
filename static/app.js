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

function formatTimeSummary(times) {
  if (!times || typeof times !== "object") return "--";

  const london = times.London ?? "--";
  const newYork = times.New_York ?? "--";
  const pk = times.PK ?? "--";
  const tokyo = times.Tokyo ?? "--";
  const utc = times.UTC ?? "--";

  return `
            <div>UTC: ${utc}</div>
            <div>PK: ${pk}</div>
            <div>London: ${london}</div>
            <div>New York: ${newYork}</div>
            <div>Tokyo: ${tokyo}</div>
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

    update("tfMatch", data.tf_match);
    update("tradeDecision", data.trade_decision);
    update("trend1m", data.trends?.["1m"]);
    update("trend5m", data.trends?.["5m"]);
    update("trend15m", data.trends?.["15m"]);

    update("adx1m", data.adx_strength?.["1m"]);
    update("adx5m", data.adx_strength?.["5m"]);
    update("adx15m", data.adx_strength?.["15m"]);

    update("atr1m", data.atr_strength?.["1m"]);
    update("atr5m", data.atr_strength?.["5m"]);
    update("atr15m", data.atr_strength?.["15m"]);

    update("rsi1m", data.rsi_strength?.["1m"]);
    update("rsi5m", data.rsi_strength?.["5m"]);
    update("rsi15m", data.rsi_strength?.["15m"]);

    updateColored("tradeAction", data.trade_action);
    updateText("timeSummary", formatTimeSummary(data.times));
    updateText("tradeSummary", formatSummary(data.summary));
    update("shortAtrTrail", data.ATR_TRAIL_SHORT);
    update("longAtrTrail", data.ATR_TRAIL_LONG);
    update("recentPrice", data.price);
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
    signal.includes("TRAIL") ||
    signal.includes("OVERSOLD")
  )
    return "text-emerald-400 font-semibold";

  if (
    signal.includes("SHORT") ||
    signal.includes("BEAR") ||
    signal.includes("BEARISH") ||
    signal.includes("WEAK") ||
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

setInterval(fetchTrend, 10000);
