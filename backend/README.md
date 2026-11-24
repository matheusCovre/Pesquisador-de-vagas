# Desenvolvimento e verificações

As regras de conteúdo e privacidade estão em [GUARDRAILS.md](GUARDRAILS.md).

## Login do Gmail

Inicie uma nova conexão pelo botão da interface ou por
http://localhost:8000/api/gmail/auth. O endpoint `/api/gmail/auth-url` retorna
essa entrada local para manter compatibilidade com a interface. Ela define
um cookie HttpOnly e redireciona ao Google; o verificador PKCE fica somente
no backend. O callback valida o estado e o navegador antes de trocar o código.
Cada tentativa expira após dez minutos e só pode ser consumida uma vez.

No Google Cloud, o cliente deve ser do tipo **Aplicativo da Web**, com a URI
autorizada exatamente igual a `GOOGLE_REDIRECT_URI`. O padrão é
`http://localhost:8000/api/gmail/callback`, sem barra final. Depois de uma
falha ou mudança no código, inicie outro login em vez de reutilizar o callback.

Para o uso local de uma pessoa, tentativas pendentes são persistidas em SQLite,
com consumo atômico entre processos no mesmo disco. Tentativas expiradas são
limpas no início de novos logins. Tokens são gravados atomicamente, com
permissão `0600`. O Docker monta `storage/private/` em `/data/private`:

- `GMAIL_OAUTH_DB_PATH`: `/data/private/gmail_oauth.sqlite3`.
- `GMAIL_TOKEN_PATH`: `/data/private/gmail_token.json`.

Essa pasta fica fora do Git e não deve ser publicada. Não há criptografia em
repouso implementada pela aplicação: são proteções locais de acesso a arquivos.
O projeto mantém uma conta Gmail por instalação; para múltiplos usuários ou
servidores será necessário separar tokens por usuário e usar armazenamento
compartilhado apropriado. Não há mudança nos escopos existentes de leitura e envio.

Referências: [Flow e PKCE](https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html)
e [OAuth para aplicações web do Google](https://developers.google.com/identity/protocols/oauth2/web-server).

Os comandos abaixo são executados na raiz do repositório e usam o ambiente
virtual `backend/.venv` com Python 3.12:

```bash
python3.12 -m venv backend/.venv  # somente se ainda não existir
make install-dev
make check
```

| Comando | Função |
| --- | --- |
| `make test` | Executa os testes com pytest |
| `make lint` | Verifica erros, imports e formatação com Ruff |
| `make format` | Aplica correções automáticas seguras e formata o código |
| `make check` | Verifica Ruff e executa os testes |
| `make coverage` | Gera cobertura no terminal e em `backend/htmlcov/index.html` |

É possível escolher outro interpretador: `make check PYTHON=python3`.
As dependências de desenvolvimento ficam em `requirements-dev.txt`; o container
da aplicação continua instalando apenas `requirements.txt`.

## Testes

`tests/` cobre arquivos locais, geração e leitura de DOCX/PDF, exportação,
validação de status, tratamento de erros e integração simulada com Gmail e
Supabase. A exportação é exercitada diretamente pela função da rota; estes
testes não verificam o transporte HTTP, CORS ou o banco real.

Cada teste usa diretório temporário e configurações sem credenciais reais.
Conexões de saída são bloqueadas e as integrações são simuladas. Não é preciso
iniciar Docker, ter chaves de API, enviar e-mails ou alterar o Supabase.
O carregamento automático de plugins é desabilitado: apenas `pytest-cov` é
habilitado explicitamente, evitando interferência de plugins de outros projetos
instalados no computador, como os de ROS.

Ao corrigir um bug, acrescente um teste que reproduza a falha. Ao modificar o
schema SQL, valide também a migração no Supabase local; os mocks não verificam
constraints, RLS ou triggers do PostgreSQL.

Ruff e pytest estão configurados em `pyproject.toml`. Referências:
[Ruff](https://docs.astral.sh/ruff/configuration/) e
[pytest](https://docs.pytest.org/en/stable/reference/customize.html).
