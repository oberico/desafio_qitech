# 09-oberico-desafio-qitech — banca da fase 1 (régua v2.13)

Commit avaliado: `161ffefb183c66a098b726cc0a09365c5b1926b6` · 2026-10-14

## Resumo

O time construiu o Banco RNV, uma conta PJ com gateway de pagamento dividida em dois serviços: o Banco, dono do livro e da identidade, e o Transferências, dono de vendas, saques, tarifas e jobs de liberação e reconciliação (RFC p. 3). O saldo é derivado das entries append-only, sem coluna de saldo, e o débito trava a linha da conta antes de somar (RFC p. 7, RFC p. 11). A idempotência mora na própria entidade, com chave e hash do payload (RFC p. 12). Nota 0, com 6 de 16 critérios atendidos: o projeto não seguiu na banca porque o saque para fora do banco não cobra tarifa, item 4 do escopo mínimo. Também pesaram as rotas fora do padrão REST (7 de 31 conformes) e a ausência de json schema nas rotas com corpo (0 de 9).

## Nota

**0,0 / 10 (eliminado no ESC-01)** · 6/16 critérios atendidos · COD-01: ✅ · ESC-01: ❌

🚩 eliminada no ESC-01 · nota de avaliação 6,7 / 10 (nota parcial: 1 item não pôde ser verificado)

Cálculo da nota: COD-01 ou ESC-01 reprovado zera a nota (são eliminatórios e, aprovados, não entram na média). Nos outros 14 critérios, o cumprimento é `ok/total` da contagem (sem contagem: 1 se passa, 0 se não passa); critério não verificado fica fora da média; nota \= 10 × média, com 1 casa decimal.

## Critérios

| id · título | resultado | contagem | falhas (arquivo:linha) |
| :---- | :---- | :---- | :---- |
| COD-01 · Sobe e testes passam | ✅ | 36/36 |  |
| ESC-01 · Escopo mínimo entregue | ❌ | 4/5 | decidido pela banca: item 4 (tarifa na transferência): o pagamento para fora atende o controle de saldo, mas não cobra tarifa (transferencias/src/controllers/payout\_controller.py:94-99) |
| COD-02 · Toda rota testada com 2xx | ❌ | 29/35 | banco/src/app.py:86: GET /admin/clients sem teste que a chame; banco/src/app.py:87: GET /admin/companies sem teste que a chame (+3) |
| COD-03 · Todo erro de domínio testado | ✅ | 35/35 |  |
| COD-04 · Só testes de integração black-box | ❌ | 516/516 | banco/tests/integration/client/test\_client\_create.py: usa TestClient; banco/tests/integration/client/test\_client\_me.py: usa TestClient (+2) |
| COD-05 · Entidade com `id` e `*_key` | ❌ | 4/8 | banco/database/database.sql:91: `api_token`: sem coluna `*_key` própria; banco/database/database.sql:157: `entry`: sem coluna `*_key` própria (+2) |
| COD-06 · Enum com tabela auxiliar | ✅ | 12/12 |  |
| COD-07 · Status registrado em `*_status_event` | ❌ | 4/7 | banco/database/database.sql:52: `allowed_transition` tem `from_status_id` e nenhuma tabela `*_status_event`; transferencias/database/database.sql:28: `payment_transition` tem `from_status_id` e nenhuma tabela `*_status_event` (+1) |
| COD-08 · Testes não importam src | ✅ | 145/145 |  |
| COD-09 · Sem chamada entre camadas irmãs | ✅ | 42/42 |  |
| COD-10 · Rotas REST no singular | ❌ | 7/31 | banco/src/app.py:71: POST /clients: `clients` no plural num POST; banco/src/app.py:73: POST /companies: `companies` no plural num POST (+22) |
| COD-11 · Commit só no fim do controller | ❌ | 9/14 | transferencias/src/controllers/payout\_reconcile\_controller.py:101 `_attempt`: commit em método privado do controller; transferencias/src/controllers/payout\_reconcile\_controller.py:158 `_finish`: commit em método privado do controller (+1) |
| COD-12 · Rota não-GET com JSON schema | ❌ | 0/9 | banco/src/app.py:71: POST /clients: `on_post` recebe corpo sem json schema; banco/src/app.py:73: POST /companies: `on_post` recebe corpo sem json schema (+7) |
| COD-13 · Connector testado via MockServer | ❌ | 0/4 | banco/src/connectors/transferencias\_connector.py:12: GET /internal/accounts/{}/in-flight: sem MockServer no compose; transferencias/src/connectors/bank\_connector.py:28: POST /ledger/transactions: sem MockServer no compose (+2) |
| COD-14 · Testes não acessam o banco | ✅ | 146/146 |  |
| RFC-01 · RFC fiel à implementação | ⏸ | 67/68 | não foi possível verificar este item. |

