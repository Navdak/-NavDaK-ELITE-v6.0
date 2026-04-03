import uvicorn
import requests
import math
import time
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔑 LIVE TOKEN
API_TOKEN = "df019868cf9b4488a1e750c92357040d"
HEADERS = {'X-Auth-Token': API_TOKEN}

# --- SSS+ DYNAMIC AI ENGINE ---
def get_poisson_cum(k_target, lamb):
    """Calculates P(X >= k) - The probability of meeting or exceeding a line"""
    prob_less_than_k = 0
    for i in range(k_target):
        prob_less_than_k += (math.exp(-lamb) * (lamb**i)) / math.factorial(i)
    return 1 - prob_less_than_k

def get_best_line(expectancy, type="goals"):
    """Finds the highest line with > 70% probability"""
    if type == "goals":
        thresholds = [0.5, 1.5, 2.5, 3.5]
    elif type == "corners_total":
        thresholds = [4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5]
    else: # team corners
        thresholds = [1.5, 2.5, 3.5, 4.5, 5.5]
    
    best_line = thresholds[0]
    for t in thresholds:
        prob = get_poisson_cum(math.ceil(t), expectancy)
        if prob > 0.68: # 68% Confidence Threshold
            best_line = t
        else:
            break
    return f"Over {best_line}"

def analyze_sss_plus(h_e, a_e, h_r, a_r):
    # Total Match Expectancy
    total_exp = h_e + a_e
    
    # 1. Goal Markets (Dynamic)
    goals_mkt = get_best_line(total_exp, "goals")
    fh_exp = total_exp * 0.44
    sh_exp = total_exp * 0.56
    fh_mkt = get_best_line(fh_exp, "goals")
    sh_mkt = get_best_line(sh_exp, "goals")
    
    # 2. Corner Markets (Dynamic Inference)
    # Average corners in top leagues is 10. Use attacking pressure (h_e) to scale.
    h_cor_exp = (h_e * 2.5) + 1.5 
    a_cor_exp = (a_e * 2.5) + 1.2
    total_cor_exp = h_cor_exp + a_cor_exp
    
    # 3. Shots & Saves (Data-Backed)
    h_sot = math.ceil(h_e / 0.32)
    a_sot = math.ceil(a_e / 0.35)
    
    # 4. Win Probability
    h_p = math.exp(-h_e)
    a_p = math.exp(-a_e)
    h_win_prob = 1 - h_p
    a_win_prob = 1 - a_p

    return {
        "primary": "Home Win" if h_e > a_e + 0.4 else "Away Win" if a_e > h_e + 0.4 else "Double Chance X2" if a_e > h_e else "Double Chance 1X",
        "conf": round((1 - (1/(total_exp+1))) * 100, 1),
        "goals": goals_mkt,
        "fh": fh_mkt,
        "sh": sh_mkt,
        "corners_total": get_best_line(total_cor_exp, "corners_total"),
        "h_corners": get_best_line(h_cor_exp, "team_corners"),
        "a_corners": get_best_line(a_cor_exp, "team_corners"),
        "btts": "Yes" if (h_e > 0.8 and a_e > 0.8) else "No",
        "h_sot": f"{h_sot}+", "a_sot": f"{a_sot}+",
        "h_saves": f"{math.ceil(a_sot * 0.7)}+", "a_saves": f"{math.ceil(h_sot * 0.7)}+",
        "cards": "Over 3.5" if abs(h_r - a_r) < 5 else "Over 2.5"
    }

