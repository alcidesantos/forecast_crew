import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()

CENARIOS = {
    "Franca_2018": {
        "data_corte": "2018-10-01",
        "fred_series": {
            "Taxa de Desemprego": "LRHUTTTTFRM156S",
            "PIB (crescimento %)": "CLVMNACSCAB1GQFR",
            "Inflação (IPC)": "CP0000FRM086NEST"
        },
        "wiki_title": "Economy of France",
        "gdelt_query": "protest tax fuel",
        "gdelt_country": "FR"
    },
    "Ucrania_2013": {
        "data_corte": "2013-10-01",
        "fred_series": {
            "PIB (crescimento %)": "UKRNGDPRSAXDCQ",
            "Taxa de Desemprego": "LRHUTTTTUAM156S"
        },
        "wiki_title": "Economy of Ukraine",
        "gdelt_query": "EU Russia protest",
        "gdelt_country": "UA"
    },
    "EUA_2007": {
        "data_corte": "2007-10-01",
        "fred_series": {
            "Taxa de Desemprego": "UNRATE",
            "PIB (crescimento %)": "A191RL1Q225SBEA",
            "Índice Case-Shiller": "CSUSHPINSA"
        },
        "wiki_title": "Economy of the United States",
        "gdelt_query": "subprime housing crisis",
        "gdelt_country": "US"
    }
}

HEADERS = {"User-Agent": "ForecastCrewAcademic/1.0 (academic research project)"}

def fetch_fred_series(series_id, realtime_start):
    fred = Fred(api_key=os.getenv("FRED_API_KEY"))
    try:
        # 1. Tenta ALFRED (vintage)
        df = fred.get_series_all_releases(series_id)
        df['realtime_start'] = pd.to_datetime(df['realtime_start'])
        df_filtrado = df[df['realtime_start'] <= pd.to_datetime(realtime_start)]
        
        if not df_filtrado.empty:
            ultima = df_filtrado.sort_values('date').iloc[-1]
            return {
                "data_observacao": str(ultima['date'].date()),
                "valor": ultima['value'],
                "realtime_start": str(ultima['realtime_start'].date()) + " (vintage)",
                "series_id": series_id
            }
            
        # 2. Se não houver vintage, tenta a série standard (sem ALFRED)
        print(f"  ℹ️ Sem dados vintage para {series_id}. A tentar série standard...")
        serie = fred.get_series(series_id, observation_end=realtime_start)
        serie = serie.dropna()
        if not serie.empty:
            return {
                "data_observacao": str(serie.index[-1].date()),
                "valor": serie.iloc[-1],
                "realtime_start": realtime_start + " (standard)",
                "series_id": series_id
            }
        return None
        
    except Exception as e:
        # Se o ALFRED falhar (ex: série não existe no arquivo), tenta a standard
        try:
            serie = fred.get_series(series_id, observation_end=realtime_start)
            serie = serie.dropna()
            if not serie.empty:
                return {
                    "data_observacao": str(serie.index[-1].date()),
                    "valor": serie.iloc[-1],
                    "realtime_start": realtime_start + " (standard)",
                    "series_id": series_id
                }
        except:
            pass
        print(f"  ⚠️ FRED falhou para {series_id}: {e}")
        return None

def fetch_wikipedia_revision(title, cutoff_date, lang="en"):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvlimit": 1,
        "rvdir": "older",
        "rvstart": f"{cutoff_date}T00:00:00Z",
        "rvprop": "ids|timestamp|content|user",
        "rvslots": "main",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        data = r.json()
        pages = data["query"]["pages"]
        for page in pages.values():
            if "revisions" in page:
                rev = page["revisions"][0]
                return {
                    "revid": rev["revid"],
                    "timestamp": rev["timestamp"],
                    "user": rev.get("user", "N/A"),
                    "content": rev["slots"]["main"]["*"][:5000]
                }
        return None
    except Exception as e:
        print(f"  ⚠️ Wikipedia falhou para '{title}': {e}")
        return None

