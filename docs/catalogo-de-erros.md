# Catálogo de erros

Todos os códigos de erro da API do RNV, com o status HTTP e o significado de cada um. As rotas que devolvem cada código estão em [Rotas da API](rotas.md).

[← Voltar ao README](../README.md)

## Sumário

- [Formato do erro](#formato-do-erro)
- [Genéricos](#genéricos) · [Integração entre serviços](#integração-entre-serviços)
- [Cadastro](#cadastro-cliente--empresa) · [Conta](#conta) · [Ledger](#ledger-transações--entries)
- [Pagamento](#pagamento-venda) · [Payout](#payout-saque--saída) · [Admin](#admin)
- [Notas e decisões](#notas-e-decisões)

## Formato do erro

Todo erro da API tem o mesmo formato:

```json
{
  "title": "Account not Found",
  "description": "Account with key 7f3a... was not found.",
  "translation": "A conta com chave 7f3a... não foi encontrada.",
  "code": "RNV001021"
}
```

| Faixa | Tipo |
|---|---|
| `RNV000xxx` | genéricos: formato da requisição, autenticação e infraestrutura |
| `RNV001xxx` | regras de negócio |

> [!NOTE]
> Os números são um contrato estável: nunca são renumerados nem reaproveitados. 

## Genéricos

| Código | HTTP | Mensagem |
|---|---|---|
| RNV000001 | 400 | Corpo que não é objeto JSON (ausente, JSON inválido, lista, `null`) |
| RNV000002 | 403 | INTERNAL-TOKEN ausente ou errado |
| RNV000003 | 401 | Token ausente, inválido ou revogado |
| RNV000004 | 404 | Rota inexistente |
| RNV000005 | 405 | Método HTTP não permitido para a rota |
| RNV000006 | 503 | Serviço ocupado: pool de conexões do banco esgotado dentro do prazo (tente novamente em instantes) |
| RNV000007 | 400 | Campo obrigatório ausente. A tradução cita o campo (`Campo obrigatório ausente: purpose.`) |
| RNV000008 | 400 | Campo ou parâmetro não permitido: campo extra, parâmetro de query desconhecido, ou campo que não combina com outro (`settles_transaction_key` em `receipt`, `debit_minor` junto de `credit_minor`) |
| RNV000009 | 400 | Tipo ou formato inválido: tipo errado, valor fora do enumerador, padrão (UUID, CPF/CNPJ, data com fuso) não atendido, data impossível. A tradução diz o esperado |
| RNV000010 | 400 | Valor fora do limite: mínimo/máximo, tamanho de texto, lista ou objeto, `from` depois de `to`, data de nascimento futura, `destination` acima de 4096 bytes. A tradução diz o limite |
| RNV000011 | 400 | Cursor de paginação inválido (vazio, inventado, adulterado ou malformado) |
| RNV000012 | 400 | Header `Idempotency-Key` ausente ou fora do tamanho (1 a 50 no Transferências, 1 a 100 no `POST /ledger/transactions`) |

## Integração entre serviços

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001017 | 503 | Banco indisponível ou sem resposta; nada foi gravado no Transferências, e o resultado no Banco pode ser desconhecido. Retente com a mesma `Idempotency-Key`; levantado pelo Transferências |
| RNV001036 | 503 | Transferências indisponível ou sem resposta no `POST /accounts/{key}/close`; o Banco não consegue conferir os valores em trânsito e recusa (fail-closed). Nada foi alterado; tente novamente em instantes. Levantado pelo Banco |

## Cadastro (cliente / empresa)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001001 | 409 | CPF já cadastrado |
| RNV001002 | 422 | CPF com dígitos inválidos |
| RNV001028 | 409 | E-mail já cadastrado |
| RNV001029 | 422 | Pessoa menor de idade |
| RNV001019 | 409 | CNPJ já cadastrado |
| RNV001020 | 422 | CNPJ inválido (formato ou dígitos) |
| RNV001018 | 404 | Empresa inexistente ou de outro dono (também usado pelo `POST /payouts` para conta inexistente ou de outro cliente) |
| RNV001022 | 409 | Empresa já possui conta aberta |

## Conta

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001021 | 404 | Conta inexistente ou de outro dono |
| RNV001030 | 403 | Empresa sem conta aberta |
| RNV001031 | 403 | Conta não está active (bloqueia só escrita) |
| RNV001005 | 422 | Conta fora de active (guard interno do ledger) |
| RNV001012 | 409 | Conta ainda tem saldo (encerre após sacar). **Sem uso**: o `/close` com saldo responde `RNV001035` |
| RNV001035 | 422 | Conta com saldo ou valores em trânsito; encerramento exige saldo zero e nada pendente (payments `held` ou payouts `pending` no Transferências) |
| RNV001009 | 409 | Conta não está active, não pode bloquear nem encerrar. A tradução diz o status atual (`A conta está bloqueada, ...`) |
| RNV001010 | 409 | Conta não está blocked (não pode desbloquear) |

> [!NOTE]
> **Leitura passa sempre.** `GET /balance` e `GET /statement` respondem mesmo com a conta `blocked` ou `closed`: o titular sempre pode ver o saldo e o extrato. O guard de conta `active` (`RNV001031`) vale **só para escrita** (criar pagamento ou saque).


## Ledger (transações / entries)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001015 | 422 | Lançamentos não fecham (débito ≠ crédito) |
| RNV001006 | 422 | Saldo insuficiente (também devolvido pelo `POST /payouts`, repassado do Banco) |
| RNV001014 | 409 | Transação já consumida (saída única). A tradução diz qual: `já foi liquidada` (há settlement) ou `já foi estornada` (há refund/reversal) |
| RNV001016 | 404 | Transação referenciada inexistente |
| RNV001024 | 422 | Idempotency-Key reusada com conteúdo diferente |
| RNV001033 | 422 | Transação referenciada de tipo incompatível (settlement liquida `receipt`/`payout`; refund estorna `receipt`; reversal estorna `payout`) |
| RNV001034 | 422 | Conta interna referenciada por `account_key` (`reserves`, `in_transit` e `revenue` só entram por `account_code`) |

## Pagamento (venda)

Erros possíveis no `POST /payments`: `RNV000003` (token ausente ou inválido),
`RNV001017` (Banco indisponível), `RNV001018` (empresa inexistente ou de outro cliente),
`RNV001030` (empresa sem conta aberta), `RNV001031` (conta não active),
`RNV001023` (valor inválido), `RNV001024` (Idempotency-Key reusada), além dos genéricos
de schema/auth e dos erros do ledger quando o lançamento é propagado ao Banco.

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001023 | 422 | Valor inválido. A tradução diz o motivo: `O valor precisa ser maior que zero.` (`amount_minor` <= 0) ou `O valor passa do máximo permitido de 9223372036854775807 centavos.` (teto do BIGINT) |
| RNV001025 | 404 | Pagamento inexistente ou de outro lojista |
| RNV001026 | 409 | Fora da janela (valor já liberado) |
| RNV001003 | 409 | Pagamento já estornado |

## Payout (saque / saída)

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001032 | 404 | Saque inexistente ou de outro lojista |

Erros possíveis no `POST /payouts`: os de formato (`RNV000001`, `RNV000007` a `RNV000010`, `RNV000012`), `RNV000003`, `RNV001018` (conta inexistente
ou de outro cliente, reaproveitando o código de empresa inexistente), `RNV001031` (conta não active), `RNV001023`, `RNV001024`, `RNV001006` (saldo
insuficiente, repassado do Banco) e `RNV001017` (Banco indisponível). `RNV001030` não se aplica.

## Admin

| Código | HTTP | Mensagem |
|---|---|---|
| RNV001027 | 403 | Token sem permissão de administrador (Banco e Transferências: rotas `/admin/*` com token de cliente) |

---

## Notas e decisões

- **Um código por tipo de erro de formato (2026-10-12).** O antigo `RNV000001` cobria todo `400`
  e a tradução era sempre "A requisição não está no formato esperado". Agora cada tipo tem código
  (`RNV000007` a `RNV000012`) e a `translation` cita o campo e o motivo em português; a `description`
  em inglês mantém o formato `The request does not match the expected schema: <campo>: <motivo>`.
  `RNV000001` ficou só para corpo que não é objeto JSON. Os números existentes não foram
  renumerados nem agrupados por serviço: o código identifica o erro, não quem o levanta
  (`RNV001006` e `RNV001024` atravessam os dois serviços).

- **`RNV000006` separado (2026-10-12).** Tinha dois sentidos: pool esgotado (Transferências) e
  Transferências fora no `/close` (Banco). O segundo virou `RNV001036`, espelho do `RNV001017`.

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
