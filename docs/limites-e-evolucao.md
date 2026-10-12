# Limites conhecidos e caminho de evolução

Status: vivo; atualize a coluna de status quando um degrau for aplicado.

> Escopo: a arquitetura atual (dois serviços, HTTP síncrono + idempotência), que é uma decisão consciente da RFC (§1 "Arquitetura" e §6 "Saga, fila ou processamento assíncrono"). Este documento não discute o desenho do livro; só registra onde ele para de escalar e o que fazemos depois. Fontes: `catalogo-de-erros.md`, `rotas.md`, `mocks-externos.md` e o código citado em cada seção.

## 1. Resumo

- **Sustentável hoje:** o volume de um bootcamp e de um produto em estágio inicial. O fluxo é simples de raciocinar, de testar e de defender.
- **Degrada com volume:** a conexão do banco do Transferências fica presa durante a chamada HTTP ao Banco, e a disponibilidade do Transferências depende da do Banco.
- **O que não depende de escala:** a corretude do dinheiro. Ela vem da chave determinística no lançamento, do `UNIQUE` e do lock `FOR UPDATE` no débito. Lento ou fora do ar, o sistema pode recusar ou atrasar, mas não lança duas vezes nem deixa saldo negativo.
- **O pior caso real é o "resultado desconhecido":** um timeout no `POST /payments` não prova que o dinheiro não se moveu (seção 2).
- **Lacuna aberta:** não existe reconciliação periódica Transferências × Banco. É o primeiro item a construir se o produto crescer.

## 2. O que acontece quando o Banco não responde no `POST /payments`

Pergunta: "rollback ou resposta negativa?" Resposta: **as duas coisas**, e nenhuma delas diz que o dinheiro não se moveu.

Fluxo atual (`transferencias/src/controllers/payment_controller.py`, `create` e `_post_receipt`):

1. `try_create` faz o `INSERT` do `payment` (`flush`), com `idempotency_key` e `payload_hash`. É a primeira escrita (RFC §5.2).
2. `_post_receipt` chama `POST /ledger/transactions` no Banco com a chave `receipt:<company_key>:<chave>`.
3. Se o conector levanta `BankUnavailable` (erro de rede, timeout de `BANK_TIMEOUT_SECONDS = 5`, corpo que não é JSON, status diferente de 200/201 ou sem `transaction_key`), o controller faz `session.rollback()` e propaga.
4. O resource devolve `503 RNV001017`.

### Por que não guardamos uma linha `failed`

A RFC §5.2 item 5 é explícita: **erro não fica guardado**. O rollback desfaz o `INSERT` do `payment` e a chave do cliente fica livre para nova tentativa. As razões:

- `failed` só existe em `payout_status` (RFC §6, "`failed` no status do livro"). O `payment` tem `held`/`settled`/`refunded`; criar um estado só para "o Banco não respondeu" abriria transições novas (`failed` → ?) e um estado que o cliente teria de interpretar.
- Uma linha `failed` com a chave ocupada obrigaria o retry a gerar outra chave, ou a regra "mesma chave reabre o `failed`", o que contradiz "a chave é do cliente e o banco não adivinha intenção".
- Sem a linha, o retry com a mesma chave é uma operação nova e limpa, que reencontra o lançamento no Banco se ele existir.

Consequências aceitas:

| Consequência | Efeito |
|---|---|
| Não há rastro local da tentativa que falhou | Só o log da requisição mostra que ela existiu. |
| A chave fica livre | O cliente retenta com a mesma `Idempotency-Key` sem atrito. |
| O Transferências pode não saber o que o Banco fez | É o caso do próximo bloco. |

### O 503 significa "resultado desconhecido", não "não aconteceu"

`503 RNV001017` quer dizer: **retente com a MESMA `Idempotency-Key`**. Não quer dizer que o dinheiro com certeza não se moveu. Há dois cenários:

| Cenário | Banco | Transferências | O que o retry faz |
|---|---|---|---|
| A. O Banco não chegou a commitar (rede caiu antes, Banco fora do ar) | sem receipt | sem `payment` | Fluxo normal: grava `payment`, lança o receipt, `201`. |
| B. O Banco commitou o receipt, mas a resposta se perdeu (timeout de 5 s, conexão cortada) | receipt `receipt:<company_key>:<chave>` existe, `settled`, em `in_transit` | `payment` sofreu rollback, não existe | O Banco recebe a mesma chave e o mesmo `payload_hash`, devolve o lançamento existente (`200`, `_replay` em `banco/src/controllers/ledger_controller.py`). O Transferências grava o `payment` e fecha a conta. Nenhum lançamento duplicado. |

