import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from fredapi import Fred
from dotenv import load_dotenv
import unicodedata

## import xml.etree.ElementTree as ET

from google.cloud import bigquery

load_dotenv()

# NOTA: Para correr este script, a máquina precisa de ter as credenciais do Google Cloud configuradas.
bq_client = bigquery.Client(project="forecast-crew-academic")

HEADERS = {"User-Agent": "ForecastCrewAcademic/1.0 (academic research project)"}

def limpar_nome(nome):
    return unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8').replace(' ', '_')

def fetch_fred_series(series_id, realtime_start):
    fred = Fred(api_key=os.getenv("FRED_API_KEY"))
    try:
        df = fred.get_series_all_releases(series_id)
        df['realtime_start'] = pd.to_datetime(df['realtime_start'])
        df_filtrado = df[df['realtime_start'] <= pd.to_datetime(realtime_start)]
        
        if not df_filtrado.empty:
            ultima = df_filtrado.sort_values('date').iloc[-1]
            return {"data": str(ultima['date'].date()), "valor": ultima['value'], "pub": str(ultima['realtime_start'].date()) + " (vintage)"}
            
        serie = fred.get_series(series_id, observation_end=realtime_start).dropna()
        if not serie.empty:
            return {"data": str(serie.index[-1].date()), "valor": serie.iloc[-1], "pub": realtime_start + " (standard)"}
        return None
    except Exception:
        try:
            serie = fred.get_series(series_id, observation_end=realtime_start).dropna()
            if not serie.empty:
                return {"data": str(serie.index[-1].date()), "valor": serie.iloc[-1], "pub": realtime_start + " (standard)"}
        except: pass
        return None

def fetch_wikipedia_revision(title, cutoff_date, lang="en"):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "prop": "revisions", "titles": title,
        "rvlimit": 1, "rvdir": "older", "rvstart": f"{cutoff_date}T00:00:00Z",
        "rvprop": "ids|timestamp|content", "rvslots": "main", "format": "json"
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        data = r.json()
        for page in data["query"]["pages"].values():
            if "revisions" in page:
                return {"revid": page["revisions"][0]["revid"], "content": page["revisions"][0]["slots"]["main"]["*"][:4000]}
    except: pass
    return None

def fetch_gdelt_events(query, country, start_date, end_date):
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    dt_start = dt_end - timedelta(days=60)
    
    palavras = []
    for p in query.split():
        p_limpo = p.strip().lower()
        if p_limpo == "usa":
            p_limpo = "us"
        if len(p_limpo) >= 2:
            palavras.append(p_limpo)
            
    condicoes_or = " OR ".join([f"LOWER(DocumentIdentifier) LIKE '%{p}%'" for p in palavras])
    
    # Soma +1 por cada palavra encontrada no URL para ordenar pelos artigos mais relevantes primeiro
    score_relevancia = " + ".join([f"(CASE WHEN LOWER(DocumentIdentifier) LIKE '%{p}%' THEN 1 ELSE 0 END)" for p in palavras])
    
    # Filtra pelo país na coluna de localizações do GDELT (ex: #FR#, #US#, #SY#)
    filtro_pais = f"AND V2Locations LIKE '%#{country}#%'" if country else ""
    
    sql = f"""
        SELECT 
            SUBSTR(CAST(DATE AS STRING), 1, 8) AS data_noticia,
            DocumentIdentifier AS url,
            SourceCommonName AS fonte,
            ({score_relevancia}) AS relevancia
        FROM `gdelt-bq.gdeltv2.gkg_partitioned`
        WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{dt_start.strftime("%Y-%m-%d")}') 
                                 AND TIMESTAMP('{dt_end.strftime("%Y-%m-%d")}')
          AND ({condicoes_or})
          {filtro_pais}
        ORDER BY relevancia DESC, DATE DESC
        LIMIT 10
    """
    
    print(f"   -> A consultar GDELT BigQuery ({dt_start.strftime('%Y-%m-%d')} a {dt_end.strftime('%Y-%m-%d')})...")
    
    try:
        query_job = bq_client.query(sql)
        resultados_bq = query_job.result()
        
        resultados = []
        for row in resultados_bq:
            slug_titulo = row.url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
            # Limpa extensões comuns como .html ou .php do título extraído
            for ext in [".html", ".htm", ".php", ".aspx"]:
                slug_titulo = slug_titulo.replace(ext, "")
                
            titulo_formatado = f"[{row.fonte}] {slug_titulo[:90]}"
            
            resultados.append({
                "titulo": titulo_formatado,
                "data": row.data_noticia,
                "url": row.url
            })
            
        print(f"   ✅ BigQuery devolveu {len(resultados)} registos do GDELT.")
        return resultados
        
    except Exception as e:
        print(f"   ❌ Erro no BigQuery: {e}")
        return None