## Feedback

A aplicação sobe e a suíte passa inteira, e a RFC descreve com detalhe o livro contábil, a concorrência no débito e a reconciliação do payout. O projeto não seguiu na banca por falta da tarifa na transferência. Os demais ajustes estão em convenções de rota, de schema e de modelagem.

**Pontos fortes**

- Todos os 35 erros de domínio têm teste que confirma o código devolvido (COD-03, 35/35).  
- Nenhum arquivo de teste importa src (145/145) e nenhum acessa dado de negócio direto no banco (146/146). Os testes verificam o comportamento pela API.  
- A RFC trata o lost update no débito com trava na linha da conta antes do SUM e explica por que READ COMMITTED é necessário.

**Pontos de atenção**

- **ESC-01 · Escopo mínimo entregue**  
  - Encontrado: Faltou o item 4 do escopo mínimo, tarifa na transferência. O pagamento para fora do banco faz o controle de saldo, mas não cobra tarifa (transferencias/src/controllers/payout\_controller.py:94-99). Os itens 1, 2, 3 e 5 foram entregues.  
  - Por que a regra existe: A tarifa na transferência faz parte do escopo mínimo do enunciado, e sem ela o fluxo de transferência fica incompleto.  
  - O que fazer: Calcular e lançar a tarifa no POST /payouts, com a perna de receita no livro, e cobrir com teste que confira o saldo debitado com a tarifa.  
- **COD-02 · Toda rota testada com 2xx**  
  - Encontrado: 29 de 35 rotas têm teste com 2xx. Faltam as rotas de admin, por exemplo GET /admin/clients (banco/src/app.py:86), GET /admin/internal-accounts (banco/src/app.py:89) e GET /admin/payments (transferencias/src/app.py:88).  
  - Por que a regra existe: Rota sem teste de sucesso pode quebrar sem que a suíte perceba.  
  - O que fazer: Criar um teste por rota de admin que chame a rota com o token de administrador e confira o 2xx.  
- **COD-04 · Só testes de integração black-box**  
  - Encontrado: 4 arquivos de teste usam TestClient, por exemplo banco/tests/integration/client/test\_client\_create.py e transferencias/tests/integration/middleware/test\_client\_auth.py.  
  - Por que a regra existe: TestClient roda a aplicação dentro do processo do teste, e o teste deixa de exercitar a API como um cliente externo.  
  - O que fazer: Trocar o TestClient por requisições HTTP ao serviço que está no ar, como fazem os demais testes.  
- **COD-05 · Entidade com `id` e `*_key`**  
  - Encontrado: 4 de 8 entidades estão conformes. `api_token` (banco/database/database.sql:91) e `entry` (banco/database/database.sql:157) não têm coluna `*_key` própria. `payment` e `payout` referenciam outras entidades por chave, por exemplo `client_key` (transferencias/database/database.sql:97) e `account_key` (transferencias/database/database.sql:118).  
  - Por que a regra existe: O id interno serve para relacionamento e índice, e a `*_key` única é o identificador público de cada entidade.  
  - O que fazer: Adicionar coluna `*_key` unique em `api_token` e `entry` e fazer `payment` e `payout` referenciarem as entidades por `id`.  
- **COD-07 · Status registrado em `*_status_event`**  
  - Encontrado: 3 tabelas guardam status sem tabela de eventos: `allowed_transition` (banco/database/database.sql:52), `payment_transition` (transferencias/database/database.sql:28) e `payout_transition` (transferencias/database/database.sql:67).  
  - Por que a regra existe: A tabela de eventos registra cada mudança de status e permite auditar quando e como o estado mudou.  
  - O que fazer: Criar a tabela `*_status_event` correspondente a cada uma dessas tabelas e gravar nela cada alteração de status.  
