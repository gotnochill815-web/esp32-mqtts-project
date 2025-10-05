#!/usr/bin/env python3
# dashboard.py - Flask dashboard with Chart.js + alert logging + alerts history + CSV download

from flask import Flask, render_template_string, jsonify, request, send_file
import sqlite3
import pandas as pd
from flask_cors import CORS
import numpy as np
import io, csv, time
from datetime import datetime

# ---------- Config ----------
DB = "telemetry.db"          # sqlite file inside cloud/ folder
ANOMALY_WINDOW = 50
ANOMALY_Z_THRESHOLD = 3.0
TEMP_HIGH_THRESHOLD = 40.0      # °C
CURRENT_HIGH_THRESHOLD = 2000.0 # mA

app = Flask(__name__)
CORS(app)

# ---------- Ensure alerts table exists ----------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER,
        ts_str TEXT,
        metric TEXT,
        alert_type TEXT,
        value REAL,
        z REAL,
        threshold REAL,
        mean REAL,
        std REAL,
        info TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ alerts table ready")

init_db()

# ---------- alert logging helper ----------
def log_alert(metric, alert_type, value=None, z=None, mean=None, std=None, info=None, threshold=None):
    """
    Insert a row into the alerts table.
    - metric: e.g. "current_mA" or "temp_c"
    - alert_type: "zscore" or "threshold" or other
    - value: observed numeric value
    - z: z-score (if applicable)
    - mean/std: prior stats (if applicable)
    - info: free text
    - threshold: numeric threshold (optional)
    """
    conn = sqlite3.connect(DB)
    try:
        ts = int(time.time())
        ts_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alerts (ts, ts_str, metric, alert_type, value, z, threshold, mean, std, info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, ts_str, metric, alert_type, value, z, threshold, mean, std, info))
        conn.commit()
    finally:
        conn.close()

# ---------- telemetry helpers ----------
def read_db(limit=50):
    conn = sqlite3.connect(DB)
    try:
        # telemetry table assumed to be present (created by mqtt_to_sqlite.py)
        df = pd.read_sql_query(f"SELECT * FROM telemetry ORDER BY ts DESC LIMIT {limit}", conn)
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        return df.to_dict(orient='records')  # newest-first
    finally:
        conn.close()

def compute_z_score(series):
    # series: list of numeric values (chronological)
    if not series or len(series) < 3:
        return None
    arr = np.array(series[:-1], dtype=float)  # prior values
    last = float(series[-1])
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return None
    z = (last - mean) / std
    return {"z": float(z), "value": last, "mean": mean, "std": std}

