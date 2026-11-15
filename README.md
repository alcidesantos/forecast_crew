# Forecast Crew: Multi-Agent System for Sociopolitical Event Forecasting

This repository contains the source code and methodology of a multi-agent system developed for the **Intelligent Agents and Multi-Agent Systems** course (5th Semester, Systems Engineering).

The project aims to estimate the probability of sociopolitical events (financial crises, popular uprisings, and armed conflicts) in a given territory and time horizon. The system uses [crewAI](https://crewai.com) to orchestrate five distinct analytical lenses (Orthodox, Marxist, Social-Democrat, Libertarian, and Base Rates) and evaluates the predictive calibration of each one using statistical metrics (Brier Score, Log Loss, and Bootstrap).

## Prerequisites

Before starting the installation, ensure you have the following requirements:

1. **Operating System**: Linux, macOS, or Windows with **WSL (Ubuntu)**. ***(Note: CrewAI is not natively supported on Windows due to UNIX signal dependencies)***.
2. **Python**: Version `>= 3.10` and `< 3`.14 (Recommended: Python 3.12).
3. `uv` **Package Manager**: Used to manage the virtual environment and dependencies quickly. 
4. **API Keys**:
    <br><sup>- **DeepSeek API Key** (for the LLM agents).</sup>
    <br><sup>- **FRED API Key** (for vintage economic data).</sup>

## Environment Configuration (Variables)

Create a `.env` file in the project root and add your API keys:

```bash
DEEPSEEK_API_KEY=sk-your_key_here
FRED_API_KEY=your_fred_key_here
```

***(You can get the DeepSeek key at [platform.deepseek.com](platform.deepseek.com) and the FRED key at [fredaccount.stlouisfed.org](fredaccount.stlouisfed.org)).***

## Google Cloud BigQuery Configuration (GDELT Data)

This project retrieves historical news data from the **GDELT Project** directly via **Google BigQuery** (`gdelt-bq.gdeltv2.gkg_partitioned`), bypassing the HTTP rate limits of the public API. 

To run the script on another computer, you need to set up a Google Cloud account (the *Sandbox* mode offers **1 TB of free queries per month** without requiring a credit card) and choose **one of the two authentication methods** below.

### Prerequisite: Create a Google Cloud Project
1. Access the [Google Cloud Console - BigQuery](https://console.cloud.google.com/bigquery).
2. Log in with a Google account and create a new project (e.g., `forecast-crew-academic`).
3. Note the generated **Project ID**.

### Method 1: Command Line Authentication (Recommended for local use)

Ideal for quickly setting up your development machine without managing key files.

1. Install the **Google Cloud CLI** (`gcloud`) following the [official instructions](https://cloud.google.com/sdk/docs/install).
2. In the terminal, authenticate your account and associate the quota project:
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```
3. Ensure your Python code initializes the client with your Project ID:
```python
bq_client = bigquery.Client(project="YOUR_PROJECT_ID")
```
### Method 2: Service Account & JSON Key (Recommended for servers or sharing)

Ideal for running the code on a server, container, or another computer without installing the `gcloud` CLI or opening a browser.

1. **Create the Service Account**:
  - Go to **IAM & Admin > Service Accounts** in the [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts).
  - Click **+ Create Service Account**, give it a name (e.g., `gdelt-reader`), and click **Create and Continue**.
  - In the permissions step (***Grant this service account access to project***), add the **BigQuery Job User** role. Click **Done**.
2. **Generate and Save the JSON Key**:
  - In the service account list, click the newly created account and go to the **Keys** tab.
  - Click **Add Key > Create new key**, select **JSON**, and click **Create**.
  - The file will download automatically. Rename it to `gcp_key.json` and place it in the project root (or a secure folder).
3. **Configure the Environment Variable (`.env`)**:
  - Add the file path and project ID to your `.env`:
```env
GOOGLE_APPLICATION_CREDENTIALS="gcp_key.json"
GCP_PROJECT_ID="YOUR_PROJECT_ID"
```
  - ***(Note: Never upload the `gcp_key.json` file to public repositories. Add `gcp_key.json` to your `.gitignore`)***.
4. **Python Code Usage**:
The Google SDK automatically detects the `GOOGLE_APPLICATION_CREDENTIALS` variable, or you can load it explicitly in `gerar_evidencia.py`:
```env
import os
from google.cloud import bigquery

# Loads automatically via GOOGLE_APPLICATION_CREDENTIALS or explicitly:
if os.path.exists("gcp_key.json"):
    bq_client = bigquery.Client.from_service_account_json("gcp_key.json")
else:
    bq_client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
```

## Dependencies and Installation

The project uses the following main libraries (versions recorded during development):
  - `crewai==1.15.35` (Multi-agent orchestration framework)
  - `pandas==3.1.1` (Master DataFrame manipulation)
  - `scikit-learn==1.9.1` (Brier Score and Log Loss calculation)
  - `fredapi==0.5.2` (FRED/ALFRED API access)
  - `gdelt-py==0.1.11` (GDELT API access)
  - `requests` and `python-dotenv` (HTTP requests and environment variable management)

### Installation Procedure:

1. Open the terminal at the project root (`forecast_crew/`).
2. Install `uv` (if you don't have it yet):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
3. Create the virtual environment and install CrewAI and the other dependencies:
```bash
uv pip install crewai fredapi pandas scikit-learn gdelt-py requests python-dotenv
```
4. Install the local project scripts (compiles the `forecast_crew` package):
```bash
crewai install
```

## Execution Procedure

The project pipeline is divided into three sequential and independent phases. **You must run the commands in the order presented**.

### Phase 1: Auditable Evidence Collection

This script queries the FRED (vintage data), Wikipedia (dated revisions), and GDELT (historical news) APIs and generates the `.md` files in the `dados/evidencia/` folder.
```bash
uv run gerar_evidencia.py
```

***(Note: Due to rate limiting on the public GDELT API, the news source may fail in some scenarios. The script is designed to be resilient and continues execution using the FRED and Wikipedia sources).***

### Phase 2: Agent Execution (CrewAI)

Open the `src/forecast_crew/main.py` file and change the `_default_inputs()` function to the scenario you want to test (e.g., France 2018, Ukraine 2013, USA 2007). You should also update the `termos_proibidos` (forbidden terms) for the Leakage test.

After configuring the scenario, run:
```bash
crewai run
```

The system will read the corresponding evidence file, execute the 5 analytical lenses + the Redactor, and save the results in the `resultados/` folder.

### Phase 3: Statistical Evaluation

After running all the intended scenarios, this script consolidates the results into `dataframe_mestre.csv` and calculates the final Leaderboard (Brier Score, Log Loss, Confidence Intervals via Bootstrap).
```bash
uv run avaliar.py
```

## Folder Structure
```text
forecast_crew/
├── src/forecast_crew/       # CrewAI source code
│   ├── config/              # Agent and Task Prompts (YAMLs)
│   ├── crew.py              # Crew and LLM definition (DeepSeek)
│   └── main.py              # Entry point and scenario inputs
├── dados/evidencia/         # .md evidence packages (automatically generated)
│   └── manifest.json        # Data provenance record (FRED, Wikipedia)
├── resultados/              # Outputs generated per scenario (estimates + aggregation)
├── gerar_evidencia.py       # Auditable data collection script
├── avaliar.py               # Metrics and Leaderboard calculation script
├── dataframe_mestre.csv     # Final table with all predictions (generated by avaliar.py)
└── .env                     # API keys (should not be versioned)
```

## Methodological Note (Leakage Mitigation)

To ensure the rigor of the ***backtesting***, the system implements two barriers against ***look-ahead bias*** (leakage):
1. **Data Isolation (Level 1)**: Agents do not have internet access. They only read the provided `.md` file, whose information is strictly dated up to the cutoff date (via FRED's `realtime_start` and Wikipedia's `revid`).
2. **Self-Recall (Level 2)**: The agent prompts contain a strict temporality rule, forcing them to reason only with the facts in the evidence package.
The `main.py` script also includes a **Leakage Probe** that automatically checks if the agents used forbidden terms (which would only exist after the cutoff date).

## Advanced Experimental Design & Future Work

While the current prototype (`v2`) focuses on a baseline evaluation (1 reciter: Base Rates) across 7 scenarios, the architecture is fully prepared for a large-scale factorial experiment. The theoretical framework for this expansion is described below and left as future work due to computational time constraints.

### 1. Ablation Study: With vs. Without the "Hallucination Auditor"
The system includes an LLM-based Auditor to detect if agents invent facts outside the provided evidence. To empirically measure the Auditor's impact on predictive accuracy, the entire pipeline can be run in two modes:
*   **With Auditor:** Agents are forced to strictly adhere to the evidence (reduces hallucinations, but may limit deductive reasoning).
*   **Without Auditor:** Agents rely on their internal knowledge to interpret the evidence (risk of leakage/hallucination, but potentially higher reasoning capability).
*   *Implementation:* By running the dataset twice and comparing the Brier Scores, we can prove whether fact-checking improves or degrades calibration.
**Leakage Mitigation without the Auditor:**
When the system operates in the "Without Auditor" mode, temporal integrity is not left unchecked. The pipeline automatically falls back to a rule-based **Leakage Probe**. This script cross-references the agents' generated texts against a predefined list of `forbidden_terms` (e.g., "Lehman Brothers" for the 2007 scenario) configured in the `cenarios.json`. 
If any of these future-specific terms are detected, the system flags the output as contaminated. This dual-layer approach ensures that:
*   **With Auditor:** Leakage is checked semantically (LLM-based fact-checking).
*   **Without Auditor:** Leakage is checked heuristically (Regex/String matching against the forbidden terms list).
Thus, a baseline of data isolation and historical accuracy is maintained in both experimental setups.

### 2. Selection Bias: The "Reciter Rotation" Matrix
Currently, the "Base Rates" agent is responsible for summarizing the evidence file before the other agents interpret it. However, each ideological lens (Orthodox, Marxist, etc.) perceives facts differently. To test for **selection bias**, a full factorial design (Rotation Matrix) is proposed:
*   Each of the 5 profiles acts as the "Reciter" one time.
*   For each recitation, all 5 profiles generate an estimate.
*   This results in a matrix of \(5 \times 5 = 25\) estimates per scenario.

### 3. The Combinatorial Challenge (Why it is Future Work)
If applied to all 7 historical scenarios, the full experiment would require:
*   7 scenarios × 5 reciters = 35 full crew executions.
*   With and without the Auditor (Ablation) = 70 executions.
*   Each execution generates 5 agent estimates: **350 individual predictions**.

Considering an average execution time of ~2 minutes per crew, the full factorial experiment would require **~12 hours of continuous processing**, generating over 5 million API tokens. 
Therefore, the current deliverable implements the baseline (7 executions), while the rotation matrix and ablation study are documented as the immediate next step for a production-grade deployment. The code architecture (`run_all.py` and `crew.py`) already supports dynamic injection of the `reciter` and `auditor` parameters to enable this future expansion seamlessly.

## Declaration of AI Usage

In the spirit of academic transparency and integrity, the author declares the use of Generative Artificial Intelligence in this project in two distinct capacities:

**1. AI as the Object of Study (The System Engine)**
The multi-agent system itself is powered by Large Language Models (LLMs). The model used to run the agents (Orthodox, Marxist, Social-Democrat, Libertarian, Base Rates, and Redactor) is:
*   **Model:** DeepSeek (`deepseek-chat` model, accessed via API).
*   **Role:** To process the historical evidence, apply the specific analytical lenses defined in the prompts (`agents.yaml`), and generate probabilistic estimates.
*   **Parameters:** The system was executed with `temperature=0.0` to ensure maximum reproducibility and minimize non-deterministic variations.

**2. AI as a Development Tool (Coding and Methodology)**
The author also utilized an AI assistant (DeepSeek) to support the software engineering and methodological design process.
*   **Role:** Assistance in writing the Python code (CrewAI framework, data pipeline scripts), debugging API errors (FRED/GDELT), brainstorming the evaluation metrics (Brier Score, Bootstrap), and structuring this document.
*   **Academic Integrity:** All intellectual decisions regarding the experimental design, choice of historical scenarios, analysis of the empirical results, and final conclusions are solely the author's responsibility. The AI was used as a coding and structuring tool, not as a substitute for critical thinking or scientific authorship.