Cenário B é a razão de a chave do lançamento ser determinística e derivada da chave do cliente (RFC §5.2, "As chaves dos lançamentos no Banco").

### Receipt órfão se o cliente nunca retentar: reconciliado

Se no cenário B o cliente **não retentar**, sobra no Banco um receipt `settled` (D `reserves` / C `in_transit`) sem `payment` correspondente no Transferências. O livro fecha, nenhum lojista é afetado, mas o valor fica parado no `in_transit`.

**Mitigação (2026-10-12):** o job `POST /internal/receipts/reconcile` do Transferências pagina `GET /internal/ledger/receipts` no Banco (recebimentos sem `settlement` nem `refund`, criados antes de `as_of - RECEIPT_ORPHAN_GRACE_HOURS`, padrão 24 h), filtra os de chave `receipt:` sem `payment` local e lança um `refund` (D `in_transit` / C `reserves`, chave `orphan-refund:<transaction_key>`). Contrato em `rotas.md`.

- **Por que estorno e não criar a venda depois:** o lançamento no Banco não guarda o meio de pagamento, então não dá para reconstruir o `payment` (taxa e janela dependem dele). Do lado do lojista a venda falhou (`503`) e ele não retentou; devolver o valor é o caminho seguro.
- **Retry depois do estorno:** a chave do cliente nunca expira. Para que um retry tardio não crie uma venda sobre um recebimento estornado, o Banco devolve `reversed: true` no replay e o `POST /payments` recusa com `409 RNV001038`, sem gravar o `payment`. A chave fica queimada.
- **Resíduo aceito:** se o retry tardio receber o replay do Banco **antes** do estorno e commitar o `payment` **depois** da checagem local do job, nasce um `payment` `held` sobre um recebimento estornado: não libera (`RNV001014` no settlement) nem estorna. Nenhum dinheiro se cria ou se perde (o livro fecha), mas o `payment` fica parado. Exige um retry exatamente na janela de milissegundos entre a listagem e o estorno, depois de 24 h de carência. Fechar a janela exigiria uma trava comum (por exemplo, advisory lock por `company_key` + chave) entre o job e o `POST /payments`.
- **Custo:** a listagem inclui os recebimentos de vendas `held` ainda na janela (até 720 h de cartão) e qualquer `receipt` lançado direto no ledger; o job lê tudo isso a cada run, 100 por página.

### Inconsistência: o texto do `RNV001017`

O catálogo (`docs/catalogo-de-erros.md`, linha do `RNV001017`) diz "Banco indisponível (nada foi gravado)", e `transferencias/src/errors/custom_errors.py` (`BankUnavailable`) diz "The bank service is unavailable; nothing was recorded." / "O Banco está indisponível; nada foi gravado."

Isso é verdade **no Transferências** e impreciso no timeout: o Banco pode ter gravado o receipt (cenário B). Redação adotada (aplicada em 2026-10-11, com aprovação do usuário, no catálogo e em `custom_errors.py`):

| Onde | Redação proposta |
|---|---|
| Catálogo | Banco indisponível ou sem resposta; nada foi gravado no Transferências, e o resultado no Banco pode ser desconhecido. Retente com a mesma `Idempotency-Key`. |
| `description` (en) | The bank service is unavailable or did not answer in time; nothing was recorded in this service and the outcome at the bank may be unknown. Retry with the same Idempotency-Key. |
| `translation` (pt) | O Banco está indisponível ou não respondeu a tempo; nada foi gravado neste serviço e o resultado no Banco pode ser desconhecido. Retente com a mesma Idempotency-Key. |

O código `RNV001017` não muda (o catálogo diz que número é contrato estável); só o texto. Mudar texto de erro é decisão do grupo (CLAUDE.md); esta foi aprovada.

## 3. Limites conhecidos

### (a) Conexão do banco presa durante a chamada HTTP ao Banco