# ---------- Web UI template (Chart.js) ----------
TEMPLATE = """
<!doctype html>
<html><head><meta charset="utf-8"><title>ENT Device Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Arial,Helvetica,sans-serif;margin:18px;background:#f6f7fb}
.card{background:#fff;padding:12px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-bottom:12px}
.row{display:flex;gap:16px;flex-wrap:wrap}
.card canvas{background:#fff;border-radius:6px}
#alertBar{display:none;background:#ff5252;color:#fff;padding:10px;border-radius:6px;margin-bottom:12px;font-weight:700}
table{width:100%;border-collapse:collapse}th,td{padding:6px 8px;border-bottom:1px solid #eee;text-align:left;font-size:13px}
th{background:#fafafa}
.small{font-size:12px;color:#666}
</style>
</head><body>
<h2>ENT Device Telemetry</h2>
<div id="alertBar"></div>

<div class="row">
  <div class="card" style="flex:1;min-width:300px">
    <h3>Temperature (last {{limit}})</h3><canvas id="chartTemp" height="120"></canvas><div class="small">High alert when ≥ {{temp_threshold}}°C</div>
  </div>
  <div class="card" style="flex:1;min-width:300px">
    <h3>Current mA (last {{limit}})</h3><canvas id="chartCurrent" height="120"></canvas><div class="small">High alert when ≥ {{current_threshold}} mA</div>
  </div>
  <div class="card" style="flex:1;min-width:300px">
    <h3>Humidity (last {{limit}})</h3><canvas id="chartHum" height="120"></canvas>
  </div>
  <div class="card" style="flex:1;min-width:300px">
    <h3>Voltage V (last {{limit}})</h3><canvas id="chartVolt" height="120"></canvas>
  </div>
</div>

<div class="card">
  <h3>Latest telemetry</h3>
  <div id="tableDiv">Loading...</div>
</div>

<div class="card">
  <h3>Alerts history</h3>
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
    <button id="refreshAlertsLog">Refresh</button>
    <button id="downloadCsv">Download CSV</button>
  </div>
  <div id="alertsLog">Loading...</div>
</div>

<script>
const API_DATA = "/data?limit={{limit}}";
const API_ALERT = "/alerts?window={{window}}&z={{z_threshold}}&limit={{limit}}";
const API_ALERTS_LOG = "/alerts/log?limit=100";

let tempChart, currChart, humChart, voltChart;

function buildCharts(){
  const cfg = (label,color) => ({type:'line',data:{labels:[],datasets:[{label:label,data:[],borderColor:color,pointRadius:0,tension:0.25}]},options:{animation:false,plugins:{legend:{display:false}}}});
  tempChart = new Chart(document.getElementById('chartTemp'), cfg('Temp °C','rgb(220,53,69)'));
  currChart = new Chart(document.getElementById('chartCurrent'), cfg('Current mA','rgb(54,162,235)'));
  humChart  = new Chart(document.getElementById('chartHum'), cfg('Humidity %','rgb(75,192,192)'));
  voltChart = new Chart(document.getElementById('chartVolt'), cfg('Voltage V','rgb(153,102,255)'));
}

function renderTable(rows){
  if(!rows||rows.length==0) return "<i>No rows</i>";
  let html="<table><thead><tr>",fields=['ts','device_id','temp_c','humidity_pct','vibration','current_mA','voltage_v'];
  for(let f of fields) html+="<th>"+f+"</th>";
  html+="</tr></thead><tbody>";
  for(let r of rows){ html+="<tr>"; for(let f of fields){ html+="<td>"+(r[f]===null?'':r[f])+"</td>"} html+="</tr>"}
  html+="</tbody></table>"; return html;
}

function renderAlertsLog(rows){
  if(!rows || rows.length==0) return "<i>No historical alerts</i>";
  let html="<table><thead><tr><th>id</th><th>ts</th><th>metric</th><th>type</th><th>value</th><th>z</th><th>info</th></tr></thead><tbody>";
  for(let r of rows){
    html+="<tr>";
    html+="<td>"+r.id+"</td>";
    html+="<td>"+r.ts_str+"</td>";
    html+="<td>"+(r.metric||"")+"</td>";
    html+="<td>"+(r.alert_type||"")+"</td>";
    html+="<td>"+(r.value==null?"":r.value)+"</td>";
    html+="<td>"+(r.z==null?"":(Math.round(r.z*100)/100))+"</td>";
    html+="<td>"+(r.info||"")+"</td>";
    html+="</tr>";
  }
  html+="</tbody></table>";
  return html;
}

function showAlert(msg){ const bar=document.getElementById('alertBar'); if(!msg){bar.style.display='none';bar.innerText='';return;} bar.style.display='block'; bar.innerText=msg; }

async function refresh(){
  try{
    const resp=await fetch(API_DATA); const j=await resp.json(); const rows=j.rows;
    document.getElementById('tableDiv').innerHTML=renderTable(rows);
    const chron=rows.slice().reverse();
    const labels=chron.map(r=>r.ts);
    tempChart.data.labels=labels; tempChart.data.datasets[0].data=chron.map(r=>r.temp_c); tempChart.update();
    currChart.data.labels=labels; currChart.data.datasets[0].data=chron.map(r=>r.current_mA); currChart.update();
    humChart.data.labels=labels; humChart.data.datasets[0].data=chron.map(r=>r.humidity_pct); humChart.update();
    voltChart.data.labels=labels; voltChart.data.datasets[0].data=chron.map(r=>r.voltage_v); voltChart.update();
  }catch(e){console.error(e)}
}

async function refreshAlerts(){
  try{
    const resp=await fetch(API_ALERT); const j=await resp.json();
    if(j.alerts && j.alerts.length){ const msgs=j.alerts.map(a=> a.metric? `${a.metric.toUpperCase()} anomaly (z=${a.z? a.z.toFixed(2):''} val=${a.value})` : (a.info||'alert')); showAlert(msgs.join(' • ')); }
    else showAlert(null);
  }catch(e){console.error(e)}
}

async function refreshAlertsLog(){
  try{
    const resp=await fetch(API_ALERTS_LOG); const j=await resp.json();
    document.getElementById('alertsLog').innerHTML = renderAlertsLog(j.rows);
  }catch(e){console.error(e)}
}

document.getElementById && (function(){
  buildCharts(); refresh(); refreshAlerts(); refreshAlertsLog();
  setInterval(refresh,3000); setInterval(refreshAlerts,3000);
  document.getElementById('refreshAlertsLog').onclick=refreshAlertsLog;
  document.getElementById('downloadCsv').onclick=()=>{ window.location.href='/alerts/log/download'; };
})();
</script>
</body></html>
"""

