from crewai import Agent, Task

from app.crew.prompts import TASK_PROMPTS
from app.crew.safety_policy import SAFETY_POLICY


def create_pesquisar_vagas_task(agent: Agent, user_message: str) -> Task:
    cfg = TASK_PROMPTS["pesquisar_vagas"]
    return Task(
        description=SAFETY_POLICY + "\n" + cfg["description"].format(user_message=user_message),
        expected_output=cfg["expected_output"],
        agent=agent,
    )


def create_verificar_vagas_task(
    agent: Agent,
    context_tasks: list[Task] | None = None,
) -> Task:
    cfg = TASK_PROMPTS["verificar_vagas"]
    return Task(
        description=SAFETY_POLICY + "\n" + cfg["description"],
        expected_output=cfg["expected_output"],
        agent=agent,
        context=context_tasks or [],
    )


def create_desenvolver_curriculo_task(
    agent: Agent,
    current_resume_json: str,
    context_tasks: list[Task] | None = None,
) -> Task:
    cfg = TASK_PROMPTS["desenvolver_curriculo"]
    return Task(
        description=SAFETY_POLICY
        + "\n"
        + cfg["description"].format(current_resume_json=current_resume_json),
        expected_output=cfg["expected_output"],
        agent=agent,
        context=context_tasks or [],
    )


def create_verificar_curriculo_task(
    agent: Agent,
    context_tasks: list[Task] | None = None,
) -> Task:
    cfg = TASK_PROMPTS["verificar_curriculo"]
    return Task(
        description=SAFETY_POLICY + "\n" + cfg["description"],
        expected_output=cfg["expected_output"],
        agent=agent,
        context=context_tasks or [],
    )


def create_atendimento_candidato_task(
    agent: Agent,
    user_message: str,
    context_tasks: list[Task] | None = None,
) -> Task:
    cfg = TASK_PROMPTS["atendimento_candidato"]
    return Task(
        description=SAFETY_POLICY + "\n" + cfg["description"].format(user_message=user_message),
        expected_output=cfg["expected_output"],
        agent=agent,
        context=context_tasks or [],
    )


def create_coordenar_processo_task(
    agent: Agent,
    context_tasks: list[Task] | None = None,
) -> Task:
    cfg = TASK_PROMPTS["coordenar_processo"]
    return Task(
        description=SAFETY_POLICY + "\n" + cfg["description"],
        expected_output=cfg["expected_output"],
        agent=agent,
        context=context_tasks or [],
    )
