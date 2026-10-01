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
('created'),
('held'),
('pending'),
('settled'),
('refunded'),
('reversed'),
('needs_action'),
('failed');

CREATE TABLE origin(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO origin (enumerator) VALUES
('gateway'),
('tap_to_pay');

CREATE TABLE payout_result(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payout_result (enumerator) VALUES
('confirmed'),
('rejected'),
('timeout');

CREATE TABLE allowed_transition(
    id                              SERIAL PRIMARY KEY,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    from_status_id                  INTEGER NOT NULL REFERENCES transaction_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES transaction_status(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(type_id, from_status_id, to_status_id)
);

INSERT INTO allowed_transition (type_id, from_status_id, to_status_id) VALUES
((SELECT id FROM transaction_type WHERE enumerator = 'gateway_receipt'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'held')),
((SELECT id FROM transaction_type WHERE enumerator = 'gateway_receipt'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'settled')),
((SELECT id FROM transaction_type WHERE enumerator = 'gateway_receipt'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'refunded')),
((SELECT id FROM transaction_type WHERE enumerator = 'gateway_receipt'),
 (SELECT id FROM transaction_status WHERE enumerator = 'held'),
 (SELECT id FROM transaction_status WHERE enumerator = 'settled')),
((SELECT id FROM transaction_type WHERE enumerator = 'gateway_receipt'),
 (SELECT id FROM transaction_status WHERE enumerator = 'held'),
 (SELECT id FROM transaction_status WHERE enumerator = 'refunded')),
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'settled')),
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'),
 (SELECT id FROM transaction_status WHERE enumerator = 'needs_action')),
((SELECT id FROM transaction_type WHERE enumerator = 'payout'),
 (SELECT id FROM transaction_status WHERE enumerator = 'needs_action'),
 (SELECT id FROM transaction_status WHERE enumerator = 'pending'));

CREATE TABLE person(
    id                              SERIAL PRIMARY KEY,
    person_key                      CHAR(36) NOT NULL,
    cpf                             CHAR(11) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    birthdate                       DATE NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(person_key),
    UNIQUE(cpf),
    UNIQUE(email)
);

CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    cnpj                            CHAR(14) NOT NULL,
    legal_name                      VARCHAR(255) NOT NULL,
    person_id                       INTEGER NOT NULL REFERENCES person(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
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
    client_id                       INTEGER REFERENCES client(id),
    class_id                        INTEGER NOT NULL REFERENCES account_class(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    normal_balance                  CHAR(1) NOT NULL CHECK (normal_balance IN ('d', 'c')),
    currency                        VARCHAR(3) NOT NULL DEFAULT 'brl',
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(code)
);

CREATE TABLE external_bank_account(
    id                              SERIAL PRIMARY KEY,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    bank                            VARCHAR(10) NOT NULL,
    branch                          VARCHAR(10) NOT NULL,
    account_number                  VARCHAR(20) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL,
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    status_id                       INTEGER NOT NULL REFERENCES transaction_status(id),
    origin_id                       INTEGER REFERENCES origin(id),
    fee_bps                         INTEGER,
    fee_minor                       BIGINT,
    release_at                      TIMESTAMP,
    reverses_transaction_id         INTEGER REFERENCES transaction(id),
    settles_transaction_id          INTEGER REFERENCES transaction(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    UNIQUE(reverses_transaction_id),
    UNIQUE(settles_transaction_id)
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

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE payout_attempt(
    id                              SERIAL PRIMARY KEY,
    transaction_id                  INTEGER NOT NULL REFERENCES transaction(id),
    result_id                       INTEGER NOT NULL REFERENCES payout_result(id),
    attempt_number                  INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE idempotency(
    id                              SERIAL PRIMARY KEY,
    idempotency_key                 VARCHAR(80) NOT NULL,
    payload_hash                    CHAR(64) NOT NULL,
    transaction_id                  INTEGER REFERENCES transaction(id),
    status_http                     SMALLINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(idempotency_key)
);

CREATE INDEX idx_entry_account_id_desc ON entry (account_id, id DESC);
CREATE INDEX idx_transaction_status_release ON transaction (status_id, release_at);
CREATE INDEX idx_payout_attempt_tx ON payout_attempt (transaction_id);

INSERT INTO account (account_key, code, client_id, class_id, status_id, normal_balance, currency) VALUES
('00000000-0000-0000-0000-000000000001', 'reserves', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'asset'),
    (SELECT id FROM account_status WHERE enumerator = 'active'), 'd', 'brl'),
('00000000-0000-0000-0000-000000000002', 'revenue', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'revenue'),
    (SELECT id FROM account_status WHERE enumerator = 'active'), 'c', 'brl'),
('00000000-0000-0000-0000-000000000003', 'pending_release', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'liability'),
    (SELECT id FROM account_status WHERE enumerator = 'active'), 'c', 'brl'),
('00000000-0000-0000-0000-000000000004', 'in_transit', NULL,
    (SELECT id FROM account_class WHERE enumerator = 'liability'),
    (SELECT id FROM account_status WHERE enumerator = 'active'), 'c', 'brl');