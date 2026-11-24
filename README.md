# Pesquisador de Vagas

Aplicação local para pesquisar vagas com OpenAI e Tavily, adaptar currículos
a vagas, exportar PDF ou DOCX e consultar o histórico de candidaturas.
Gmail e Google Drive são integrações opcionais.

## Como começar

Instale Docker com Compose, Node.js 20.19+ (ou 22.13+) e Make. Na raiz do repositório:

```bash
install -m 600 .env.example .env
mkdir -p storage/private
install -m 600 database/estrutura_curriculo.example.json storage/private/estrutura_curriculo.json
npx --yes supabase --workdir database start
```

1. Preencha `SUPABASE_KEY` em `.env` com a chave local `service_role` exibida
   pelo Supabase. Para consultá-la novamente, use
   `npx --yes supabase --workdir database status`.
2. Preencha `OPENAI_API_KEY` para usar o chat e `TAVILY_API_KEY` para habilitar
   a pesquisa de vagas junto com a chave da OpenAI. Os campos `MODEL_*` permitem
   escolher modelos disponíveis para sua conta.
3. Execute `make up` e abra a interface em http://localhost:5173. A documentação
   da API fica em http://localhost:8000/docs e o Studio em http://localhost:54323.
   Com a base fictícia, você já pode verificar o currículo inicial e exportá-lo.

Para usar Gmail ou Drive, crie um cliente OAuth do tipo **Aplicativo da Web**
no Google Cloud, configure `ID_CLIENT` e `KEY_CLIENT` em `.env` e autorize
`http://localhost:8000/api/gmail/callback` como URI de redirecionamento.
Inicie a conexão pela interface.

O frontend chama a API local por padrão. Para alterar a URL da API ou
configurar o cliente Supabase no navegador, copie `frontend/.env.example` para
`frontend/.env.local`. Use apenas a chave pública `anon` ou `publishable` no
frontend. A chave `service_role` deve ficar no backend.

## Use seu currículo

Edite `storage/private/estrutura_curriculo.json`. Substitua nome, contatos,
formação, competências, experiências e projetos fictícios por informações que
você possa comprovar. Você pode usar listas vazias nas seções sem conteúdo.
Recarregue a página para ver o currículo inicial. A primeira variante aparece
na interface e todas as variantes servem de referência para a verificação.

O Git ignora `.env`, a base pessoal, tokens OAuth e documentos locais. As
exportações ficam em `storage/curriculos/gerados/`. A aplicação é de uso
individual e deve rodar localmente. As chamadas de IA usam informações
profissionais revisadas da base, com os campos de contato tratados localmente.

## Desenvolvimento

```bash
python3.12 -m venv backend/.venv
make install-dev
make check
npm --prefix frontend ci
npm --prefix frontend run build
```

Consulte os detalhes do [backend](backend/README.md), da
[verificação de currículos](backend/GUARDRAILS.md) e do [banco local](database/README.md).
