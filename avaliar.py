import os
import json
import re
import pandas as pd
import numpy as np
from sklearn.metrics import brier_score_loss, log_loss

# Mapeamento dos nomes dos ficheiros para os nomes dos perfis
PERFIS = {
    "01_ortodoxo.md": "Ortodoxo",
    "02_marxista.md": "Marxista",
    "03_social_democrata.md": "Social-Democrata",
    "04_libertario.md": "Libertário",
    "05_base_rates.md": "Base Rates",
    "07_agregacao.md": "Redator (Agregação)"
}

def extrair_dados():
    """Lê a pasta de resultados e o JSON para construir o Dataframe Mestre."""
    dados = []
    
    if not os.path.exists("resultados"):
        print("❌ Pasta 'resultados' não encontrada.")
        return pd.DataFrame()

    # Ler a Ground Truth do JSON
    with open("cenarios.json", "r", encoding="utf-8") as f:
        cenarios_json = json.load(f)
    
    ground_truth_map = {f"{c['pais']}_{c['ano_referencia']}": c["ground_truth"] for c in cenarios_json}

    for cenario in os.listdir("resultados"):
        caminho_cenario = os.path.join("resultados", cenario)
        if not os.path.isdir(caminho_cenario):
            continue
            
        if cenario not in ground_truth_map:
            continue
            
        realidade = ground_truth_map[cenario]
        
        # Ignorar cenários pendentes no cálculo do Brier Score
        if realidade == "pendente" or realidade == "":
            print(f"⏭️  A ignorar '{cenario}' no cálculo do Brier (Realidade: pendente).")
            continue
            
        realidade = int(realidade)
        
        for ficheiro, nome_perfil in PERFIS.items():
            caminho_ficheiro = os.path.join(caminho_cenario, ficheiro)
            if os.path.exists(caminho_ficheiro):
                with open(caminho_ficheiro, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                    
                match = re.search(r"ESTIMATIVA_FINAL:\s*(\d+)", conteudo)
                if match:
                    prob = int(match.group(1)) / 100.0
                    dados.append({
                        "Cenario": cenario,
                        "Perfil": nome_perfil,
                        "Probabilidade": prob,
                        "Realidade": realidade
                    })
    
    return pd.DataFrame(dados)

def calcular_bootstrap(df, perfil, metrica_func, n_iter=1000):
    df_perfil = df[df["Perfil"] == perfil]
    if len(df_perfil) < 2:
        return (metrica_func(df_perfil), metrica_func(df_perfil))
        
    scores = []
    for _ in range(n_iter):
        amostra = df_perfil.sample(n=len(df_perfil), replace=True)
        scores.append(metrica_func(amostra))
    return np.percentile(scores, 2.5), np.percentile(scores, 97.5)

def avaliar():
    print("📊 A carregar dados e a calcular métricas...\n")
    df = extrair_dados()
    
    if df.empty:
        print("❌ Nenhum dado válido encontrado para avaliar (apenas cenários pendentes ou sem resultados).")
        return

    df.to_csv("dataframe_mestre.csv", index=False)
    print(f"✅ Dataframe Mestre guardado ({len(df)} previsões válidas).\n")

    resultados_leaderboard = []
    classes_possiveis = [0, 1]

    for perfil in df["Perfil"].unique():
        df_perfil = df[df["Perfil"] == perfil]
        
        probs = df_perfil["Probabilidade"].values
        probs_clip = np.clip(probs, 1e-15, 1 - 1e-15)
        reais = df_perfil["Realidade"].values
        probs_2d = np.vstack([1 - probs_clip, probs_clip]).T
        
        brier = brier_score_loss(reais, probs_clip, pos_label=1)
        brier_ic = calcular_bootstrap(df, perfil, lambda d: brier_score_loss(d["Realidade"], np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15), pos_label=1))
        
        logloss = log_loss(reais, probs_2d, labels=classes_possiveis)
        logloss_ic = calcular_bootstrap(df, perfil, lambda d: log_loss(
            d["Realidade"], np.vstack([1 - np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15), np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15)]).T, labels=classes_possiveis))
        
        previsao_binaria = (df_perfil["Probabilidade"] > 0.5).astype(int)
        acerto_direcional = (previsao_binaria == reais).mean()
        
        resultados_leaderboard.append({
            "Perfil": perfil,
            "Brier Score ↓": round(brier, 4),
            "Brier IC 95%": f"[{round(brier_ic[0], 3)} - {round(brier_ic[1], 3)}]",
            "Log Loss ↓": round(logloss, 4),
            "Log Loss IC 95%": f"[{round(logloss_ic[0], 3)} - {round(logloss_ic[1], 3)}]",
            "Acerto Direcional ↑": f"{acerto_direcional * 100:.1f}%"
        })

    df_leaderboard = pd.DataFrame(resultados_leaderboard)
    df_leaderboard = df_leaderboard.sort_values(by="Brier Score ↓", ascending=True)
    
    print("="*80)
    print("🏆 LEADERBOARD FINAL (Ordenado por Brier Score)")
    print("="*80)
    print(df_leaderboard.to_string(index=False))
    print("="*80)

if __name__ == "__main__":
    avaliar()