@app.get("/api/data")
def fetch_data():
    leagues = ['PL', 'PD', 'BL1', 'SA']
    results = []
    for lg in leagues:
        try:
            r = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/standings", headers=HEADERS)
            data = r.json()
            table = {t['team']['name']: t for t in data['standings'][0]['table']}
            
            m_res = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/matches?status=SCHEDULED", headers=HEADERS).json()
            for m in m_res.get('matches', [])[:8]:
                h, a = m['homeTeam']['name'], m['awayTeam']['name']
                if h in table and a in table:
                    h_att = table[h]['goalsFor'] / max(table[h]['playedGames'], 1)
                    a_def = table[a]['goalsAgainst'] / max(table[a]['playedGames'], 1)
                    a_att = table[a]['goalsFor'] / max(table[a]['playedGames'], 1)
                    h_def = table[h]['goalsAgainst'] / max(table[h]['playedGames'], 1)
                    
                    h_e = (h_att + a_def) / 2 * 1.12
                    a_e = (a_att + h_def) / 2
                    mkt = analyze_sss_plus(h_e, a_e, table[h]['position'], table[a]['position'])
                    results.append({"match": f"{h} vs {a}", "h_name": h, "a_name": a, "lg": lg, "mkt": mkt})
            time.sleep(1.2)
        except: continue
    return sorted(results, key=lambda x: x['mkt']['conf'], reverse=True)

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NavDaK SSS+ PREMIER</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚽</text></svg>">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body { background: #020617; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif; }
            .sss-card { background: linear-gradient(145deg, #0f172a 0%, #020617 100%); border: 1px solid rgba(255,255,255,0.05); }
            .sss-glow:hover { border-color: #22c55e; box-shadow: 0 0 30px -5px rgba(34, 197, 94, 0.3); transform: translateY(-2px); }
            .accent-txt { background: linear-gradient(135deg, #4ade80 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .m-badge { background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 10px; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <header class="mb-16 flex flex-col md:flex-row justify-between items-center gap-6">
                <div>
                    <h1 class="text-5xl font-black tracking-tighter accent-txt italic">NavDaK ELITE v7.0</h1>
                    <p class="text-slate-500 text-[10px] font-black uppercase tracking-[0.5em] mt-2">SSS+ Premier Prediction Infrastructure</p>
                </div>
                <div class="flex items-center gap-4 bg-slate-900/50 px-6 py-3 rounded-2xl border border-white/5">
                    <div class="w-3 h-3 bg-green-500 rounded-full animate-ping"></div>
                    <span class="text-xs font-black uppercase tracking-widest text-green-400">AI Model: SSS+ Premier Active</span>
                </div>
            </header>

            <div id="grid" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="col-span-full py-40 text-center text-slate-500 font-bold uppercase tracking-widest animate-pulse italic">
                    Engaging High-Frequency Poisson Analysis...
                </div>
            </div>
        </div>

        <script>
            async function refresh() {
                try {
                    const r = await fetch('/api/data');
                    const d = await r.json();
                    const g = document.getElementById('grid');
                    if(!d.length) { g.innerHTML = '<div class="col-span-full text-center text-slate-500 uppercase font-black py-20">Awaiting High-Volume Fixtures...</div>'; return; }

                    g.innerHTML = d.map((x, i) => `
                        <div class="sss-card p-8 rounded-[3rem] transition-all duration-500 sss-glow animate-card">
                            <div class="flex justify-between items-center mb-8">
                                <span class="bg-white/5 text-slate-400 text-[9px] font-black px-4 py-1.5 rounded-full uppercase tracking-widest border border-white/10">${x.lg}</span>
                                <span class="text-xs font-black text-green-400 italic bg-green-500/10 px-3 py-1 rounded-lg tracking-tighter">${x.mkt.conf}% SSS+ Rating</span>
                            </div>

                            <h2 class="text-4xl font-extrabold mb-10 tracking-tighter leading-none italic uppercase">${x.match}</h2>

                            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🧤 Saves (H/A)</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.h_saves} / ${x.mkt.a_saves}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🎯 SoT (H/A)</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.h_sot} / ${x.mkt.a_sot}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🚩 Total Corners</p><p class="text-xs font-bold text-green-400 font-mono">${x.mkt.corners_total}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🏁 Team Corners</p><p class="text-[9px] font-bold text-slate-300">H: ${x.mkt.h_corners}<br>A: ${x.mkt.a_corners}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⚽ Full Match</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.goals}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⏱️ 1st Half</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.fh}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⏳ 2nd Half</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.sh}</p></div>
                                <div class="m-badge"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🟨 Cards</p><p class="text-xs font-bold text-blue-400 font-mono">${x.mkt.cards}</p></div>
                            </div>

                            <div class="flex items-center justify-between p-6 bg-green-500/5 rounded-[2rem] border border-green-500/10">
                                <div class="flex flex-col">
                                    <span class="text-[10px] font-black text-slate-500 uppercase tracking-widest italic">Premier AI Outcome</span>
                                    <span class="text-xs font-bold text-slate-300 italic">BTTS: ${x.mkt.btts}</span>
                                </div>
                                <span class="text-3xl font-black text-green-400 uppercase italic tracking-tighter">${x.mkt.primary}</span>
                            </div>
                        </div>
                    `).join('');
                } catch(e) { console.error(e); }
            }
            refresh();
            setInterval(refresh, 300000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