- **O que é:** em `create`, a sessão abre a transação na primeira consulta (`get_method`), faz o `flush` do `payment`, chama o Banco e só então dá `commit`. A conexão do pool fica emprestada durante toda a chamada HTTP. Isso é intencional: o `INSERT` com a chave é a primeira escrita e o commit só acontece depois do receipt (RFC §5.2).
- **Por que existe:** é o que faz o rollback desfazer tudo e liberar a chave, sem estado intermediário.
- **Números do código:**
  - `transferencias/src/database.py` usa `pool_size=DB_POOL_SIZE`, `max_overflow=DB_MAX_OVERFLOW` e `pool_timeout=DB_POOL_TIMEOUT_SECONDS`, lidos de `constants.py` por variável de ambiente. Padrões: 10, 10 e 3 s. Total: **10 + 10 = 20 conexões** por instância. (Antes do degrau 1b eram 5 + 10 = 15 conexões e `pool_timeout` de 30 s, padrão da biblioteca.)
  - `transferencias/src/constants.py`: `BANK_TIMEOUT_SECONDS = float(os.environ.get("BANK_TIMEOUT_SECONDS", "5"))`, passado como `timeout=` do `requests`. Esse valor vale para conexão e para leitura **separadamente**, então o pior caso de uma chamada pode passar de 5 s (até ~10 s em teoria).
  - Os resources são `def` síncronos; o FastAPI os roda no threadpool do Starlette, cujo limite padrão é **40 threads** (padrão da biblioteca, não configurado no repositório). O Dockerfile sobe `uvicorn` sem `--workers`, ou seja, 1 processo por instância.
- **Conta de vazão por instância (estimativa):** cada `POST /payments` ocupa 1 conexão pelo tempo da chamada ao Banco, `T`. Vazão máxima de escrita ≈ conexões ÷ `T`.

  | Cenário | `T` | Conta | Vazão máxima |
  |---|---|---|---|
  | Pior caso, Banco travado até o timeout | 5 s | 20 ÷ 5 | **4 pagamentos/s** |
  | Pior caso teórico (conectar 5 s + ler 5 s) | 10 s | 20 ÷ 10 | 2 pagamentos/s |
  | Banco saudável, `T` suposto de 50 ms (**suposição, não medida**) | 0,05 s | 20 ÷ 0,05 | até 400 pagamentos/s, teto teórico que ignora o tempo de consulta ao banco e a CPU |

- **Efeito cascata:** com 20 conexões presas, qualquer outra requisição que precise do banco do Transferências (`GET /payments/{key}`, e os jobs futuros) espera uma conexão por no máximo 3 s (`DB_POOL_TIMEOUT_SECONDS`) e, ao estourar, recebe `503 RNV000006` (Service Busy). O handler em `transferencias/src/app.py` mapeia `sqlalchemy.exc.TimeoutError` para esse código; antes do degrau 1b a espera era de até 30 s e o erro caía em `500`. As 40 threads do servidor ainda excedem as 20 conexões, então até 20 requisições ficam bloqueadas esperando conexão, agora por no máximo 3 s cada, e o servidor perde capacidade para o resto nesse intervalo. `GET /health_check` não toca no banco e só sofre se as 40 threads estiverem ocupadas. `GET /auth/me` roda em thread (`run_in_threadpool` no middleware), usa a thread por até 5 s, mas não usa conexão do banco do Transferências.
- **Quando dói:** quando o Banco fica lento (não só fora do ar). Fora do ar costuma falhar rápido (conexão recusada); lento é o pior caso porque segura recursos por 5 s.
- **Mitigação hoje:** timeout do Banco (5 s por padrão, configurável) limita o dano; o pool falha rápido com `503 RNV000006` em vez de enfileirar; a idempotência torna seguro o retry do cliente (o 503 significa "retente"). Provado por `transferencias/tests/integration/payment/test_payment_service_busy.py` (marker `fault`, instância `transferencias-api-fault` com pool minúsculo, 100 requisições concorrentes).
- **Evolução:** degraus 1 e 2 da seção 4.

### (b) Acoplamento de disponibilidade com o Banco