# ---------- Flask endpoints ----------
@app.route("/")
def index():
    return render_template_string(TEMPLATE,
                                  limit=50,
                                  window=ANOMALY_WINDOW,
                                  z_threshold=ANOMALY_Z_THRESHOLD,
                                  temp_threshold=TEMP_HIGH_THRESHOLD,
                                  current_threshold=CURRENT_HIGH_THRESHOLD)

@app.route("/data")
def data_endpoint():
    limit = int(request.args.get('limit', 50))
    rows = read_db(limit)
    return jsonify({"rows": rows})

@app.route("/alerts")
def alerts_endpoint():
    """
    Compute z-score and threshold alerts.
    Log any detected alerts into alerts table using log_alert(...)
    Return JSON {alerts: [...]}
    """
    limit = int(request.args.get('limit', 50))
    window = int(request.args.get('window', ANOMALY_WINDOW))
    z_thresh = float(request.args.get('z', ANOMALY_Z_THRESHOLD))

    rows = read_db(limit if limit > window else window + 1)
    chron = list(reversed(rows))  # chronological order

    alerts = []

    def series_for(field):
        vals = [r.get(field) for r in chron if r.get(field) is not None]
        return vals[-(window+1):]  # last window+1 values (so prior + candidate)

    # current_mA z-score
    cur_series = series_for("current_mA")
    cur_res = compute_z_score(cur_series) if len(cur_series) > 1 else None
    if cur_res and abs(cur_res["z"]) > z_thresh:
        alerts.append({"metric": "current_mA", "z": cur_res["z"], "value": cur_res["value"], "mean": cur_res["mean"], "std": cur_res["std"]})
        log_alert("current_mA", "zscore", value=cur_res["value"], z=cur_res["z"], mean=cur_res["mean"], std=cur_res["std"], info=f"z>{z_thresh}")

    # temp_c z-score
    temp_series = series_for("temp_c")
    temp_res = compute_z_score(temp_series) if len(temp_series) > 1 else None
    if temp_res and abs(temp_res["z"]) > z_thresh:
        alerts.append({"metric": "temp_c", "z": temp_res["z"], "value": temp_res["value"], "mean": temp_res["mean"], "std": temp_res["std"]})
        log_alert("temp_c", "zscore", value=temp_res["value"], z=temp_res["z"], mean=temp_res["mean"], std=temp_res["std"], info=f"z>{z_thresh}")

    # threshold checks using latest row (guarding None properly)
    if rows:
        latest = rows[0]

        temp_val = latest.get("temp_c")
        if temp_val is not None and temp_val >= TEMP_HIGH_THRESHOLD:
            alerts.append({"metric": "temp_threshold", "z": None, "value": temp_val, "info": "temp >= threshold"})
            log_alert("temp_c", "threshold", value=temp_val, threshold=TEMP_HIGH_THRESHOLD, info=f">= {TEMP_HIGH_THRESHOLD}")

        current_val = latest.get("current_mA")
        if current_val is not None and current_val >= CURRENT_HIGH_THRESHOLD:
            alerts.append({"metric": "current_threshold", "z": None, "value": current_val, "info": "current >= threshold"})
            log_alert("current_mA", "threshold", value=current_val, threshold=CURRENT_HIGH_THRESHOLD, info=f">= {CURRENT_HIGH_THRESHOLD}")

    return jsonify({"alerts": alerts})

@app.route("/alerts/log")
def alerts_log_endpoint():
    limit = int(request.args.get('limit', 100))
    conn = sqlite3.connect(DB)
    try:
        df = pd.read_sql_query(f"SELECT * FROM alerts ORDER BY ts DESC LIMIT {limit}", conn)
        # ensure ts_str present
        if 'ts_str' not in df.columns and 'ts' in df.columns:
            df['ts_str'] = pd.to_datetime(df['ts'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        rows = df.to_dict(orient='records')
        return jsonify({"rows": rows})
    finally:
        conn.close()

@app.route("/alerts/log/download")
def alerts_log_download():
    conn = sqlite3.connect(DB)
    try:
        df = pd.read_sql_query("SELECT * FROM alerts ORDER BY ts DESC LIMIT 1000", conn)
    finally:
        conn.close()

    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(["id","ts","ts_str","metric","alert_type","value","z","threshold","mean","std","info"])
    for idx, r in df[::-1].iterrows():  # oldest-first
        w.writerow([r.get("id"), r.get("ts"), r.get("ts_str"), r.get("metric"), r.get("alert_type"),
                    r.get("value"), r.get("z"), r.get("threshold"), r.get("mean"), r.get("std"), r.get("info")])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"alerts_{int(time.time())}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)

# ---------- Start server ----------
if __name__ == "__main__":
    print("Starting dashboard with alert logging at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
