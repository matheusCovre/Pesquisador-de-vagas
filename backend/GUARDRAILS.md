# Verificação de currículos e proteção de informações

O backend aplica bloqueios determinísticos, independentemente da aprovação
de um agente. O objetivo é reduzir invenções e exposição de informações;
esta implementação não certifica conformidade jurídica com a LGPD nem substitui
a avaliação das obrigações contratuais e de confidencialidade.

## Fonte de fatos

`GUARDRAIL_SOURCE_PATH` aponta para `storage/private/estrutura_curriculo.json`
por padrão. Crie esse arquivo a partir do exemplo fictício e preencha seus
fatos revisados. A base local fica fora do Git. A aplicação lê esse arquivo.
As alterações são feitas manualmente pela pessoa responsável.

A pessoa responsável deve verificar autorização, comprovação e atualidade antes
de acrescentar qualquer fato à base. A IA, páginas web, documentos importados,
descrições de vagas e o currículo enviado pelo navegador não são fontes de
aprovação. O histórico de revisões da base e a comprovação das autorizações
ainda dependem desse processo humano, fora da aplicação.

Nesta primeira política, a comparação é literal, normalizando apenas Unicode,
maiúsculas/minúsculas e espaços. Permite selecionar e ordenar fatos; bloqueia
paráfrases, datas novas, cargos, métricas, idiomas e competências sem fonte.
Qualificadores como fundamentos, estudos e simulação devem ser preservados.
Contatos opcionais podem ser omitidos; contatos novos são rejeitados.

Fonte ausente ou inválida bloqueia a operação. `POST /api/documents/verify`
recebe `ResumeData` e retorna `approved` ou `blocked`, códigos e campos.
Um resultado aprovado inclui o SHA-256 dos fatos usados. Esse relatório é uma
checagem técnica e não uma autorização de envio. Cada geração verifica tudo
novamente; não confia em um campo de aprovação vindo do cliente.

## Onde os bloqueios atuam

- Geração direta de DOCX/PDF, exportação, ferramentas e anexos do Gmail.
- Antes de criar agentes a partir de um currículo e após receber sua saída.
- Pesquisa web: bloqueio de identificação do candidato e padrões sensíveis.
- Texto extraído do documento gerado, antes de gravá-lo na pasta.
- Uploads: limite de 5 MiB, PDF com até dez páginas, bloqueio de PDF criptografado
  e anexos incorporados, limite de expansão de ZIP e bloqueio de macros/objetos
  incorporados em DOCX. Conteúdo textual e metadados textuais são inspecionados.

Os agentes recebem contatos substituídos por `[DADO_LOCAL]`. O contexto de
evidências contém somente informações profissionais. O backend restaura os
contatos a partir da base local. Mensagens de erro e logs de bloqueio incluem
somente códigos/campos; não repetem o conteúdo rejeitado. Verbose, telemetria
OpenTelemetry e tracing do CrewAI estão desabilitados neste fluxo.

Resultados de busca e documentos são dados não confiáveis; os prompts proíbem
seguir instruções encontradas neles. A defesa final é a comparação com a base,
não a promessa do modelo de que revisou o próprio resultado. O backend não
exibe respostas livres ou caminhos de arquivos inventados pelo modelo. Nesta
fase, a resposta do chat é um aviso fixo sobre o resultado da verificação;
uma conversa livre com checagem semântica de evidências ainda não foi implementada.

## Envio e arquivos

O escritor e o verificador não recebem ferramentas para gravar documentos.
O backend só gera os arquivos finais depois da validação. As ferramentas de
geração continuam protegidas caso sejam chamadas diretamente.

O Gmail exige `reviewed_by_user=true` e repete a checagem do currículo e a
inspeção de privacidade no assunto/corpo. Essa declaração exige revisão do
usuário; não é autenticação nem prova de consentimento/base legal. Não pode
liberar fatos que falharam na verificação. A mensagem de e-mail é texto escrito
pelo usuário: sua factualidade não é comprovada por comparação semântica.

Os arquivos novos usam permissão `0600` e permanecem no armazenamento local.
O frontend envia `reviewed_by_user` após a revisão e exibe os bloqueios HTTP 422.

## Limites conhecidos

A detecção de dados pessoais/segredos usa padrões e não é exaustiva. Não há
OCR, antivírus, inspeção esteganográfica, avaliação jurídica automática, prova
de autorização das fontes, autenticação de usuários ou política automática
de retenção/exclusão. Upload aprovado na inspeção estrutural continua
`trusted=false` e `requires_review=true`; ele nunca aprova novos fatos.

O modelo recebe dados profissionais revisados para executar a tarefa. A
minimização não significa ausência total de dados pessoais ou anonimização
juridicamente comprovada. A escolha do provedor, a base legal e as obrigações
de tratamento/transferência precisam ser avaliadas no uso real.

Os princípios de finalidade, necessidade e qualidade dos dados orientam esta
política técnica: [art. 6º da LGPD, texto oficial](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html).

## Verificação em desenvolvimento

Execute `make check`. Os testes usam fatos fictícios em uma fonte temporária,
sem desligar o guardrail. Há testes para falsificação de experiência, métricas,
senioridade, idiomas, contatos, dados sensíveis, segredos, metadados ocultos,
saídas inválidas da IA, ferramentas chamadas diretamente e envio sem revisão.
Não chamar provedores reais com documentos internos durante desenvolvimento.