def main():
    with open("cenarios.json", "r", encoding="utf-8") as f:
        cenarios = json.load(f)

    os.makedirs("dados/evidencia", exist_ok=True)
    manifest = {}
    
    for c in cenarios:
        if not c.get("gerar_evidencia", False):
            continue
            
        nome_ficheiro = f"{limpar_nome(c['pais'])}_{c['ano_referencia']}"
        print(f"\n📡 A recolher evidência para {nome_ficheiro}...")
        
        linhas = [f"# Evidência Histórica: {nome_ficheiro}", f"**Data de corte:** {c['data_corte']}\n", "---\n", "## 1. Dados Económicos (FRED)"]
        
        fred_resultados = {}
        if c.get("fred_series"):
            for nome, sid in c["fred_series"].items():
                print(f"   -> FRED: {nome} ({sid})")
                info = fetch_fred_series(sid, c['data_corte'])
                fred_resultados[nome] = info
                if info: linhas.append(f"- **{nome}:** {info['valor']} (obs: {info['data']}, pub: {info['pub']})")
                else: linhas.append(f"- **{nome}:** (indisponível)")
        else:
            linhas.append("- (Sem séries FRED definidas para este cenário)")
        linhas.append("")

        print(f"   -> Wikipedia: {c['wiki_title']}")
        wiki = fetch_wikipedia_revision(c['wiki_title'], c['data_corte'])
        linhas.append("## 2. Contexto Qualitativo (Wikipedia)")
        if wiki:
            linhas.append(f"*Revisão ID: {wiki['revid']}*\n")
            linhas.append(wiki['content'].replace("\n", " ") + "...\n")
        else:
            linhas.append("(indisponível)\n")

        linhas.append("## 3. Eventos Noticiosos (GDELT)")
        
        ano_corte = int(c['data_corte'][:4])
        if ano_corte < 2017:
            linhas.append("*(GDELT indisponível para datas anteriores a 2017. A análise baseia-se na Wikipedia e FRED.)*\n")
            gdelt = None
        else:
            data_inicio = (datetime.strptime(c['data_corte'], "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
            print(f"   -> GDELT: {c['gdelt_query']}")
            gdelt = fetch_gdelt_events(c['gdelt_query'], c['gdelt_country'], data_inicio, c['data_corte'])
            
            if gdelt is None:
                linhas.append("*(GDELT indisponível por limite de pedidos.)*\n")
            elif len(gdelt) == 0:
                linhas.append("*(Nenhum artigo encontrado.)*\n")
            else:
                for art in gdelt:
                    linhas.append(f"- **{art['data']}:** {art['titulo']} ([link]({art['url']}))")
        
        caminho = f"dados/evidencia/{nome_ficheiro}.md"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))
            
        manifest[nome_ficheiro] = {
            "data_corte": c['data_corte'],
            "fred_series": c.get("fred_series", {}),
            "wiki_revid": wiki["revid"] if wiki else None,
            "gdelt_query": c['gdelt_query'],
            "gdelt_artigos": len(gdelt) if gdelt else 0
        }
        print(f"   ✅ Guardado em {caminho}")
        
    with open("dados/evidencia/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("\n✅ Manifesto de proveniência guardado em dados/evidencia/manifest.json")

if __name__ == "__main__":
    main()
