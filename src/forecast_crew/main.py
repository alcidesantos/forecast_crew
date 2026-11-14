#!/usr/bin/env python
import sys
import warnings
import os
import unicodedata
import re

from datetime import datetime

from forecast_crew.crew import ForecastCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def _default_inputs() -> dict:
    """Inputs por defeito."""
    return {
        'pais': 'EUA',
        'ano_referencia': '2007',
        'horizonte': '1 ano',
        'tipo_evento': 'uma crise financeira sistémica', 
        'termos_proibidos': ["Lehman Brothers", "Grande Recessão", "resgate bancário", "TARP"]
    ####
    #    'pais': 'Ucrania',
    #    'ano_referencia': '2013',
    #    'horizonte': '1 ano',
    #    'tipo_evento': 'uma guerra ou conflito armado', 
    #    'termos_proibidos': ["Euromaidan", "Crimeia", "Donbass", "Yanukovych fugiu", "Rússia anexou"] # Termos pós-Out/2013
    ####
    #    'pais': 'França',
    #    'ano_referencia': '2018',
    #    'horizonte': '1 ano',
    #    'tipo_evento': 'um levantamento popular ou crise social',
    #    'termos_proibidos': ["gilets jaunes", "coletes amarelos", "novembro de 2018", "Macron cede", "Champs-Élysées"] 
    }

def run():
    """
    Run the crew and save outputs to dedicated folders.
    """
    inputs = _default_inputs()
    
    # 1. LER O PACOTE DE EVIDÊNCIA
    pais_limpo_ficheiro = unicodedata.normalize('NFKD', inputs['pais']).encode('ASCII', 'ignore').decode('utf-8').replace(' ', '_')
    caminho_evidencia = f"dados/evidencia/{pais_limpo_ficheiro}_{inputs['ano_referencia']}.md"
    
    try:
        with open(caminho_evidencia, "r", encoding="utf-8") as f:
            inputs['pacote_evidencia'] = f.read()
        print(f"📄 Evidência carregada de: {caminho_evidencia}")
    except FileNotFoundError:
        raise Exception(f"ERRO: Ficheiro de evidência não encontrado em {caminho_evidencia}.")

    print(f"\n🚀 A iniciar o cenário: {inputs['pais']} em {inputs['ano_referencia']} (Evento: {inputs['tipo_evento']})...\n")

    try:
        # 2. Correr a Crew
        result = ForecastCrew().crew().kickoff(inputs=inputs)
        
        # 3. Preparar os nomes e a pasta de resultados
        pais_limpo = unicodedata.normalize('NFKD', inputs['pais']).encode('ASCII', 'ignore').decode('utf-8').replace(' ', '_')
        pasta_destino = os.path.join("resultados", f"{pais_limpo}_{inputs['ano_referencia']}")
        os.makedirs(pasta_destino, exist_ok=True)
        
        # Lista atualizada para 7 ficheiros (1 evidência + 5 estimativas + 1 agregação)
        ficheiros = [
            "00_pacote_evidencia.md",
            "01_estimativa_ortodoxa.md",
            "02_estimativa_marxista.md",
            "03_estimativa_social_democrata.md",
            "04_estimativa_libertario.md",
            "05_estimativa_base_rates.md",
            "06_relatorio_agregacao.md"
        ]
        
        # 4. Guardar o output e extrair o valor via Regex
        valores_finais = {}
        for i, task_output in enumerate(result.tasks_output):
            if i < len(ficheiros):
                caminho_ficheiro = os.path.join(pasta_destino, ficheiros[i])
                with open(caminho_ficheiro, "w", encoding="utf-8") as f:
                    f.write(task_output.raw)
                
                # Extrair número de todas as estimativas e da agregação (ignorar o ficheiro 0)
                if i > 0:
                    match = re.search(r"ESTIMATIVA_FINAL:\s*(\d+)", task_output.raw)
                    if match:
                        valores_finais[ficheiros[i]] = int(match.group(1))
                    else:
                        valores_finais[ficheiros[i]] = "Não encontrado"
        
        print(f"\n✅ Concluído! Relatórios guardados em: /{pasta_destino}/")
        print("\n📊 Matriz de Estimativas (Regex):")
        for k, v in valores_finais.items():
            print(f"   - {k}: {v}")

        # 5: LEAKAGE PROBE (Verificação de Fuga)
        termos = inputs.get('termos_proibidos', [])
        if termos:
            print("\n🔍 A executar Leakage Probe (Sonda de Fuga de Informação)...")
            leak_detetado = False
            
            for i, task_output in enumerate(result.tasks_output):
                for termo in termos:
                    # Procura o termo no texto (ignorando maiúsculas/minúsculas)
                    if termo.lower() in task_output.raw.lower():
                        print(f"   ⚠️  LEAKAGE DETETADO no ficheiro {ficheiros[i]}! Termo encontrado: '{termo}'")
                        leak_detetado = True
            
            if not leak_detetado:
                print("   ✅ SUCESSO: Nenhum dos termos proibidos foi encontrado nos relatórios!")
                print("   ✅ O isolamento de dados (Nível 1) funcionou perfeitamente.")
            else:
                print("   ❌ AVISO: O modelo conseguiu 'espreitar' o futuro. O isolamento falhou.")

    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = _default_inputs()
    try:
        ForecastCrew().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ForecastCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = _default_inputs()

    try:
        ForecastCrew().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "pais": "",
        "ano_referencia": "",
        "horizonte": "",
    }

    try:
        result = ForecastCrew().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")