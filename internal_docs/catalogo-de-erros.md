# Catálogo de erros — RNV

> Fonte da verdade dos códigos de erro. Alinhado com o documento de Rotas v7 e a RFC v7.2.
> Formato da resposta: `{ title, description, translation, code }`.
> `RNV000xxx` = genéricos (schema, auth). `RNV001xxx` = regra de negócio.
> Números são contrato estável: não renumerar. `RNV001011` está reservado (sem uso).

## Genéricos

| Código | HTTP | Mensagem |
|---|---|---|
| RNV000001 | 400 | Corpo, filtro ou cursor fora do schema (inclui Idempotency-Key ausente) |
| RNV000002 | 403 | INTERNAL-TOKEN ausente ou errado |
| RNV000003 | 401 | Token ausente, inválido ou revogado |
| RNV000004 | 404 | Rota inexistente |
| RNV000005 | 405 | Método HTTP não permitido para a rota |

## Integração entre serviços

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001017 | 503 | Banco indisponível (nada foi gravado); levantado pelo Transferências |

## Cadastro (cliente / empresa)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001001 | 409 | CPF já cadastrado |
| RNV001002 | 422 | CPF com dígitos inválidos |
| RNV001028 | 409 | E-mail já cadastrado |
| RNV001029 | 422 | Pessoa menor de idade |
| RNV001019 | 409 | CNPJ já cadastrado |
| RNV001020 | 422 | CNPJ inválido (formato ou dígitos) |
| RNV001018 | 404 | Empresa inexistente ou de outro dono |
| RNV001022 | 409 | Empresa já possui conta aberta |

## Conta

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001021 | 404 | Conta inexistente ou de outro dono |
| RNV001030 | 403 | Empresa sem conta aberta |
| RNV001031 | 403 | Conta não está active (bloqueia só escrita) |
| RNV001005 | 422 | Conta fora de active (guard interno do ledger) |
| RNV001012 | 409 | Conta ainda tem saldo (encerre após sacar) |
| RNV001009 | 409 | Conta não está active — não pode bloquear nem encerrar |
| RNV001010 | 409 | Conta não está blocked (não pode desbloquear) |

> **Leitura passa sempre.** `GET /balance` e `GET /statement` respondem mesmo com a conta
> `blocked` ou `closed` — o padrão de banco é deixar o titular ver saldo e extrato de uma conta
> fechada/bloqueada. O guard de conta `active` (`RNV001031`) vale **só para escrita** (criar
> pagamento, criar payout). Logo esses dois códigos nunca aparecem em rota de leitura.

## Ledger (transações / entries)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001015 | 422 | Lançamentos não fecham (débito ≠ crédito) |
| RNV001006 | 422 | Saldo insuficiente |
| RNV001014 | 409 | Transação já consumida ou estornada (saída única) |
| RNV001016 | 404 | Transação referenciada inexistente |
| RNV001024 | 422 | Idempotency-Key reusada com conteúdo diferente |

## Pagamento (venda)

Erros possíveis no `POST /payments`: `RNV000003` (token ausente ou inválido),
`RNV001017` (Banco indisponível), `RNV001018` (empresa inexistente ou de outro cliente),
`RNV001030` (empresa sem conta aberta), `RNV001031` (conta não active),
`RNV001023` (valor inválido), `RNV001024` (Idempotency-Key reusada), além dos genéricos
de schema/auth e dos erros do ledger quando o lançamento é propagado ao Banco.

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001023 | 422 | Valor inválido |
| RNV001025 | 404 | Pagamento inexistente ou de outro lojista |
| RNV001026 | 409 | Fora da janela (valor já liberado) |
| RNV001003 | 409 | Pagamento já estornado |

## Payout (saque / saída)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001032 | 404 | Saque inexistente ou de outro lojista |

## Admin

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001027 | 403 | Token sem permissão de administrador |

---

## Notas e decisões

- **`RNV001030` (empresa sem conta aberta) entra na lista do `POST /payments`.** Cobre o caso
  de a empresa existir e **nunca ter aberto conta**. Distinto da reprovação do birô: a validação
  do birô ocorre na abertura da conta e a reprovação deixa a conta em `rejected` (um estado
  "não active"), que cai em `RNV001031`. "Empresa não validada pelo birô" não tem código próprio.

- **Dois códigos para "conta não active" (regra adotada):** `RNV001031` (403) na borda do
  cliente × `RNV001005` (422) no guard interno do ledger. Regra: borda do cliente = 403
  `RNV001031`; reservar 422 `RNV001005` só para o ledger; no `/close`, conta não-active é
  conflito de estado (409).

- **Leitura de conta não-active: resolvido.** Leitura (`GET /balance`, `GET /statement`) passa
  para conta `blocked`/`closed`. O guard de conta `active` vale só para escrita.

- **Retirados** (restos de conta externa / transferência interna, fora do escopo):
  `RNV001004` (conta de destino inexistente), `RNV001007` (transferência para a própria
  conta), `RNV001008` (conta externa não cadastrada), `RNV001013` (destino de outro
  titular). Números aposentados — não reaproveitar.

- **`RNV001011`** nunca foi usado. Reservado.
