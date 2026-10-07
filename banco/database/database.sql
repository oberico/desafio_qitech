CREATE TABLE account_class(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_class (enumerator) VALUES
('asset'),
('liability'),
('revenue');

CREATE TABLE account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
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
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator) VALUES
('gateway_receipt'),
('payout'),
('settlement'),
('refund'),
('reversal'),
('deposit'),
('transfer');

CREATE TABLE transaction_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO transaction_status (enumerator) VALUES
('pending'),
('settled'),
('failed');

CREATE TABLE allowed_transition(
    id                              SERIAL PRIMARY KEY,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    from_status_id                  INTEGER NOT NULL REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(type_id, from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO allowed_transition (type_id, from_status_id, to_status_id) VALUES
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'settled')),
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'failed'));

CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    cpf                             CHAR(14) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    birthdate                       DATE NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
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
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(company_key),
    UNIQUE(cnpj)
);

CREATE TABLE api_token(
    id                              SERIAL PRIMARY KEY,
    token_hash                      CHAR(64) NOT NULL,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    revoked_at                      TIMESTAMP,
    last_used_at                    TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
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
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(code)
);

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    status_id                       INTEGER NOT NULL REFERENCES transaction_status(id),
    idempotency_key                 VARCHAR(80),
    payload_hash                    CHAR(64),
    reverses_transaction_id         INTEGER REFERENCES transaction(id),
    settles_transaction_id          INTEGER REFERENCES transaction(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    CONSTRAINT uq_transaction_idempotency_key UNIQUE(idempotency_key),
    UNIQUE(reverses_transaction_id),
    UNIQUE(settles_transaction_id),
    CHECK ((idempotency_key IS NULL) = (payload_hash IS NULL))
);

CREATE TABLE entry(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'brl',
    debit_minor                     BIGINT NOT NULL DEFAULT 0,
    credit_minor                    BIGINT NOT NULL DEFAULT 0,
    balance_after                   BIGINT,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
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
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE INDEX idx_entry_account_id_desc ON entry (account_id, id DESC);