- **O que é:** todo request de cliente no Transferências chama `GET /auth/me` no Banco (`middlewares/client_auth.py` → `BankConnector.get_client_identity`), e o `POST /payments` chama ainda `POST /ledger/transactions`. Sem o Banco, o Transferências não autentica ninguém: tudo responde `503 RNV001017`, inclusive leituras.
- **Por que existe:** a identidade tem um dono só (CLAUDE.md, "Tese da arquitetura"); duplicar a tabela de cliente foi descartado.
- **Quando dói:** indisponibilidade do Banco derruba os dois serviços do ponto de vista do cliente. Disponibilidade composta: se cada serviço tem 99,9%, o conjunto serial tem no máximo ≈ 99,8% (0,999 × 0,999 = 0,998; conta, não medição).
- **Mitigação hoje:** nenhuma além do timeout. Não há cache de identidade.
- **Evolução:** cache curto do resultado de `/auth/me` (TTL de segundos, invalidado por revogação; custo: janela em que um token revogado ainda passa, decisão de segurança do grupo), ou token verificável localmente (assinado). Ambos mudam o modelo de segurança do CLAUDE.md (token hasheado no banco, com `revoked_at`), então exigem decisão explícita.

### (c) Resultado desconhecido no timeout

Ver seção 2. Limite: o Transferências não sabe se o Banco commitou; o desfecho é resolvido pelo retry do cliente (idempotência) ou, se ele nunca vier, por uma reconciliação que não existe.

### (d) Conta quente no débito

- **O que é:** o débito faz `SELECT ... FOR UPDATE` na linha da `account`, soma o saldo depois de travar, confere e insere (`banco/src/controllers/ledger_controller.py`, `_ensure_funds`; RFC §5.1). Débitos da **mesma** conta fazem fila; contas diferentes seguem em paralelo.
- **Por que existe:** é o que impede o *lost update* sem guardar saldo na `entry`.
- **Quando dói:** um lojista com muitos saques simultâneos. Mil débitos na mesma conta viram uma fila de mil transações curtas (RFC §5.1, perguntas de estresse). Mais lento para aquela conta, nunca errado.
- **Mitigação hoje:** índice `(account_id, id) INCLUDE (debit_minor, credit_minor)` para o `SUM` ser index-only scan.
- **Evolução:** saldo materializado em linha **mutável e reconstruível**, atualizado na mesma transação com `UPDATE ... SET saldo = saldo + :delta WHERE saldo + :delta >= 0` (RFC §5.1). Nunca `balance_after` na `entry`.

### (e) Contas internas sem conferência de saldo no caminho da requisição

- **O que é:** `reserves`, `in_transit` e `revenue` nunca são travadas nem conferidas (`_ensure_funds` só considera contas com `company_id`). Elas crescem com o volume do sistema inteiro, então o `SUM` delas é o que quebra primeiro.
- **Por que existe:** travar uma conta tocada por toda transação serializaria o sistema (RFC §5.1 item 5).
- **Controle relacionado:** `account_key` de conta interna é recusado com `422 RNV001034`; elas só entram por `account_code`, o que impede o cliente de movimentar o Caixa ou o Trânsito.
- **Quando dói:** quando alguém precisar saber o saldo de `in_transit` ou `reserves` em tempo real. Hoje nada no caminho da requisição depende disso.
- **Mitigação:** reconciliação em lote, com *checkpoint* se o volume pedir (RFC §5.1). **Esse job também não existe hoje**; a equação `Caixa = Trânsito + Clientes + Receita` (RFC §1) é verificável por consulta, mas ninguém a executa periodicamente.
- **Evolução:** job de reconciliação com checkpoint; depois, saldo materializado para as internas.

### (e2) `GET /admin/internal-accounts` agrega a tabela `entry` inteira

- **O que é:** a cada chamada, a rota soma `debit_minor`/`credit_minor` de todas as `entry` das contas internas para devolver os totais e a equação do livro. O custo é O(n) no tamanho do livro e cresce com o volume.
- **Evolução:** saldo materializado em linha **mutável e reconstruível**, atualizado na mesma transação com incremento atômico (nunca `balance_after`), conforme a seção (e).

### Paginação das rotas admin: cursor opaco assinado

- `GET /admin/clients`, `/admin/companies` e `/admin/accounts` paginam por **cursor opaco assinado** (HMAC-SHA256 com `CURSOR_SECRET`), o mesmo padrão do extrato (`utils/cursor.py`). O cursor nunca é uma chave pública; cursor adulterado, inventado ou vazio devolve `400 RNV000011`.
- O envelope é `{data, limit, cursor, is_last_page}`; `cursor` é `null` na última página.
- Trocar `CURSOR_SECRET` invalida os cursores em circulação (aceitável: o cliente recomeça a listagem).

### (f) Mocks em memória e `as_of` fora da RFC

- **Mocks:** o `external-mocks` guarda `transfer_id` e o contador do cenário `flaky` em memória; reiniciar o container zera tudo (`mocks-externos.md`, "Limites aceitos"). O risco "o mock pagou, mas a resposta se perdeu" não existe aqui; contra um banco real, a RFC §2 o registra como risco aceito (consultar o status no destino antes do `failed` por timeout). O birô ainda é um mock dentro do Banco.
- **`as_of`:** corpo opcional de `POST /internal/settlements` e `POST /internal/payouts/reconcile`, que injeta o "agora". **Não está na RFC v7.2**, que só fala em "o relógio" (`rotas.md`, notas finais). Só vale com `INTERNAL-TOKEN` e existe para testar sem esperar a janela (24h/72h/720h) e o backoff. Risco: um operador com o token pode antecipar a liberação de um pagamento; é um refino que precisa de aprovação do grupo e de ficar fora do caminho do cliente (hoje já é).
- **Evolução:** trocar o mock por integração real exige a consulta de status no destino; `as_of` entra na RFC ou sai quando houver um relógio injetável de outra forma.

### (g) Outros limites reais

| Limite | O que é | Fonte |
|---|---|---|
| Reconciliação depende de agendador | Receipt órfão (seção 2) e payout em `pending` têm job, mas nada os chama sozinho; a equação do livro só é conferida quando alguém consulta o admin. | RFC §2 passo 7; `rotas.md` |
| Retry reflete o estado atual | Um retry tardio de `POST /payments` volta o estado de agora (por exemplo `settled`), e `200` em vez de `201`. É decisão, mas surpreende quem espera uma foto da resposta original. | RFC §5.2 item 4 |
| `payload_hash` só cobre `company_key`, `amount_minor`, `method` | Mudar outro campo com a mesma chave não é detectado como reuso. Hoje esses são todos os campos que definem o pedido. | `payment_controller.py`, `_meaningful_fields` |
| Chave do cliente limitada a 50 caracteres | Vem do composto `receipt:<company_key>:<chave>` = 95 de 100. Aumentar a chave exige aumentar a coluna do Banco. | RFC §5.2 "Tamanhos coordenados" |
| Fila de payout com o mock | A espera do backoff do payout depende de um job chamado de fora; sem agendador, ninguém chama. | RFC §2 passo 7 |
| Reconcile é um job global | `POST /internal/payouts/reconcile` varre todos os payouts `pending` de todas as empresas numa chamada; o custo cresce com a base. O teto `PAYOUT_MAX_PER_RUN` (50) limita o trabalho por run, mas a lista de candidatos `pending` é lida inteira (uma query com `COUNT` e último resultado por payout) antes do corte, e o resto espera o próximo run. Cada timeout segura a linha do payout e uma conexão do pool por até 5 s, então um run cheio de timeouts pode levar minutos (50 x 5 s). Evolução: filtrar o vencimento do backoff na query, fatiar por empresa/shard, paralelizar com `SKIP LOCKED` e agendar o job. | `payout_reconcile_controller.py` |
| Reconciliação de payout depende de agendador | Nada chama o job sozinho; sem cron/agendador, payouts ficam `pending`. `as_of` existe só para testar o backoff. | RFC §2 passo 7 |
| Payout `pending` com conta bloqueada | Se settlement/reversal é recusado (`RNV001005`) ou o Banco cai, o payout fica `pending` indefinidamente (não vira `failed` sem reversal) até alguém desbloquear a conta; o run só o reporta em `pending`. Sem alerta nem limite de idade. | `rotas.md`, fases do reconcile |
| Sem observabilidade de saturação | Não há métrica de uso do pool nem de latência do Banco. Sem ela, os números da seção 3(a) não podem ser validados. | (ausência no código) |
| Isolamento READ COMMITTED é regra | Mudar para REPEATABLE READ quebra a conferência do débito. | RFC §5.1 item 6 |

### (h) Encerramento de conta: Banco consulta o Transferências (direção invertida)

- **Decisão consciente (opção B, tomada pelo usuário):** `POST /accounts/{key}/close` só encerra com saldo derivado zero **e** nada em voo no Transferências (payments `held` e payouts `pending` da conta). Recusa → `422 RNV001035`. A consulta de "em voo" é `GET /internal/accounts/{account_key}/in-flight` (`INTERNAL-TOKEN`), que devolve `{"held_payments": n, "pending_payouts": n}`. É a **única** chamada Banco → Transferências; todas as outras vão no sentido contrário.
- **Ordem no controller:** trava a linha da `account` (`FOR UPDATE`, READ COMMITTED) → status `active` (`409 RNV001009`) → saldo (lido depois do lock) → consulta in-flight → muda o status → commit. O lock fica retido durante a chamada HTTP; débitos concorrentes na mesma conta esperam e, ao entrar, enxergam a conta `closed`.
- **Fail-closed:** Transferências fora, lento (`TRANSFERENCIAS_TIMEOUT_SECONDS`, padrão 5), resposta não-200 ou corpo fora do contrato → `503 RNV001036`, nada muda e a conta continua `active`. Nunca fecha na dúvida. Até 2026-10-12 esse caso reaproveitava o `RNV000006` ("Service Busy"); a decisão mudou e ele ganhou código próprio, espelho do `RNV001017`, deixando o `RNV000006` só para pool esgotado.
- **Riscos aceitos:**
  - **Acoplamento circular de disponibilidade:** o Transferências já depende do Banco (`/auth/me`, ledger); agora o `close` do Banco depende do Transferências. Sem Transferências, ninguém encerra conta (o resto do Banco segue de pé). Não há dependência circular no startup (`banco-api` não tem `depends_on` do Transferências).
  - **Lock durante HTTP:** até `TRANSFERENCIAS_TIMEOUT_SECONDS` segundos com a linha da conta travada e uma conexão do Banco presa; débitos da mesma conta esperam. Escopo limitado a uma conta que o titular está encerrando.
  - **Janela de criação de payment:** o `POST /payments` lê o status da conta no início da requisição (`/auth/me`) e o crédito do `receipt` vai para `in_transit`, uma conta interna que não toca a linha do cliente nem espera o lock. Logo um payment aceito antes do commit do `close` pode não aparecer na consulta in-flight (a linha ainda não está commitada) e a conta fecha com um payment `held`. O guard de conta `active` do `POST /payments` mitiga só quem começa depois do commit. Consequência: no settlement o crédito para a conta `closed` seria recusado pelo ledger (`RNV001005`) e o payment ficaria `held` até um refund. É o resíduo da opção B; fechar a janela exigiria o Transferências travar algo da conta durante o `POST /payments`, o que não existe hoje.
  - **Sem índice** em `payment(account_key, status_id)` e `payout(account_key, status_id)`: a contagem faz varredura. Pedir ao Wren se o volume crescer.
- **Bloqueio (`block`) não move dinheiro:** o saldo fica congelado na conta do titular, sem débito, como passivo do banco perante o titular. Para fundos bloqueados por fraude ou ordem judicial, o destino do dinheiro é evolução (por exemplo uma conta interna `held_funds`).
- **Payout `pending` de conta bloqueada:** fica parado em `in_transit` até o `unblock`; o dinheiro já saiu da conta do titular e ainda não saiu do banco.

### (i) Padrão de paginação: cursor opaco assinado

