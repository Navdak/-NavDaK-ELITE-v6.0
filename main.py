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

# --- NAVDAK PROPRIETARY AI ENGINE ---
def get_poisson(k, lamb):
    if lamb <= 0: return 0.0001
    return (math.exp(-lamb) * (lamb**k)) / math.factorial(k)

def analyze_elite_markets(h_e, a_e, h_r, a_r):
    h_win, a_win, draw = 0, 0, 0
    o25, btts_total = 0, 0
    h_p = [get_poisson(i, h_e) for i in range(6)]
    a_p = [get_poisson(j, a_e) for j in range(6)]
    
    for i in range(6):
        for j in range(6):
            p = h_p[i] * a_p[j]
            if i > j: h_win += p
            elif i < j: a_win += p
            else: draw += p
            if (i+j) > 2.5: o25 += p
            if i > 0 and j > 0: btts_total += p

    # --- ADVANCED STATISTICAL INFERENCE ---
    # SoT is calculated based on Attacking Pressure (Goals/0.31 conversion rate)
    h_sot_calc = math.ceil(h_e / 0.31)
    a_sot_calc = math.ceil(a_e / 0.34)
    
    # Saves are calculated based on Opponent Shots OT x Save Percentage (Avg 72%)
    h_saves_calc = math.ceil(a_sot_calc * 0.72)
    a_saves_calc = math.ceil(h_sot_calc * 0.72)

    return {
        "primary": "Home Win" if h_win > a_win else "Away Win" if a_win > h_win else "Draw",
        "conf": round(max(h_win, a_win, draw) * 100, 1),
        "goals": "Over 2.5" if o25 > 0.52 else "Under 2.5",
        "btts": "Yes" if btts_total > 0.55 else "No",
        "h_sot": f"{h_sot_calc}+",
        "a_sot": f"{a_sot_calc}+",
        "h_saves": f"{h_saves_calc}+",
        "a_saves": f"{a_saves_calc}+",
        "corners": "Over 9.5" if (h_e + a_e) > 2.45 else "Under 9.5",
        "cards": "Over 3.5" if abs(h_r - a_r) < 6 else "Under 3.5"
    }

@app.get("/api/data")
def fetch_data():
    leagues = ['PL', 'PD', 'BL1']
    results = []
    for lg in leagues:
        try:
            response = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/standings", headers=HEADERS)
            s_data = response.json()
            if 'standings' not in s_data: continue
            
            table = {t['team']['name']: t for t in s_data['standings'][0]['table']}
            m_res = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/matches?status=SCHEDULED", headers=HEADERS).json()
            
            for m in m_res.get('matches', [])[:8]:
                h, a = m['homeTeam']['name'], m['awayTeam']['name']
                if h in table and a in table:
                    # Calculating Goal Expectancy from Table Data
                    h_attack = table[h]['goalsFor'] / max(table[h]['playedGames'], 1)
                    a_defense = table[a]['goalsAgainst'] / max(table[a]['playedGames'], 1)
                    a_attack = table[a]['goalsFor'] / max(table[a]['playedGames'], 1)
                    h_defense = table[h]['goalsAgainst'] / max(table[h]['playedGames'], 1)

                    h_e = (h_attack + a_defense) / 2 * 1.15 # Home Advantage Multiplier
                    a_e = (a_attack + h_defense) / 2
                    
                    mkt = analyze_elite_markets(h_e, a_e, table[h]['position'], table[a]['position'])
                    results.append({
                        "match": f"{h} vs {a}", 
                        "h_team": h, "a_team": a, 
                        "lg": lg, "mkt": mkt
                    })
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
        <title>NavDaK ELITE v6.0</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚽</text></svg>">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body { background: #030712; color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; }
            .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.05); }
            .navdak-text { background: linear-gradient(135deg, #22c55e 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .stat-box { background: rgba(2, 6, 23, 0.6); border: 1px solid rgba(255,255,255,0.03); border-radius: 16px; padding: 12px; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-6xl mx-auto">
            <header class="mb-12 text-center md:text-left">
                <h1 class="text-5xl font-extrabold tracking-tighter navdak-text">NavDaK ELITE v6.0</h1>
                <p class="text-slate-500 text-xs font-bold uppercase tracking-widest mt-2 italic underline decoration-green-500">Professional Prediction Infrastructure</p>
            </header>

            <div id="grid" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="col-span-full py-20 text-center animate-pulse text-slate-500 font-bold uppercase tracking-widest">
                    Initializing Neural Network & Standings Data...
                </div>
            </div>
        </div>

        <script>
            async function load() {
                try {
                    const r = await fetch('/api/data');
                    const d = await r.json();
                    const container = document.getElementById('grid');
                    
                    if(!d || d.length === 0) {
                        container.innerHTML = `<div class="col-span-full glass p-20 rounded-3xl text-center text-slate-500 font-bold">Scanning Fixtures...</div>`;
                        return;
                    }

                    container.innerHTML = d.map(x => `
                        <div class="glass p-8 rounded-[2.5rem] border border-white/5 hover:border-green-500/40 transition-all duration-500">
                            <div class="flex justify-between items-start mb-6">
                                <span class="bg-blue-600/10 text-blue-400 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest border border-blue-500/20">${x.lg}</span>
                                <span class="text-xl font-black text-white italic">${x.mkt.conf}% Confidence</span>
                            </div>
                            <h2 class="text-3xl font-black mb-8 tracking-tighter italic leading-none">${x.match}</h2>
                            
                            <div class="grid grid-cols-2 md:grid-cols-2 gap-4 mb-8">
                                <div class="stat-box">
                                    <p class="text-[9px] text-slate-500 font-bold uppercase mb-2 underline decoration-blue-500">Saves Prediction</p>
                                    <p class="text-sm font-bold">Home: <span class="text-green-400">${x.mkt.h_saves}</span></p>
                                    <p class="text-sm font-bold">Away: <span class="text-green-400">${x.mkt.a_saves}</span></p>
                                </div>
                                <div class="stat-box">
                                    <p class="text-[9px] text-slate-500 font-bold uppercase mb-2 underline decoration-blue-500">Shots on Target</p>
                                    <p class="text-sm font-bold">Home: <span class="text-green-400">${x.mkt.h_sot}</span></p>
                                    <p class="text-sm font-bold">Away: <span class="text-green-400">${x.mkt.a_sot}</span></p>
                                </div>
                                <div class="stat-box flex justify-between items-center px-4">
                                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter italic">Goals</span>
                                    <span class="text-sm font-black text-green-400 uppercase">${x.mkt.goals}</span>
                                </div>
                                <div class="stat-box flex justify-between items-center px-4">
                                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter italic">Corners</span>
                                    <span class="text-sm font-black text-green-400 uppercase">${x.mkt.corners}</span>
                                </div>
                            </div>

                            <div class="flex items-center justify-between p-5 bg-green-500/5 rounded-2xl border border-green-500/10">
                                <span class="text-xs font-black text-slate-400 uppercase tracking-tighter">Elite AI Outcome</span>
                                <span class="text-2xl font-black text-green-400 uppercase italic tracking-tighter">${x.mkt.primary}</span>
                            </div>
                        </div>
                    `).join('');
                } catch(e) {
                    document.getElementById('grid').innerHTML = `<div class="col-span-full text-center text-red-500">API Connection Error - Please Wait...</div>`;
                }
            }
            load();
            setInterval(load, 180000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
