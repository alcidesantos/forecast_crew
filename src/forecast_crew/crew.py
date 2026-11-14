import os
from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

@CrewBase
class ForecastCrew():
    """ForecastCrew crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    def _llm(self) -> LLM:
        return LLM(
            model="deepseek/deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.0,
        )

    # ----- Agentes -----
    @agent
    def economista_ortodoxo(self) -> Agent:
        return Agent(config=self.agents_config['economista_ortodoxo'], llm=self._llm(), verbose=True)

    @agent
    def economista_marxista(self) -> Agent:
        return Agent(config=self.agents_config['economista_marxista'], llm=self._llm(), verbose=True)

    @agent
    def sociologo_social_democrata(self) -> Agent:
        return Agent(config=self.agents_config['sociologo_social_democrata'], llm=self._llm(), verbose=True)

    @agent
    def analista_libertario(self) -> Agent:
        return Agent(config=self.agents_config['analista_libertario'], llm=self._llm(), verbose=True)

    @agent
    def analista_base_rates(self) -> Agent:
        return Agent(config=self.agents_config['analista_base_rates'], llm=self._llm(), verbose=True)

    @agent
    def redator(self) -> Agent:
        return Agent(config=self.agents_config['redator'], llm=self._llm(), verbose=True)

    # ----- Tarefas -----
    @task
    def tarefa_evidencia(self) -> Task:
        return Task(config=self.tasks_config['tarefa_evidencia'])

    @task
    def tarefa_estimativa_ortodoxa(self) -> Task:
        return Task(config=self.tasks_config['tarefa_estimativa_ortodoxa'])

    @task
    def tarefa_estimativa_marxista(self) -> Task:
        return Task(config=self.tasks_config['tarefa_estimativa_marxista'])

    @task
    def tarefa_estimativa_social_democrata(self) -> Task:
        return Task(config=self.tasks_config['tarefa_estimativa_social_democrata'])

    @task
    def tarefa_estimativa_libertario(self) -> Task:
        return Task(config=self.tasks_config['tarefa_estimativa_libertario'])

    @task
    def tarefa_estimativa_base_rates(self) -> Task:
        return Task(config=self.tasks_config['tarefa_estimativa_base_rates'])

    @task
    def tarefa_agregacao(self) -> Task:
        return Task(config=self.tasks_config['tarefa_agregacao'])

    # ----- Crew -----
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )