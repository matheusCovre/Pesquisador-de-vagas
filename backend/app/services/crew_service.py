from app.crew.crew_runner import run_chat_flow_detailed
from app.schemas.resume import ResumeData


def run_resume_chat(
    user_message: str,
    current_resume: ResumeData | None = None,
    use_search: bool = True,
) -> dict:
    """Orquestra o workflow CrewAI Flow para o chat."""
    return run_chat_flow_detailed(
        user_message=user_message,
        current_resume=current_resume,
        use_search=use_search,
    )