def fetch_gdelt_events(query, country, start_date, end_date):
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f"{query} sourcecountry:{country}",
        "mode": "artlist",
        "maxrecords": "10",
        "startdatetime": f"{start_date.replace('-', '')}000000",
        "enddatetime": f"{end_date.replace('-', '')}235959",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code == 429:
            print("  ⚠️ GDELT bloqueou (429). A ignorar esta fonte para este cenário.")
            return None # None indica que falhou por bloqueio
        if r.status_code != 200:
            print(f"  ⚠️ GDELT HTTP {r.status_code}")
            return None
        data = r.json()
        artigos = data.get("articles", [])
        return [
            {"titulo": a.get("title", ""), "data": a.get("seendate", ""), "url": a.get("url", "")}
            for a in artigos
        ]
    except Exception as e:
        print(f"  ⚠️ GDELT falhou (talvez sem resultados): {e}")
        return None

def compilar_markdown(nome_cenario, dados):
    linhas = [f"# Evidência Histórica: {nome_cenario}", f"**Data de corte:** {dados['data_corte']}\n", "---\n"]
    
    linhas.append("## 1. Dados Económicos (FRED/ALFRED)")
    for nome, info in dados["fred"].items():
        if info:
            linhas.append(f"- **{nome}:** {info['valor']} (obs: {info['data_observacao']}, pub: {info['realtime_start']})")
        else:
            linhas.append(f"- **{nome}:** (dados indisponíveis)")
    linhas.append("")
    
    linhas.append("## 2. Contexto Qualitativo (Wikipedia)")
    wiki = dados["wiki"]
    if wiki:
        linhas.append(f"*Artigo: {dados['wiki_title']} | Revisão ID: {wiki['revid']}*\n")
        texto_limpo = wiki["content"].replace("\n", " ").strip()
        linhas.append(texto_limpo[:2000] + "...\n")
    else:
        linhas.append("(contexto Wikipedia indisponível)\n")
        
    linhas.append("## 3. Eventos Noticiosos (GDELT)")
    gdelt = dados["gdelt"]
    if gdelt is None:
        linhas.append("*(GDELT temporariamente indisponível por limite de pedidos. A análise baseia-se nas fontes 1 e 2.)*\n")
    elif gdelt:
        linhas.append(f"*{len(gdelt)} artigos encontrados.*\n")
        for art in gdelt:
            linhas.append(f"- **{art['data'][:8]}:** {art['titulo']} ([link]({art['url']}))")
    else:
        linhas.append("(Sem resultados para a query no GDELT)\n")
    return "\n".join(linhas)

def main():
    os.makedirs("dados/evidencia", exist_ok=True)
    manifest = {}
    for nome, config in CENARIOS.items():
        print(f"\n📡 A recolher evidência para {nome}...")
        data_corte = config["data_corte"]
        
        fred_resultados = {}
        for nome_indicador, series_id in config["fred_series"].items():
            print(f"   -> FRED: {nome_indicador} ({series_id})")
            fred_resultados[nome_indicador] = fetch_fred_series(series_id, data_corte)
            
        print(f"   -> Wikipedia: {config['wiki_title']}")
        wiki_resultado = fetch_wikipedia_revision(config["wiki_title"], data_corte)
        
        data_inicio = (datetime.strptime(data_corte, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
        print(f"   -> GDELT: {config['gdelt_query']} ({data_inicio} a {data_corte})")
        gdelt_resultado = fetch_gdelt_events(config["gdelt_query"], config["gdelt_country"], data_inicio, data_corte)
        
        dados = {
            "data_corte": data_corte, "fred": fred_resultados, "wiki": wiki_resultado,
            "wiki_title": config["wiki_title"], "gdelt": gdelt_resultado, "gdelt_query": config["gdelt_query"]
        }
        
        caminho = f"dados/evidencia/{nome}.md"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(compilar_markdown(nome, dados))
            
        manifest[nome] = {
            "data_corte": data_corte, "fred_series": config["fred_series"],
            "wiki_revid": wiki_resultado["revid"] if wiki_resultado else None,
            "gdelt_artigos": len(gdelt_resultado) if gdelt_resultado else 0
        }
        print(f"   ✅ Guardado em {caminho}")
        
    with open("dados/evidencia/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("\n✅ Manifesto guardado em dados/evidencia/manifest.json")

if __name__ == "__main__":
    main()