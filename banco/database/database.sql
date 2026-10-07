CREATE TABLE account_class(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_class (enumerator) VALUES
('ASSET'),
('LIABILITY'),
('REVENUE');

CREATE TABLE account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_status (enumerator) VALUES
('CREATED'),
('ACTIVE'),
('REJECTED'),
('BLOCKED'),
('CLOSED');

CREATE TABLE transaction_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator) VALUES
('GATEWAY_RECEIPT'),
('PAYOUT'),
('SETTLEMENT'),
('REFUND'),
('REVERSAL'),
('DEPOSIT'),
('TRANSFER');

CREATE TABLE transaction_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_status (enumerator) VALUES
('CREATED'),
('HELD'),
('PENDING'),
('SETTLED'),
('REFUNDED'),
('REVERSED'),
('NEEDS_ACTION'),
('FAILED');

CREATE TABLE allowed_transition(
    id                              SERIAL PRIMARY KEY,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    from_status_id                  INTEGER NOT NULL REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(type_id, from_status_id, to_status_id)
);

INSERT INTO allowed_transition (type_id, from_status_id, to_status_id) VALUES
((SELECT id FROM transaction_type WHERE enumerator = 'GATEWAY_RECEIPT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'),
 (SELECT id FROM transaction_status WHERE enumerator = 'HELD')),
((SELECT id FROM transaction_type WHERE enumerator = 'GATEWAY_RECEIPT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'),
 (SELECT id FROM transaction_status WHERE enumerator = 'SETTLED')),
((SELECT id FROM transaction_type WHERE enumerator = 'GATEWAY_RECEIPT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'),
 (SELECT id FROM transaction_status WHERE enumerator = 'REFUNDED')),
((SELECT id FROM transaction_type WHERE enumerator = 'GATEWAY_RECEIPT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'HELD'),
 (SELECT id FROM transaction_status WHERE enumerator = 'SETTLED')),
((SELECT id FROM transaction_type WHERE enumerator = 'GATEWAY_RECEIPT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'HELD'),
 (SELECT id FROM transaction_status WHERE enumerator = 'REFUNDED')),
((SELECT id FROM transaction_type WHERE enumerator = 'PAYOUT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'),
 (SELECT id FROM transaction_status WHERE enumerator = 'SETTLED')),
((SELECT id FROM transaction_type WHERE enumerator = 'PAYOUT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'),
 (SELECT id FROM transaction_status WHERE enumerator = 'NEEDS_ACTION')),
((SELECT id FROM transaction_type WHERE enumerator = 'PAYOUT'),
 (SELECT id FROM transaction_status WHERE enumerator = 'NEEDS_ACTION'),
 (SELECT id FROM transaction_status WHERE enumerator = 'PENDING'));

CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    cpf                             CHAR(14) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    birthdate                       DATE NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
    UNIQUE(cpf),
    UNIQUE(email)
);

CREATE TABLE company(
    id                              SERIAL PRIMARY KEY,
    company_key                     CHAR(36) NOT NULL,
    cnpj                            CHAR(18) NOT NULL,
    legal_name                      VARCHAR(255) NOT NULL,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(company_key),
    UNIQUE(cnpj)
);

CREATE TABLE api_token(
    id                              SERIAL PRIMARY KEY,
    token_hash                      CHAR(64) NOT NULL,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    revoked_at                      TIMESTAMPTZ,
    last_used_at                    TIMESTAMPTZ,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(token_hash)
);

CREATE TABLE account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL,
    code                            VARCHAR(20),
    company_id                      INTEGER REFERENCES company(id),
    class_id                        INTEGER NOT NULL REFERENCES account_class(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    normal_balance                  CHAR(1) NOT NULL CHECK (normal_balance IN ('D', 'C')),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'BRL',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(code)
);

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMPTZ NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW())
);

CREATE TABLE transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    status_id                       INTEGER NOT NULL REFERENCES transaction_status(id),
    idempotency_key                 VARCHAR(80),
    reverses_transaction_id         INTEGER REFERENCES transaction(id),
    settles_transaction_id          INTEGER REFERENCES transaction(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    UNIQUE(idempotency_key),
    UNIQUE(reverses_transaction_id),
    UNIQUE(settles_transaction_id)
);

CREATE TABLE entry(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'BRL',
    debit_minor                     BIGINT NOT NULL DEFAULT 0,
    credit_minor                    BIGINT NOT NULL DEFAULT 0,
    balance_after                   BIGINT,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(CLOCK_TIMESTAMP()),
    CHECK (
        (debit_minor > 0 AND credit_minor = 0)
        OR (debit_minor = 0 AND credit_minor > 0)
    )
);

CREATE TABLE transaction_status_event(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    status_id                       INTEGER NOT NULL REFERENCES transaction_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMPTZ NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW())
);

CREATE INDEX idx_entry_account_id_desc ON entry (account_id, id DESC);
CREATE INDEX idx_entry_account_created_at ON entry (account_id, created_at);

INSERT INTO account (account_key, code, company_id, class_id, status_id, normal_balance, currency) VALUES
('00000000-0000-0000-0000-000000000001', 'RESERVES', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'ASSET'),
    (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), 'D', 'BRL'),
('00000000-0000-0000-0000-000000000002', 'REVENUE', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'REVENUE'),
    (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), 'C', 'BRL'),
('00000000-0000-0000-0000-000000000003', 'PENDING_RELEASE', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'LIABILITY'),
    (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), 'C', 'BRL'),
('00000000-0000-0000-0000-000000000004', 'IN_TRANSIT', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'LIABILITY'),
    (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), 'C', 'BRL');