from crewai import LLM, Agent
from crewai.agent.planning_config import PlanningConfig
from crewai.tools import BaseTool

from app.config import get_settings
from app.crew.prompts import AGENT_PROMPTS, TASK_PROMPTS
from app.crew.safety_policy import SAFETY_POLICY
from app.crew.tools import TavilySearchTool

MAX_AGENT_ITER = 3


def _build_llm(model_name: str) -> LLM:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY não configurada no .env")
    return LLM(model=model_name, api_key=settings.OPENAI_API_KEY)


def _create_agent(
    key: str,
    model_name: str,
    tools: list[BaseTool] | None = None,
    allow_delegation: bool = False,
    reasoning_attempts: int = 0,
) -> Agent:
    cfg = AGENT_PROMPTS[key]
    planning_config = (
        PlanningConfig(
            max_attempts=reasoning_attempts,
            max_replans=1,
            max_step_iterations=MAX_AGENT_ITER,
            reasoning_effort="low",
        )
        if reasoning_attempts > 0
        else None
    )

    return Agent(
        role=cfg["role"],
        goal=SAFETY_POLICY + "\n" + cfg["goal"],
        backstory=cfg["backstory"],
        llm=_build_llm(model_name),
        tools=tools or [],
        allow_delegation=allow_delegation,
        max_iter=MAX_AGENT_ITER,
        planning_config=planning_config,
        verbose=False,
    )


def create_pesquisador() -> Agent:
    return _create_agent(
        "pesquisador",
        get_settings().MODEL_PESQUISA,
        tools=[TavilySearchTool()],
        reasoning_attempts=2,
    )


def create_escritor() -> Agent:
    return _create_agent(
        "escritor",
        get_settings().MODEL_WRITE,
        reasoning_attempts=1,
    )


def create_verificador() -> Agent:
    return _create_agent(
        "verificador",
        get_settings().MODEL_WRITE,
        allow_delegation=True,
        reasoning_attempts=2,
    )


def create_chatbot() -> Agent:
    return _create_agent(
        "chatbot",
        get_settings().MODEL_CHAT,
        reasoning_attempts=0,
    )


def create_manager() -> Agent:
    cfg = AGENT_PROMPTS["manager"]
    coordination_rules = TASK_PROMPTS["coordenar_processo"]["description"]
    return Agent(
        role=cfg["role"],
        goal=SAFETY_POLICY + "\n" + cfg["goal"],
        backstory=f"{cfg['backstory']}\n\n{coordination_rules}",
        llm=_build_llm(get_settings().MODEL_CHAT),
        tools=[],
        allow_delegation=True,
        max_iter=MAX_AGENT_ITER,
        planning_config=PlanningConfig(
            max_attempts=1,
            max_replans=1,
            max_step_iterations=MAX_AGENT_ITER,
            reasoning_effort="low",
        ),
        verbose=False,
    )
