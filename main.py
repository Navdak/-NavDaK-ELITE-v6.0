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

# --- NAVDAK ELITE AI ENGINE ---
def get_poisson(k, lamb):
    if lamb <= 0: return 0.0001
    return (math.exp(-lamb) * (lamb**k)) / math.factorial(k)

def analyze_elite_markets(h_e, a_e, h_r, a_r):
    h_win, a_win, draw = 0, 0, 0
    o25, btts_p = 0, 0
    fh_o05, sh_o05 = 0, 0
    
    # Probabilities for Goals (0 to 5)
    h_p = [get_poisson(i, h_e) for i in range(6)]
    a_p = [get_poisson(j, a_e) for j in range(6)]
    
    for i in range(6):
        for j in range(6):
            p = h_p[i] * a_p[j]
            if i > j: h_win += p
            elif i < j: a_win += p
            else: draw += p
            if (i+j) > 2.5: o25 += p
            if i > 0 and j > 0: btts_p += p

    # --- TEMPORAL SPLIT (FH/SH) ---
    # Statistically FH = 45% of total goals, SH = 55%
    fh_exp = (h_e + a_e) * 0.45
    sh_exp = (h_e + a_e) * 0.55
    fh_o05 = 1 - get_poisson(0, fh_exp)
    sh_o05 = 1 - get_poisson(0, sh_exp)

    # --- PROPS & INTENSITY ---
    h_sot = math.ceil(h_e / 0.31)
    a_sot = math.ceil(a_e / 0.34)
    h_saves = math.ceil(a_sot * 0.72)
    a_saves = math.ceil(h_sot * 0.72)

    return {
        "primary": "Home Win" if h_win > a_win else "Away Win" if a_win > h_win else "Draw",
        "conf": round(max(h_win, a_win, draw) * 100, 1),
        "goals": "Over 2.5" if o25 > 0.52 else "Under 2.5",
        "fh": "Over 0.5" if fh_o05 > 0.62 else "Under 0.5",
        "sh": "Over 0.5" if sh_o05 > 0.68 else "Under 0.5",
        "btts": "Yes" if btts_p > 0.55 else "No",
        "h_sot": f"{h_sot}+", "a_sot": f"{a_sot}+",
        "h_saves": f"{h_saves}+", "a_saves": f"{a_saves}+",
        "corners": "Over 9.5" if (h_e + a_e) > 2.4 else "Under 9.5",
        "cards": "Over 3.5" if abs(h_r - a_r) < 6 else "Under 3.5"
    }

@app.get("/api/data")
def fetch_data():
    leagues = ['PL', 'PD', 'BL1']
    results = []
    for lg in leagues:
        try:
            r = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/standings", headers=HEADERS)
            data = r.json()
            if 'standings' not in data: continue
            table = {t['team']['name']: t for t in data['standings'][0]['table']}
            
            m_res = requests.get(f"https://api.football-data.org/v4/competitions/{lg}/matches?status=SCHEDULED", headers=HEADERS).json()
            for m in m_res.get('matches', [])[:8]:
                h, a = m['homeTeam']['name'], m['awayTeam']['name']
                if h in table and a in table:
                    h_att = table[h]['goalsFor'] / max(table[h]['playedGames'], 1)
                    a_def = table[a]['goalsAgainst'] / max(table[a]['playedGames'], 1)
                    a_att = table[a]['goalsFor'] / max(table[a]['playedGames'], 1)
                    h_def = table[h]['goalsAgainst'] / max(table[h]['playedGames'], 1)
                    
                    h_e = (h_att + a_def) / 2 * 1.15
                    a_e = (a_att + h_def) / 2
                    mkt = analyze_elite_markets(h_e, a_e, table[h]['position'], table[a]['position'])
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
        <title>NavDaK ELITE v6.0</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚽</text></svg>">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body { background: #030712; color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; }
            .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
            .navdak-accent { background: linear-gradient(135deg, #22c55e 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .m-card { background: rgba(2, 6, 23, 0.4); border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; padding: 12px; }
            @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            .animate-card { animation: slideUp 0.6s ease-out forwards; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-6xl mx-auto">
            <header class="mb-12 flex flex-col md:flex-row justify-between items-center gap-6">
                <div class="text-center md:text-left">
                    <h1 class="text-5xl font-extrabold tracking-tighter navdak-accent">NavDaK ELITE v6.0</h1>
                    <p class="text-slate-500 text-xs font-bold uppercase tracking-[0.3em] mt-2 italic">Professional Sports Prediction Bot</p>
                </div>
                <div class="flex items-center gap-3 glass px-4 py-2 rounded-full border-green-500/20">
                    <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    <span class="text-[10px] font-black text-green-400 uppercase tracking-widest">Live Engine</span>
                </div>
            </header>

            <div id="grid" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="col-span-full py-40 text-center text-slate-500 font-bold uppercase tracking-widest animate-pulse">Syncing Standings & AI Neural Networks...</div>
            </div>
        </div>

        <script>
            async function load() {
                try {
                    const r = await fetch('/api/data');
                    const d = await r.json();
                    const g = document.getElementById('grid');
                    if(!d.length) { g.innerHTML = '<div class="col-span-full glass p-20 rounded-3xl text-center uppercase tracking-widest text-slate-500">Awaiting weekend fixtures...</div>'; return; }

                    g.innerHTML = d.map((x, i) => `
                        <div class="glass p-8 rounded-[2.5rem] border border-white/5 hover:border-green-500/40 transition-all duration-500 animate-card" style="animation-delay: ${i*0.1}s">
                            <div class="flex justify-between items-center mb-6">
                                <span class="bg-blue-600/10 text-blue-400 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest border border-blue-500/20">${x.lg}</span>
                                <span class="text-xl font-black text-white italic">${x.mkt.conf}% Confidence</span>
                            </div>
                            <h2 class="text-3xl font-extrabold mb-10 tracking-tight leading-none italic">${x.match}</h2>
                            
                            <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-10">
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🧤 Saves (H/A)</p><p class="text-xs font-bold text-green-400">${x.mkt.h_saves} / ${x.mkt.a_saves}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🎯 SoT (H/A)</p><p class="text-xs font-bold text-green-400">${x.mkt.h_sot} / ${x.mkt.a_sot}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⚽ Full Time</p><p class="text-xs font-bold text-green-400">${x.mkt.goals}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⏱️ 1st Half</p><p class="text-xs font-bold text-green-400">${x.mkt.fh}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">⏳ 2nd Half</p><p class="text-xs font-bold text-green-400">${x.mkt.sh}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🔄 BTTS</p><p class="text-xs font-bold text-green-400">${x.mkt.btts}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🚩 Corners</p><p class="text-xs font-bold text-green-400">${x.mkt.corners}</p></div>
                                <div class="m-card text-center"><p class="text-[8px] text-slate-500 uppercase font-black mb-1">🟨 Cards</p><p class="text-xs font-bold text-green-400">${x.mkt.cards}</p></div>
                            </div>

                            <div class="flex items-center justify-between p-5 bg-green-500/5 rounded-2xl border border-green-500/10">
                                <span class="text-xs font-black text-slate-400 uppercase tracking-tighter italic">Elite Pick</span>
                                <span class="text-2xl font-black text-green-400 uppercase italic tracking-tighter">${x.mkt.primary}</span>
                            </div>
                        </div>
                    `).join('');
                } catch(e) { console.error(e); }
            }
            load();
            setInterval(load, 240000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
