from supabase import Client, create_client

from app.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não configurados.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def list_modelos() -> list[dict]:
    client = get_supabase_client()
    res = client.table("modelos_curriculo").select("*").order("nome").execute()
    return res.data or []


def get_or_create_empresa(
    nome: str,
    site: str | None = None,
    pais: str | None = None,
    setor_atuacao: str | None = None,
) -> dict:
    client = get_supabase_client()
    existing = client.table("empresas").select("*").ilike("nome", nome.strip()).limit(1).execute()
    if existing.data:
        return existing.data[0]

    res = (
        client.table("empresas")
        .insert(
            {
                "nome": nome.strip(),
                "site": site,
                "pais": pais,
                "setor_atuacao": setor_atuacao,
            }
        )
        .execute()
    )
    return res.data[0]


def create_vaga(
    titulo: str,
    empresa_id: str,
    url_original: str | None = None,
    requisitos: list[str] | None = None,
    senioridade: str | None = None,
    modalidade: str | None = None,
    salario: str | None = None,
    idioma: str | None = None,
    elegivel_brasil: bool | None = None,
    pontuacao_compatibilidade: float | None = None,
) -> dict:
    client = get_supabase_client()
    res = (
        client.table("vagas")
        .insert(
            {
                "titulo": titulo.strip(),
                "empresa_id": empresa_id,
                "url_original": url_original,
                "requisitos": requisitos or [],
                "senioridade": senioridade,
                "modalidade": modalidade,
                "salario": salario,
                "idioma": idioma,
                "elegivel_brasil": elegivel_brasil,
                "pontuacao_compatibilidade": pontuacao_compatibilidade,
            }
        )
        .execute()
    )
    return res.data[0]


def create_curriculo_gerado(
    modelo_id: str,
    vaga_id: str,
    modelo_ia: str,
    arquivo_docx_id: str | None = None,
    arquivo_pdf_id: str | None = None,
) -> dict:
    client = get_supabase_client()
    latest = (
        client.table("curriculos_gerados")
        .select("versao")
        .eq("modelo_id", modelo_id)
        .eq("vaga_id", vaga_id)
        .order("versao", desc=True)
        .limit(1)
        .execute()
    )
    next_version = (latest.data[0]["versao"] + 1) if latest.data else 1

    res = (
        client.table("curriculos_gerados")
        .insert(
            {
                "modelo_id": modelo_id,
                "vaga_id": vaga_id,
                "versao": next_version,
                "modelo_ia": modelo_ia,
                "arquivo_docx_id": arquivo_docx_id,
                "arquivo_pdf_id": arquivo_pdf_id,
            }
        )
        .execute()
    )
    return res.data[0]


def create_candidatura(
    vaga_id: str,
    curriculo_id: str,
    status_atual: str = "enviado_sem_resposta",
    comprovante_id: str | None = None,
) -> dict:
    client = get_supabase_client()
    res = (
        client.table("candidaturas")
        .insert(
            {
                "vaga_id": vaga_id,
                "curriculo_id": curriculo_id,
                "status_atual": status_atual,
                "comprovante_id": comprovante_id,
            }
        )
        .execute()
    )
    return res.data[0]


def update_candidatura_status(candidatura_id: str, status_novo: str) -> dict:
    client = get_supabase_client()
    res = (
        client.table("candidaturas")
        .update({"status_atual": status_novo})
        .eq("id", candidatura_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def list_candidaturas(limit: int = 20) -> list[dict]:
    client = get_supabase_client()
    res = (
        client.table("candidaturas")
        .select(
            "id, data_candidatura, status_atual, comprovante_id, "
            "vagas(id, titulo, modalidade, senioridade, pontuacao_compatibilidade, empresas(id, nome, pais)), "
            "curriculos_gerados(id, versao, modelo_ia, arquivo_docx_id, arquivo_pdf_id, modelos_curriculo(codigo, nome)), "
            "eventos_candidatura(id, data_evento, tipo, status_anterior, status_novo, descricao)"
        )
        .order("data_candidatura", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def register_candidatura_flow(
    empresa_nome: str,
    vaga_titulo: str,
    modelo_codigo: str,
    modelo_ia: str,
    comprovante_id: str | None = None,
    arquivo_docx_id: str | None = None,
    arquivo_pdf_id: str | None = None,
) -> dict:
    """Registra empresa -> vaga -> curriculo_gerado -> candidatura em sequência."""
    client = get_supabase_client()
    modelo_res = (
        client.table("modelos_curriculo")
        .select("id")
        .eq("codigo", modelo_codigo)
        .limit(1)
        .execute()
    )
    if not modelo_res.data:
        raise ValueError(f"Modelo de currículo '{modelo_codigo}' não encontrado.")

    empresa = get_or_create_empresa(empresa_nome)
    vaga = create_vaga(titulo=vaga_titulo, empresa_id=empresa["id"])
    curriculo = create_curriculo_gerado(
        modelo_id=modelo_res.data[0]["id"],
        vaga_id=vaga["id"],
        modelo_ia=modelo_ia,
        arquivo_docx_id=arquivo_docx_id,
        arquivo_pdf_id=arquivo_pdf_id,
    )
    candidatura = create_candidatura(
        vaga_id=vaga["id"],
        curriculo_id=curriculo["id"],
        comprovante_id=comprovante_id,
    )
    return {
        "empresa": empresa,
        "vaga": vaga,
        "curriculo_gerado": curriculo,
        "candidatura": candidatura,
    }