- **COD-10 · Rotas REST no singular**  
  - Encontrado: 7 de 31 rotas de domínio seguem o padrão. São 24 falhas, por exemplo POST /clients no plural (banco/src/app.py:71), GET /accounts/{account\_key}/balance com plural fora do último segmento (banco/src/app.py:79) e GET /internal/internal-accounts com prefixo `/internal` e plural sem paginação (banco/src/app.py:84).  
  - Por que a regra existe: Rotas baseadas na entidade e no singular deixam o contrato previsível e reservam o plural para listagens paginadas.  
  - O que fazer: Renomear para a entidade no singular (POST /client, GET /account/{account\_key}), tirar o prefixo `/internal` do caminho e paginar com limit/page/offset todo GET no plural.  
- **COD-11 · Commit só no fim do controller**  
  - Encontrado: 3 métodos fazem commit fora do fim do método público do controller, em métodos privados: transferencias/src/controllers/payout\_reconcile\_controller.py:101, transferencias/src/controllers/payout\_reconcile\_controller.py:158 e transferencias/src/controllers/settlement\_controller.py:69.  
  - Por que a regra existe: Um único commit no fim do controller garante que a operação inteira grava junto ou não grava nada.  
  - O que fazer: Mover o commit de `_attempt`, `_finish` e `_release` para o fim do método público do controller que os chama.  
- **COD-12 · Rota não-GET com JSON schema**  
  - Encontrado: Nenhuma das 9 rotas não-GET com corpo valida json schema, por exemplo POST /clients (banco/src/app.py:71), POST /payments (transferencias/src/app.py:77) e PUT /internal/payment-methods/{method} (transferencias/src/app.py:87).  
  - Por que a regra existe: O schema rejeita entrada malformada na borda, antes de chegar à regra de negócio.  
  - O que fazer: Declarar um json schema por rota não-GET e validar o corpo com ele antes do controller.  
- **COD-13 · Connector testado via MockServer**  
  - Encontrado: Nenhum dos 4 endpoints de connector é verificado em MockServer. Não há MockServer no compose, e o interbancário é simulado por um `.py` em `external-mocks/` (transferencias/src/connectors/interbank\_connector.py:29). Os outros casos estão em banco/src/connectors/transferencias\_connector.py:12 e transferencias/src/connectors/bank\_connector.py:28.  
  - Por que a regra existe: O MockServer permite provar no teste que o serviço chamou o endpoint externo com o contrato esperado.  
  - O que fazer: Subir o MockServer no compose, configurar nele as respostas dos 4 endpoints e criar um teste por endpoint que confirme o acesso.

**Próximo passo:** Comecem pelo ESC-01: cobrar e lançar a tarifa no POST /payouts, com teste que confira o débito da tarifa no saldo.

## Detalhe por critério

### COD-01 · Sobe e testes passam — ✅

- contagem: 36/36 testes passando

### ESC-01 · Escopo mínimo entregue — ❌

- contagem: 4/5 itens do escopo mínimo  
- atendido: item 1 · Cliente: cadastro e consulta: banco/src/app.py:71, banco/src/controllers/client\_controller.py:60, banco/src/resources/client.py:13, banco/src/app.py:72, banco/src/controllers/client\_controller.py:78  
- atendido: item 2 · Conta vinculada a cliente e consulta de saldo: banco/src/app.py:77, banco/src/controllers/account\_controller.py:59, banco/database/database.sql:105, banco/src/app.py:79, banco/src/controllers/account\_controller.py:84  
- atendido: item 5 · Extrato paginado da conta: banco/src/app.py:80, banco/src/controllers/account\_controller.py:99, banco/src/repositories/ledger\_repository.py:90  
- falha: decidido pela banca: item 4 (tarifa na transferência): o pagamento para fora atende o controle de saldo, mas não cobra tarifa (transferencias/src/controllers/payout\_controller.py:94-99)  
- observação (fora da contagem): Não há depósito nem saque como rotas de cliente. POST /payments registra recebimento e POST /payouts debita a conta para um destino externo.  
- observação (fora da contagem): As rotas /ledger/\* e /internal/\* são internas (constants.py:15): exigem token interno e não ficam acessíveis ao cliente final.  
- observação (fora da contagem): A tarifa (fee\_bps) existe em payment e payment\_method e é cobrada só na liquidação de payments.

