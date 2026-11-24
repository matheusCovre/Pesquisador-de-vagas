-- Arquivos de currículos permanecem fora do PostgreSQL.
-- Identificadores de arquivo são referências opacas no armazenamento escolhido.

create table public.empresas (
    id uuid primary key default gen_random_uuid(),
    nome text not null check (btrim(nome) <> ''),
    site text,
    pais text,
    setor_atuacao text
);

create table public.vagas (
    id uuid primary key default gen_random_uuid(),
    titulo text not null check (btrim(titulo) <> ''),
    empresa_id uuid not null references public.empresas(id) on delete restrict,
    url_original text,
    requisitos text[] not null default '{}',
    senioridade text,
    modalidade text,
    salario text,
    idioma text,
    data_publicacao date,
    elegivel_brasil boolean,
    pontuacao_compatibilidade numeric(5,2)
        check (pontuacao_compatibilidade between 0 and 100)
);

comment on column public.vagas.salario is 'Texto preserva moeda, faixa e periodicidade anunciadas.';
comment on column public.vagas.elegivel_brasil is 'NULL: ainda não verificado; true: elegível; false: inelegível.';
comment on column public.vagas.pontuacao_compatibilidade is 'Escala de 0 a 100; NULL quando não avaliada.';

create table public.modelos_curriculo (
    id uuid primary key default gen_random_uuid(),
    codigo text not null unique,
    nome text not null check (btrim(nome) <> ''),
    arquivo_docx_id text,
    arquivo_pdf_id text
);

insert into public.modelos_curriculo (codigo, nome) values
    ('automacao', 'Automação'),
    ('ia_python', 'IA/Python'),
    ('robotica', 'Robótica'),
    ('physical_ai', 'Physical AI');

create table public.curriculos_gerados (
    id uuid primary key default gen_random_uuid(),
    modelo_id uuid not null references public.modelos_curriculo(id) on delete restrict,
    vaga_id uuid not null references public.vagas(id) on delete restrict,
    versao integer not null check (versao > 0),
    data_criacao timestamptz not null default now(),
    arquivo_docx_id text,
    arquivo_pdf_id text,
    modelo_ia text not null check (btrim(modelo_ia) <> ''),
    unique (modelo_id, vaga_id, versao),
    unique (id, vaga_id)
);

create table public.candidaturas (
    id uuid primary key default gen_random_uuid(),
    vaga_id uuid not null references public.vagas(id) on delete restrict,
    data_candidatura timestamptz not null default now(),
    curriculo_id uuid not null,
    status_atual text not null default 'enviado_sem_resposta'
        check (status_atual in (
            'enviado_sem_resposta', 'enviado_com_resposta', 'confirmacao',
            'entrevista', 'rejeicao', 'aprovacao', 'cancelamento'
        )),
    comprovante_id text,
    foreign key (curriculo_id, vaga_id)
        references public.curriculos_gerados(id, vaga_id) on delete restrict
);

comment on column public.candidaturas.comprovante_id is 'Identificador externo do comprovante; não contém o documento.';

create table public.eventos_candidatura (
    id uuid primary key default gen_random_uuid(),
    candidatura_id uuid not null references public.candidaturas(id) on delete restrict,
    data_evento timestamptz not null default now(),
    tipo text not null check (btrim(tipo) <> ''),
    status_anterior text,
    status_novo text,
    descricao text
);

-- Cada criação ou mudança de status gera um evento na mesma transação.
-- Outros eventos (ex.: segunda entrevista) podem ser registrados explicitamente.
create function public.registrar_evento_candidatura()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if TG_OP = 'INSERT' then
        insert into public.eventos_candidatura
            (candidatura_id, data_evento, tipo, status_anterior, status_novo)
        values (new.id, new.data_candidatura, 'registro_candidatura', null, new.status_atual);
    elsif new.status_atual is distinct from old.status_atual then
        insert into public.eventos_candidatura
            (candidatura_id, tipo, status_anterior, status_novo)
        values (new.id, 'mudanca_status', old.status_atual, new.status_atual);
    end if;
    return new;
end;
$$;

revoke all on function public.registrar_evento_candidatura() from public, anon, authenticated;

create trigger candidaturas_registrar_evento
after insert or update of status_atual on public.candidaturas
for each row execute function public.registrar_evento_candidatura();

create index vagas_empresa_idx on public.vagas (empresa_id);
create index curriculos_gerados_vaga_idx on public.curriculos_gerados (vaga_id);
create index candidaturas_vaga_idx on public.candidaturas (vaga_id);
create index candidaturas_curriculo_vaga_idx on public.candidaturas (curriculo_id, vaga_id);
create index eventos_candidatura_data_idx
    on public.eventos_candidatura (candidatura_id, data_evento);

-- Acesso pelo backend com service_role; o frontend não tem acesso anônimo.
alter table public.empresas enable row level security;
alter table public.vagas enable row level security;
alter table public.modelos_curriculo enable row level security;
alter table public.curriculos_gerados enable row level security;
alter table public.candidaturas enable row level security;
alter table public.eventos_candidatura enable row level security;

revoke all on table public.empresas, public.vagas, public.modelos_curriculo,
    public.curriculos_gerados, public.candidaturas, public.eventos_candidatura
    from anon, authenticated;
grant select, insert, update, delete on table public.empresas, public.vagas,
    public.modelos_curriculo, public.curriculos_gerados, public.candidaturas
    to service_role;
-- Histórico preservado: o backend pode ler e adicionar eventos.
grant select, insert on table public.eventos_candidatura to service_role;
revoke update, delete, truncate, references, trigger
    on table public.eventos_candidatura from service_role;

notify pgrst, 'reload schema';
