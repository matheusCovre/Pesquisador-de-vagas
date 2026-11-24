# Banco local

Execute `make up` na raiz do repositório para iniciar o Supabase, aplicar
migrações pendentes e iniciar a aplicação. Com o Supabase já iniciado, execute
`make db-migrate` para aplicar apenas as migrações. Não é necessário resetar o banco.

Studio: http://localhost:54323. PostgreSQL: localhost:54322, banco `postgres`.

## Estrutura

| Módulo | Tabela | Conteúdo |
| --- | --- | --- |
| A | empresas | nome, site, país e setor de atuação |
| A | vagas | título, empresa, URL original, requisitos, senioridade, modalidade, salário, idioma, publicação, elegibilidade Brasil e compatibilidade |
| B | candidaturas | vaga, data da candidatura, currículo, status atual e identificador do comprovante |
| B | eventos_candidatura | candidatura, data do evento, tipo, status anterior/novo e descrição |
| C | modelos_curriculo | código, nome e identificadores dos arquivos originais |
| C | curriculos_gerados | modelo, vaga, versão, criação, identificadores DOCX/PDF e modelo de IA |

Todas as tabelas têm identificador UUID. Uma empresa pode ter várias vagas;
uma vaga pode ter vários currículos e candidaturas. Cada candidatura referencia
um currículo preparado para aquela mesma vaga. As exclusões de registros
referenciados são bloqueadas para preservar o histórico.

A migração cadastra as categorias Automação, IA/Python, Robótica e Physical AI.
As categorias são registros de banco. Cada pessoa configura sua base de fatos
em `storage/private/estrutura_curriculo.json`.

## Pasta dos arquivos

Os arquivos ficam em `storage/curriculos/`:

- `modelos/`: espaço opcional para os documentos da própria pessoa.
- `gerados/AAAA/MM/DD/<uuid>.pdf` ou `.docx`: cada exportação ou geração para
  envio por e-mail salva uma nova cópia; as datas das pastas usam UTC.

O backend usa `CURRICULOS_DIR`. No Docker, `/data/curriculos` está montado nessa
pasta do PC, preservando arquivos quando o container é recriado. Sem Docker,
o valor padrão aponta para a mesma pasta do projeto. Execute
`docker compose up -d --no-deps backend` após alterar o volume para recriar o
container com a montagem nova.

A exportação devolve o identificador relativo no cabeçalho `X-Document-Id`;
o envio por e-mail devolve `arquivo_id`. Esses identificadores podem preencher
`arquivo_docx_id` e `arquivo_pdf_id` em `curriculos_gerados` quando o cadastro
das gerações estiver integrado. Os arquivos não são servidos como pasta pública
e ficam fora do Git. As funções de geração que retornam apenas bytes continuam
disponíveis; as rotas de exportação e Gmail usam a geração com persistência.

## Convenções

- Não armazenar conteúdo de DOCX, PDF, currículo em JSON, base64 ou comprovantes
  no PostgreSQL. `arquivo_docx_id`, `arquivo_pdf_id` e `comprovante_id` são
  identificadores opacos de arquivos mantidos fora do banco, sem links assinados
  ou credenciais. A gravação local já está integrada à exportação e ao envio;
  a associação desses identificadores às seis tabelas ainda precisa ser implementada.
- Datas com horário usam `timestamptz`. A data de publicação usa `date`.
- Requisitos são uma lista de textos. Salário é texto para preservar moeda,
  faixa e periodicidade anunciadas. Campos não informados permanecem `NULL`.
- Elegibilidade Brasil: `true`, `false` ou `NULL` (não verificada).
- Compatibilidade: 0 a 100 ou `NULL` (não avaliada).
- Versões são inteiros positivos, únicos por combinação de modelo e vaga.
- Status: `enviado_sem_resposta`, `enviado_com_resposta`, `confirmacao`,
  `entrevista`, `rejeicao`, `aprovacao` e `cancelamento`.

Cadastre uma candidatura depois do envio efetivo. Sua criação gera um evento
`registro_candidatura`; alterar `status_atual` gera um evento `mudanca_status`.
Atualizações que preservam o status não duplicam eventos. Eventos adicionais
podem ser inseridos explicitamente, por exemplo uma segunda entrevista.
`data_evento` deve refletir o horário real da ocorrência quando informado pela
integração. Nas mudanças automáticas, ela registra o horário da atualização.
Assim, tempos de resposta calculados por eventos automáticos representam o
momento em que a resposta foi registrada pelo sistema.

O acesso previsto é pelo backend com `service_role`. RLS está habilitado e
`anon`/`authenticated` não têm acesso aos registros. A chave `service_role` fica
somente no backend; a integração da aplicação com essas tabelas ainda está pendente.
O backend pode ler e adicionar eventos, mas não atualizar ou excluir o histórico.

Referências: [migrações](https://supabase.com/docs/guides/deployment/database-migrations)
e [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