### COD-02 · Toda rota testada com 2xx — ❌

- contagem: 29/35 rotas testadas com 2xx  
- falha: banco/src/app.py:86: GET /admin/clients sem teste que a chame  
- falha: banco/src/app.py:87: GET /admin/companies sem teste que a chame  
- falha: banco/src/app.py:88: GET /admin/accounts sem teste que a chame  
- falha: banco/src/app.py:89: GET /admin/internal-accounts sem teste que a chame  
- falha: transferencias/src/app.py:88: GET /admin/payments sem teste que a chame  
- outros 3 pontos: não foi possível verificar este item.

### COD-03 · Todo erro de domínio testado — ✅

- contagem: 35/35 erros de domínio levantados com teste do código  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:5: RNV000002 (ForbiddenNotInternal) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:16: RNV000001 (InvalidSchema) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:27: RNV000007 (MissingField) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:38: RNV000008 (FieldNotAllowed) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:84: RNV000012 (InvalidIdempotencyKey) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:106: RNV000004 (NotFoundRoute) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:117: RNV000005 (MethodNotAllowed) declarado e nunca levantado  
- observação (fora da contagem): banco/src/errors/custom\_errors.py:139: RNV001027 (AdminForbidden) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:5: RNV000002 (ForbiddenNotInternal) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:16: RNV000004 (NotFoundRoute) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:27: RNV000006 (ServiceBusy) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:38: RNV000005 (MethodNotAllowed) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:86: RNV000001 (InvalidSchema) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:97: RNV000007 (MissingField) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:108: RNV000008 (FieldNotAllowed) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:154: RNV000012 (InvalidIdempotencyKey) declarado e nunca levantado  
- observação (fora da contagem): transferencias/src/errors/custom\_errors.py:264: RNV001027 (AdminForbidden) declarado e nunca levantado

### COD-04 · Só testes de integração black-box — ❌

- contagem: 516/516 testes de integração black-box  
- falha: banco/tests/integration/client/test\_client\_create.py: usa TestClient  
- falha: banco/tests/integration/client/test\_client\_me.py: usa TestClient  
- falha: banco/tests/integration/middleware/test\_client\_auth.py: usa TestClient  
- falha: transferencias/tests/integration/middleware/test\_client\_auth.py: usa TestClient

### COD-05 · Entidade com `id` e `*_key` — ❌

- contagem: 4/8 entidades com id PK, \*\_key unique e FK por id  
- falha: banco/database/database.sql:91: `api_token`: sem coluna `*_key` própria  
- falha: banco/database/database.sql:157: `entry`: sem coluna `*_key` própria  
- falha: transferencias/database/database.sql:94: `payment`: `client_key` referencia `client` por chave (transferencias/database/database.sql:97); a referência deve ser por `id`; `company_key` referencia `company` por chave (transferencias/database/database.sql:98); a referência deve ser por `id`; `account_key` referencia `account` por chave (transferencias/database/database.sql:99); a referência deve ser por `id`; `transaction_key` referencia `transaction` por chave (transferencias/database/database.sql:105); a referência deve ser por `id`  
- falha: transferencias/database/database.sql:114: `payout`: `company_key` referencia `company` por chave (transferencias/database/database.sql:117); a referência deve ser por `id`; `account_key` referencia `account` por chave (transferencias/database/database.sql:118); a referência deve ser por `id`; `transaction_key` referencia `transaction` por chave (transferencias/database/database.sql:125); a referência deve ser por `id`  
- outro 1 ponto: não foi possível verificar este item.  
- observação (fora da contagem): banco/database/database.sql:52: `allowed_transition` (associativa pura, não é entidade)  
- observação (fora da contagem): transferencias/database/database.sql:28: `payment_transition` (associativa pura, não é entidade)  
- observação (fora da contagem): transferencias/database/database.sql:67: `payout_transition` (associativa pura, não é entidade)

### COD-06 · Enum com tabela auxiliar — ✅

- contagem: 12/12 colunas enumeradoras com tabela auxiliar

### COD-07 · Status registrado em `*_status_event` — ❌

