# Pesquisador de Vagas

Aplicação local para pesquisar vagas com OpenAI e Tavily, adaptar currículos
a vagas, exportar PDF ou DOCX e consultar o histórico de candidaturas.
Gmail e Google Drive são integrações opcionais.

## Como começar

Instale Docker com Compose, Node.js 20.19+ (ou 22.13+) e Make. Rode os comandos
abaixo na raiz do repositório para criar os arquivos locais se estiverem ausentes.

```bash
test -f .env || install -m 600 .env.example .env
mkdir -p storage/private
test -f storage/private/estrutura_curriculo.json ||
  install -m 600 database/estrutura_curriculo.example.json storage/private/estrutura_curriculo.json
npx --yes supabase --workdir database start
```

1. Preencha `OPENAI_API_KEY` e `TAVILY_API_KEY` no `.env`. Veja onde criar cada
   chave na seção [Chaves de API](#chaves-de-api).
2. Preencha `SUPABASE_KEY` no mesmo arquivo com a chave local `service_role`.
   Consulte `npx --yes supabase --workdir database status` se precisar localizá-la.
3. Execute `make up` e abra a interface em http://localhost:5173. A documentação
   da API fica em http://localhost:8000/docs.
4. Confira se o currículo inicial mostra **Pessoa Exemplo**. Clique em
   **Verificar** e exporte em **PDF** ou **DOCX**. Para testar a IA, envie
   no chat “Adapte o currículo para destacar os testes automatizados da base”. Com as
   duas chaves, use **Pesquisar Vagas** para testar a busca na web.

## Chaves de API

- **`OPENAI_API_KEY`** é usada pelos agentes para pesquisar e analisar vagas,
  conversar e adaptar o currículo. Crie uma chave no seu projeto da API.
  [Painel da OpenAI](https://platform.openai.com/api-keys)
- **`TAVILY_API_KEY`** é usada para buscar vagas e fontes na web. Crie a chave
  no painel do Tavily. [Painel do Tavily](https://app.tavily.com/)

A pesquisa de vagas requer as duas chaves. A adaptação sem pesquisa web
usa a OpenAI. A verificação local e a exportação usam a base de currículos
e funcionam sem essas chaves. Guarde as chaves no `.env` da raiz. Após
alterá-las, aplique a configuração com `docker compose up -d --force-recreate backend`.

## Modelos da OpenAI

O padrão é `gpt-6-luna`. As opções abaixo usam a API da OpenAI. Se escolher
outro modelo, confira se ele está disponível para seu projeto e revise o preço.

| ID do modelo | Quando usar |
| --- | --- |
| `gpt-6-luna` | Começar com o padrão de menor custo entre as opções da tabela |
| `gpt-6.1-terra` | Experimentar outro modelo para escrita e revisão |
| `gpt-6.2-sol` | Experimentar um modelo mais capaz em tarefas complexas |

[Catálogo da OpenAI](https://developers.openai.com/api/docs/models) ·
[Preços da API](https://developers.openai.com/api/docs/pricing)

| Variável no `.env` | Função |
| --- | --- |
| `MODEL_PESQUISA` | Agente que pesquisa vagas com Tavily |
| `MODEL_WRITE` | Agentes que escrevem o currículo e verificam currículos e vagas |
| `MODEL_CHAT` | Assistente de chat e agente coordenador |
| `MODEL_PLANILHA` | Reservada para planilhas, sem uso no fluxo atual |

## Base de currículos para a IA

A IA usa o arquivo local `storage/private/estrutura_curriculo.json` como fonte
de fatos. O projeto inclui dois currículos fictícios no mesmo
[JSON de exemplo](database/estrutura_curriculo.example.json), um voltado a
desenvolvimento web e outro a testes de software. O passo de instalação já copia
esse arquivo para o local que a aplicação lê.

1. Abra `storage/private/estrutura_curriculo.json` e use seu currículo atual
   como referência para editar o JSON. Se você tem o currículo em PDF ou DOCX,
   transcreva os fatos relevantes para o arquivo local.
2. Preencha `candidate` com seus dados, `education` com a formação e
   `languages` com os idiomas. Em `variants`, mantenha pelo menos uma variante
   com título profissional (`headline`), resumo (`summary`), competências
   (`skills`) e experiências (`experiences`). Use listas vazias para seções sem
   conteúdo e remova os exemplos fictícios que você não pretende usar.
3. Se tiver currículos para áreas diferentes, adicione uma entrada em
   `variants` para cada área. A primeira entrada é exibida ao abrir a página.
   A IA pode selecionar fatos das demais variantes ao adaptar o currículo.
4. Salve o arquivo, recarregue a página e confirme seu nome no documento.
   Use **Verificar** para conferir o currículo contra a base. Se aparecer
   `approved_source_unavailable`, confira o caminho e a sintaxe do JSON.

Os PDFs e DOCXs servem como referência para preencher o JSON. A seleção
automática de fatos usa apenas o JSON revisado. Para aprovar uma experiência
que faltou, acrescente-a ao arquivo local antes de pedir uma nova adaptação.

O Git ignora `.env`, a base pessoal, tokens OAuth e documentos locais. As
exportações ficam em `storage/curriculos/gerados/`. A aplicação é de uso
individual e deve rodar localmente. As chamadas de IA usam informações
profissionais revisadas da base, com os campos de contato tratados localmente.

## Integrações opcionais

Para usar Gmail ou Drive, crie um cliente OAuth do tipo **Aplicativo da Web**
no Google Cloud, configure `ID_CLIENT` e `KEY_CLIENT` em `.env` e autorize
`http://localhost:8000/api/gmail/callback` como URI de redirecionamento.
Inicie a conexão pela interface.

O frontend chama a API local por padrão. Para alterar a URL da API ou
configurar o cliente Supabase no navegador, copie `frontend/.env.example` para
`frontend/.env.local`. Use apenas a chave pública `anon` ou `publishable` no
frontend. A chave `service_role` deve ficar no backend. O Supabase Studio
fica em http://localhost:54323.

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
