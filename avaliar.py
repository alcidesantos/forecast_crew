import os
import re
import pandas as pd
import numpy as np
from sklearn.metrics import brier_score_loss, log_loss

# =====================================================================
# 1. DEFINIÇÃO DA GROUND TRUTH (A Realidade Histórica)
# =====================================================================
# Aqui defines o que realmente aconteceu em cada cenário.
# 1 = O evento ocorreu | 0 = O evento não ocorreu
# Nota: Para a França 2018, os Gilets Jaunes ocorreram, logo = 1.
GROUND_TRUTH = {
    "Franca_2018": 1,
    "Ucrania_2013": 1,
    "EUA_2007": 1
}

# Mapeamento dos nomes dos ficheiros para os nomes dos perfis
PERFIS = {
    "01_estimativa_ortodoxa.md": "Ortodoxo",
    "02_estimativa_marxista.md": "Marxista",
    "03_estimativa_social_democrata.md": "Social-Democrata",
    "04_estimativa_libertario.md": "Libertário",
    "05_estimativa_base_rates.md": "Base Rates",
    "06_relatorio_agregacao.md": "Redator (Agregação)"
}

def extrair_dados():
    """Lê a pasta de resultados e constrói o Dataframe Mestre."""
    dados = []
    
    if not os.path.exists("resultados"):
        print("❌ Pasta 'resultados' não encontrada.")
        return pd.DataFrame()

    for cenario in os.listdir("resultados"):
        caminho_cenario = os.path.join("resultados", cenario)
        if not os.path.isdir(caminho_cenario):
            continue
            
        if cenario not in GROUND_TRUTH:
            print(f"⚠️  Cenário '{cenario}' não tem Ground Truth definida. A ignorar.")
            continue
            
        realidade = GROUND_TRUTH[cenario]
        
        for ficheiro, nome_perfil in PERFIS.items():
            caminho_ficheiro = os.path.join(caminho_cenario, ficheiro)
            if os.path.exists(caminho_ficheiro):
                with open(caminho_ficheiro, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                    
                # Extrai o número (ex: ESTIMATIVA_FINAL: 80)
                match = re.search(r"ESTIMATIVA_FINAL:\s*(\d+)", conteudo)
                if match:
                    prob = int(match.group(1)) / 100.0  # Converte para 0.0 - 1.0
                    dados.append({
                        "Cenario": cenario,
                        "Perfil": nome_perfil,
                        "Probabilidade": prob,
                        "Realidade": realidade
                    })
    
    return pd.DataFrame(dados)

def calcular_bootstrap(df, perfil, metrica_func, n_iter=1000):
    """Calcula o Intervalo de Confiança (95%) via Bootstrap para uma métrica."""
    df_perfil = df[df["Perfil"] == perfil]
    if len(df_perfil) < 2:
        # Se só há 1 cenário, não há variância para o Bootstrap
        return (metrica_func(df_perfil), metrica_func(df_perfil))
        
    scores = []
    for _ in range(n_iter):
        # Reamostragem com reposição
        amostra = df_perfil.sample(n=len(df_perfil), replace=True)
        scores.append(metrica_func(amostra))
        
    return np.percentile(scores, 2.5), np.percentile(scores, 97.5)

def avaliar():
    print("📊 A carregar dados e a calcular métricas...\n")
    df = extrair_dados()
    
    if df.empty:
        print("❌ Nenhum dado válido encontrado para avaliar.")
        return

    # Guardar o dataframe mestre para consulta
    df.to_csv("dataframe_mestre.csv", index=False)
    print(f"✅ Dataframe Mestre guardado em 'dataframe_mestre.csv' ({len(df)} previsões).\n")

    resultados_leaderboard = []
    classes_possiveis = [0, 1] # Força o sklearn a considerar ambas as classes

    for perfil in df["Perfil"].unique():
        df_perfil = df[df["Perfil"] == perfil]
        
        # Evitar log(0) no Log Loss
        probs = df_perfil["Probabilidade"].values
        probs_clip = np.clip(probs, 1e-15, 1 - 1e-15)
        reais = df_perfil["Realidade"].values
        
        # Para o log_loss, o scikit-learn precisa das probabilidades para AMBAS as classes [P(0), P(1)]
        probs_2d = np.vstack([1 - probs_clip, probs_clip]).T
        
        # 1. Brier Score
        brier = brier_score_loss(reais, probs_clip, pos_label=1)
        brier_ic = calcular_bootstrap(df, perfil, lambda d: brier_score_loss(d["Realidade"], np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15), pos_label=1))
        
        # 2. Log Loss (Corrigido com 'labels' e 'probs_2d')
        logloss = log_loss(reais, probs_2d, labels=classes_possiveis)
        logloss_ic = calcular_bootstrap(df, perfil, lambda d: log_loss(
            d["Realidade"], 
            np.vstack([1 - np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15), np.clip(d["Probabilidade"], 1e-15, 1 - 1e-15)]).T, 
            labels=classes_possiveis
        ))
        
        # 3. Acerto Direcional (>50% = 1, <=50% = 0)
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

    # Construir e ordenar o Leaderboard (pelo Brier Score, que é a métrica principal)
    df_leaderboard = pd.DataFrame(resultados_leaderboard)
    df_leaderboard = df_leaderboard.sort_values(by="Brier Score ↓", ascending=True)
    
    print("="*80)
    print("🏆 LEADERBOARD FINAL (Ordenado por Brier Score)")
    print("="*80)
    print(df_leaderboard.to_string(index=False))
    print("="*80)
    print("\nNota: ↓ significa que quanto mais baixo, melhor. ↑ significa quanto mais alto, melhor.")
    print("O Brier Score varia entre 0 (perfeito) e 1 (péssimo).")

if __name__ == "__main__":
    avaliar()