- contagem: 4/7 entidades com status e \*\_status\_event  
- falha: banco/database/database.sql:52: `allowed_transition` tem `from_status_id` e nenhuma tabela `*_status_event`  
- falha: transferencias/database/database.sql:28: `payment_transition` tem `from_status_id` e nenhuma tabela `*_status_event`  
- falha: transferencias/database/database.sql:67: `payout_transition` tem `from_status_id` e nenhuma tabela `*_status_event`

### COD-08 · Testes não importam src — ✅

- contagem: 145/145 arquivos de teste sem import de src

### COD-09 · Sem chamada entre camadas irmãs — ✅

- contagem: 42/42 arquivos de camada sem chamada à camada irmã

### COD-10 · Rotas REST no singular — ❌

- contagem: 7/31 rotas de domínio na forma REST  
- falha: banco/src/app.py:71: POST /clients: `clients` no plural num POST  
- falha: banco/src/app.py:73: POST /companies: `companies` no plural num POST  
- falha: banco/src/app.py:74: GET /companies/{company\_key}: `companies` no plural fora do último segmento  
- falha: banco/src/app.py:75: POST /ledger/transactions: `transactions` no plural num POST  
- falha: banco/src/app.py:76: GET /internal/ledger/receipts: `/internal` não é recurso REST (régua v2.6: ponto negativo); GET no plural `receipts` sem paginação (limit/page/offset)  
- falha: banco/src/app.py:77: POST /companies/{company\_key}/accounts: `companies` no plural num POST; `accounts` no plural num POST  
- falha: banco/src/app.py:78: GET /accounts/{account\_key}: `accounts` no plural fora do último segmento  
- falha: banco/src/app.py:79: GET /accounts/{account\_key}/balance: `accounts` no plural fora do último segmento  
- falha: banco/src/app.py:80: GET /accounts/{account\_key}/statement: `accounts` no plural fora do último segmento  
- falha: banco/src/app.py:81: POST /accounts/{account\_key}/close: `accounts` no plural num POST  
- falha: banco/src/app.py:82: POST /internal/accounts/{account\_key}/block: `/internal` não é recurso REST (régua v2.6: ponto negativo); `accounts` no plural num POST  
- falha: banco/src/app.py:83: POST /internal/accounts/{account\_key}/unblock: `/internal` não é recurso REST (régua v2.6: ponto negativo); `accounts` no plural num POST  
- falha: banco/src/app.py:84: GET /internal/internal-accounts: `/internal` não é recurso REST (régua v2.6: ponto negativo); GET no plural `internal-accounts` sem paginação (limit/page/offset)  
- falha: banco/src/app.py:89: GET /admin/internal-accounts: GET no plural `internal-accounts` sem paginação (limit/page/offset)  
- falha: transferencias/src/app.py:77: POST /payments: `payments` no plural num POST  
- falha: transferencias/src/app.py:79: GET /payments/{payment\_key}: `payments` no plural fora do último segmento  
- falha: transferencias/src/app.py:80: POST /payments/{payment\_key}/refund: `payments` no plural num POST  
- falha: transferencias/src/app.py:81: POST /payouts: `payouts` no plural num POST  
- falha: transferencias/src/app.py:82: GET /payouts/{payout\_key}: `payouts` no plural fora do último segmento  
- falha: transferencias/src/app.py:83: GET /internal/accounts/{account\_key}/in-flight: `/internal` não é recurso REST (régua v2.6: ponto negativo); `accounts` no plural fora do último segmento  
- falha: transferencias/src/app.py:84: POST /internal/payouts/reconcile: `/internal` não é recurso REST (régua v2.6: ponto negativo); `payouts` no plural num POST  
- falha: transferencias/src/app.py:85: POST /internal/receipts/reconcile: `/internal` não é recurso REST (régua v2.6: ponto negativo); `receipts` no plural num POST  
- falha: transferencias/src/app.py:86: POST /internal/settlements: `/internal` não é recurso REST (régua v2.6: ponto negativo); `settlements` no plural num POST  
- falha: transferencias/src/app.py:87: PUT /internal/payment-methods/{method}: `/internal` não é recurso REST (régua v2.6: ponto negativo); `payment-methods` no plural num PUT  
- observação (fora da contagem): banco/src/app.py:85: GET /auth/me: `auth` é ação, sub-recurso ou agrupamento (isento)

### COD-11 · Commit só no fim do controller — ❌

