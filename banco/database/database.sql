CREATE TABLE account_class(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_class (enumerator) VALUES
('asset'),
('liability'),
('revenue');

CREATE TABLE account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_status (enumerator) VALUES
('created'),
('active'),
('rejected'),
('blocked'),
('closed');

CREATE TABLE transaction_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator) VALUES
('receipt'),
('payout'),
('settlement'),
('refund'),
('reversal');

CREATE TABLE transaction_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_status (enumerator) VALUES
('pending'),
('settled');

CREATE TABLE allowed_transition(
    id                              SERIAL PRIMARY KEY,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    from_status_id                  INTEGER NOT NULL REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(type_id, from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO allowed_transition (type_id, from_status_id, to_status_id) VALUES
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'settled'));

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
    normal_balance                  CHAR(1) NOT NULL CHECK (normal_balance IN ('d', 'c')),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'brl',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(code),
    CONSTRAINT account_company_id_key UNIQUE(company_id),
    CONSTRAINT ck_account_internal_or_client CHECK (
        (company_id IS NULL AND code IS NOT NULL)
        OR (company_id IS NOT NULL AND code IS NULL)
    )
);

INSERT INTO account (account_key, code, class_id, status_id, normal_balance) VALUES
(gen_random_uuid()::text, 'reserves',
 (SELECT id FROM account_class WHERE enumerator = 'asset'),
 (SELECT id FROM account_status WHERE enumerator = 'active'), 'd'),
(gen_random_uuid()::text, 'in_transit',
 (SELECT id FROM account_class WHERE enumerator = 'liability'),
 (SELECT id FROM account_status WHERE enumerator = 'active'), 'c'),
(gen_random_uuid()::text, 'revenue',
 (SELECT id FROM account_class WHERE enumerator = 'revenue'),
 (SELECT id FROM account_status WHERE enumerator = 'active'), 'c');

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
    idempotency_key                 VARCHAR(100) NOT NULL,
    payload_hash                    CHAR(64) NOT NULL,
    reverses_transaction_id         INTEGER REFERENCES transaction(id),
    settles_transaction_id          INTEGER REFERENCES transaction(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    CONSTRAINT uq_transaction_idempotency_key UNIQUE(idempotency_key),
    CONSTRAINT uq_transaction_reverses UNIQUE(reverses_transaction_id),
    CONSTRAINT uq_transaction_settles UNIQUE(settles_transaction_id)
);

CREATE TABLE entry(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'brl',
    debit_minor                     BIGINT NOT NULL DEFAULT 0,
    credit_minor                    BIGINT NOT NULL DEFAULT 0,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(CLOCK_TIMESTAMP()),
    CONSTRAINT ck_entry_one_side CHECK (
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

CREATE INDEX entry_account_idx ON entry (account_id, id) INCLUDE (debit_minor, credit_minor);
CREATE INDEX idx_entry_account_created_at ON entry (account_id, created_at);
CREATE INDEX idx_entry_transaction ON entry (transaction_id);