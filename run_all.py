import json
import os
import unicodedata
from src.forecast_crew.crew import ForecastCrew

def limpar_nome(nome):
    return unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8').replace(' ', '_')

def main():
    with open("cenarios.json", "r", encoding="utf-8") as f:
        cenarios = json.load(f)

    for c in cenarios:
        if not c.get("ativo", False):
            continue

        pasta_destino = os.path.join("resultados", f"{c['pais']}_{c['ano_referencia']}")
        ficheiro_final = os.path.join(pasta_destino, "07_agregacao.md")

        # === A MÁGICA ACONTECE AQUI ===
        # Se o ficheiro final já existir, salta o cenário (poupa tempo e dinheiro)
        if os.path.exists(ficheiro_final):
            print(f"⏭️  A saltar {c['pais']} {c['ano_referencia']} (já tem resultados guardados).")
            continue

        print(f"\n{'='*50}\nA INICIAR CENÁRIO: {c['pais']} {c['ano_referencia']}\n{'='*50}")
        
        caminho_evidencia = f"dados/evidencia/{c['pais']}_{c['ano_referencia']}.md"
        try:
            with open(caminho_evidencia, "r", encoding="utf-8") as f:
                pacote_evidencia = f.read()
        except FileNotFoundError:
            print(f"❌ Ficheiro {caminho_evidencia} não encontrado. Salta o cenário.")
            continue

        inputs = {
            'pais': c['pais'],
            'ano_referencia': c['ano_referencia'],
            'horizonte': '1 ano',
            'tipo_evento': c['tipo_evento'],
            'pacote_evidencia': pacote_evidencia
        }

        result = ForecastCrew().crew().kickoff(inputs=inputs)

        os.makedirs(pasta_destino, exist_ok=True)
        
        ficheiros = [
            "00_evidencia.md", "01_ortodoxo.md", "02_marxista.md", 
            "03_social_democrata.md", "04_libertario.md", 
            "05_base_rates.md", "06_auditor.md", "07_agregacao.md"
        ]
        
        for i, task_output in enumerate(result.tasks_output):
            if i < len(ficheiros):
                with open(os.path.join(pasta_destino, ficheiros[i]), "w", encoding="utf-8") as f:
                    f.write(task_output.raw)

        # Leakage Probe
        leak = False
        for output in result.tasks_output:
            for termo in c['termos_proibidos']:
                if termo.lower() in output.raw.lower():
                    print(f"⚠️ LEAKAGE DETETADO no cenário {c['pais']}: '{termo}'")
                    leak = True
        if not leak:
            print(f"✅ Leakage Probe ({c['pais']}): Limpo.")

if __name__ == "__main__":
    main()