- contagem: 9/14 métodos com commit conforme  
- falha: transferencias/src/controllers/payout\_reconcile\_controller.py:101 `_attempt`: commit em método privado do controller  
- falha: transferencias/src/controllers/payout\_reconcile\_controller.py:158 `_finish`: commit em método privado do controller  
- falha: transferencias/src/controllers/settlement\_controller.py:69 `_release`: commit em método privado do controller  
- outros 2 pontos: não foi possível verificar este item.

### COD-12 · Rota não-GET com JSON schema — ❌

- contagem: 0/9 rotas não-GET com corpo e com json schema  
- falha: banco/src/app.py:71: POST /clients: `on_post` recebe corpo sem json schema  
- falha: banco/src/app.py:73: POST /companies: `on_post` recebe corpo sem json schema  
- falha: banco/src/app.py:75: POST /ledger/transactions: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:77: POST /payments: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:81: POST /payouts: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:84: POST /internal/payouts/reconcile: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:85: POST /internal/receipts/reconcile: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:86: POST /internal/settlements: `on_post` recebe corpo sem json schema  
- falha: transferencias/src/app.py:87: PUT /internal/payment-methods/{method}: `on_put` recebe corpo sem json schema  
- observação (fora da contagem): banco/src/app.py:77: POST /companies/{company\_key}/accounts: rota sem corpo, não precisa de schema (handler `on_post` em banco/src/resources/account.py:11)  
- observação (fora da contagem): banco/src/app.py:81: POST /accounts/{account\_key}/close: rota sem corpo, não precisa de schema (handler `on_post_close` em banco/src/resources/account.py:31)  
- observação (fora da contagem): banco/src/app.py:82: POST /internal/accounts/{account\_key}/block: rota sem corpo, não precisa de schema (handler `on_post_block` em banco/src/resources/account.py:36)  
- observação (fora da contagem): banco/src/app.py:83: POST /internal/accounts/{account\_key}/unblock: rota sem corpo, não precisa de schema (handler `on_post_unblock` em banco/src/resources/account.py:41)  
- observação (fora da contagem): transferencias/src/app.py:80: POST /payments/{payment\_key}/refund: rota sem corpo, não precisa de schema (handler `on_post_refund` em transferencias/src/resources/payment.py:33)

### COD-13 · Connector testado via MockServer — ❌

- contagem: 0/4 endpoints de connector verificados no MockServer  
- falha: banco/src/connectors/transferencias\_connector.py:12: GET /internal/accounts/{}/in-flight: sem MockServer no compose  
- falha: transferencias/src/connectors/bank\_connector.py:28: POST /ledger/transactions: sem MockServer no compose  
- falha: transferencias/src/connectors/bank\_connector.py:49: GET /internal/ledger/receipts: sem MockServer no compose  
- falha: transferencias/src/connectors/interbank\_connector.py:29: POST /interbank/transfers: o provedor é o `.py` solto `external-mocks/`, não o MockServer (régua v2.7/v2.10: falha)  
- observação (fora da contagem): ponto negativo: provedor externo simulado por `.py` solto em `external-mocks/` (deveria ser o MockServer)  
- observação (fora da contagem): transferencias/src/connectors/bank\_connector.py:12: GET /auth/me (`get_client_identity` não é chamado por nenhuma rota)

### COD-14 · Testes não acessam o banco — ✅

- contagem: 146/146 arquivos de teste sem acesso a dado de negócio

### RFC-01 · RFC fiel à implementação — ⏸

- contagem: 67/68 afirmações da RFC que batem  
- não foi possível verificar este item.  
- observação (fora da contagem): omissão \[rota\] banco/src/app.py:72: `GET /me` existe e o texto legível da RFC não o cita; a RFC só fala em `GET /auth/me`.  
- observação (fora da contagem): omissão \[rota\] banco/src/app.py:84: `GET /internal/internal-accounts` existe e a RFC cita só `GET /admin/internal-accounts`.  
- observação (fora da contagem): omissão \[estado\] banco/database/database.sql:21: O status `created` da conta existe e a RFC só descreve active, rejected, blocked e closed.  
- observação (fora da contagem): omissão \[db\] banco/database/database.sql:52: As tabelas de transição (`allowed_transition`; `payment_transition` e `payout_transition` em transferencias/database/database.sql:28,67) não aparecem no texto legível da RFC.