- **Padrão do projeto (decisão do usuário):** paginação por **cursor opaco assinado** (keyset por `id` interno, `id < before_id`). O cursor é `base64url("<id>.<HMAC-SHA256 hex>")` com o segredo `CURSOR_SECRET`; o id interno não vai em claro nem é forjável. Envelope `{"data": [...], "limit": n, "cursor": <opaco ou null>, "is_last_page": bool}`; `limit` de 1 a 100. Cursor adulterado, inventado ou malformado → `400 RNV000011`. Origem: extrato da Victoria (#18, `banco/src/utils/cursor.py`); no Transferências a cópia isolada é `src/utils/cursor.py` e a primeira rota é `GET /payments`.
- **Por que cursor:** o offset repete ou pula linha quando entra item novo entre duas páginas; o keyset não escorrega.
- **A alinhar:** as listagens admin da Natalia (#21) usam a **chave pública** como cursor e devem migrar para o cursor opaco assinado.

## 4. Caminho de evolução em degraus

| Degrau | O que muda | Custo | Muda o contrato da RFC? | Status |
|---|---|---|---|---|
| 1a | `BANK_TIMEOUT_SECONDS` configurável por variável de ambiente (float, padrão 5, em `constants.py`). O padrão não mudou; agora dá para baixar sem alterar código. Trade-off: timeout menor segura menos conexão, mas aumenta a chance de "resultado desconhecido" (cenário B) em Banco lento. Ainda em aberto: timeouts separados de conexão e de leitura. | Muito baixo | Não | aplicado em 2026-10-11, branch `chore/bank-timeout-and-pool-busy` |
| 1b | Pool configurável (`DB_POOL_SIZE` 10, `DB_MAX_OVERFLOW` 10, `DB_POOL_TIMEOUT_SECONDS` 3 por padrão; 20 conexões para 40 threads) e `pool_timeout` curto: falha rápido em até 3 s em vez de enfileirar até 30 s. A decisão de código novo foi tomada: `RNV000006` (503 "Service Busy", genérico), levantado quando o pool estoura dentro do prazo, mapeado em `app.py` a partir de `sqlalchemy.exc.TimeoutError`. O 503 significa "retente". Dimensionar o pool contra as threads do servidor continua sendo ajuste a medir. | Baixo | Sim, um código novo no catálogo (aprovado) | aplicado em 2026-10-11, branch `chore/bank-timeout-and-pool-busy` |
| 1c | Circuit breaker no `BankConnector`: após N falhas, responde `503` direto por X segundos sem chamar o Banco. Protege o pool em Banco lento. Pode não valer a complexidade nesta escala: com timeout de 5 s, 20 conexões e `pool_timeout` de 3 s o sistema já se auto-limita, e um breaker adiciona estado, configuração e casos de teste (aberto, meio-aberto, fechado). Vale se o Banco passar a ter lentidão frequente. | Baixo a médio | Não | não aplicado |
| 1d | Reconciliação periódica Transferências × Banco para receipt órfão (seção 2) e verificação da equação do livro (3e). | Médio | Não, é job novo | receipt órfão aplicado (`POST /internal/receipts/reconcile`, 2026-10-12); a equação é exposta no admin, sem job |
| 2 | Não segurar a conexão durante a chamada HTTP: gravar o `payment` com estado intermediário (por exemplo `pending_ledger`), commitar, chamar o Banco sem conexão emprestada, e promover a `held` depois. Um job de recuperação reprocessa os `pending_ledger` antigos reusando a chave `receipt:...`. Elimina a cascata do 3(a) e o receipt órfão, porque o `payment` passa a existir antes da chamada. | Médio: novo estado e transições em `payment_transition`, job, testes de falha no meio | Parcial: novo estado do `payment` (a RFC fixa `held`/`settled`/`refunded`) e o `201` passa a significar "aceito", não "lançado". Exige decisão explícita. | não aplicado |
| 3 | Outbox assíncrono com `202`: o Transferências grava o pedido e um evento na mesma transação; um *worker* entrega ao Banco com retry. Larga escala: o Transferências deixa de depender da disponibilidade do Banco para aceitar o pedido. | Alto: worker, outbox, observabilidade, consistência eventual no produto | **Sim**: contradiz a decisão "sem saga, sem fila" (RFC §6) e muda a resposta de `201` para `202`. Exige decisão explícita do grupo e nova versão da RFC. | não aplicado |

Ordem sugerida: 1a e 1b já aplicados; 1d antes de ter volume real, 2 quando a cascata aparecer em medição, 3 só com requisito de escala que o justifique.

## 5. Como defender isso numa entrevista

- **É decisão, não esquecimento.** A RFC §6 descarta saga, fila e processamento assíncrono de propósito: "corretude do saldo vale mais que vazão". O custo (vazão limitada por instância, acoplamento ao Banco) está escrito aqui com números.
- **O que a escala não quebra:** o dinheiro. Chave determinística no lançamento, `UNIQUE` na entidade e `FOR UPDATE` no débito valem com 1 ou 1.000 instâncias. O pior que o volume faz é recusar ou atrasar.
- **O limite real e honesto:** conexão presa na chamada ao Banco (20 conexões por instância, 4 pagamentos/s no pior caso de Banco travado, conta na seção 3a; o pool já falha em 3 s com `503 RNV000006`) e o resultado desconhecido no timeout, com a reconciliação ainda inexistente.
- **O 503 é "retente com a mesma chave", não "falhou".** Por isso não guardamos `failed`: a idempotência reencontra o receipt no Banco e fecha a conta. Reconhecemos que o texto do `RNV001017` ("nada foi gravado") merece ajuste.
- **Próximo passo:** o degrau 1 (timeout configurável, `pool_timeout` curto, `RNV000006`) já está aplicado; falta a reconciliação; degrau 2 se a medição mostrar cascata; degrau 3 só com mudança explícita da RFC.
