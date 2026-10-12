CREATE TABLE payment_method(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    version                         INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    fee_bps                         INTEGER NOT NULL CHECK (fee_bps BETWEEN 0 AND 10000),
    release_window_hours            INTEGER NOT NULL CHECK (release_window_hours BETWEEN 0 AND 8760),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator, version)
);

INSERT INTO payment_method (enumerator, version, fee_bps, release_window_hours) VALUES
('pix', 1, 99, 24),
('boleto', 1, 199, 72),
('card', 1, 499, 720);

CREATE TABLE payment_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payment_status (enumerator) VALUES
('held'),
('settled'),
('refunded');

CREATE TABLE payment_transition(
    id                              SERIAL PRIMARY KEY,
    from_status_id                  INTEGER NOT NULL REFERENCES payment_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES payment_status(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO payment_transition (from_status_id, to_status_id) VALUES
((SELECT id FROM payment_status WHERE enumerator = 'held'),
 (SELECT id FROM payment_status WHERE enumerator = 'settled')),
((SELECT id FROM payment_status WHERE enumerator = 'held'),
 (SELECT id FROM payment_status WHERE enumerator = 'refunded'));

CREATE TABLE payout_purpose(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payout_purpose (enumerator) VALUES
('withdrawal'),
('bill_payment'),
('transfer');

CREATE TABLE payout_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payout_status (enumerator) VALUES
('pending'),
('settled'),
('failed');

CREATE TABLE payout_transition(
    id                              SERIAL PRIMARY KEY,
    from_status_id                  INTEGER NOT NULL REFERENCES payout_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES payout_status(id),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO payout_transition (from_status_id, to_status_id) VALUES
((SELECT id FROM payout_status WHERE enumerator = 'pending'),
 (SELECT id FROM payout_status WHERE enumerator = 'settled')),
((SELECT id FROM payout_status WHERE enumerator = 'pending'),
 (SELECT id FROM payout_status WHERE enumerator = 'failed'));

CREATE TABLE payout_result(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payout_result (enumerator) VALUES
('confirmed'),
('rejected'),
('timeout');

CREATE TABLE payment(
    id                              SERIAL PRIMARY KEY,
    payment_key                     CHAR(36) NOT NULL,
    client_key                      CHAR(36) NOT NULL,
    company_key                     CHAR(36) NOT NULL,
    account_key                     CHAR(36) NOT NULL,
    method_id                       INTEGER NOT NULL REFERENCES payment_method(id),
    status_id                       INTEGER NOT NULL REFERENCES payment_status(id),
    amount_minor                    BIGINT NOT NULL CHECK (amount_minor > 0),
    fee_bps                         INTEGER NOT NULL CHECK (fee_bps >= 0),
    release_at                      TIMESTAMPTZ NOT NULL,
    transaction_key                 CHAR(36),
    idempotency_key                 VARCHAR(50) NOT NULL,
    payload_hash                    CHAR(64) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(payment_key),
    UNIQUE(transaction_key),
    CONSTRAINT uq_payment_idempotency UNIQUE(company_key, idempotency_key)
);

CREATE TABLE payout(
    id                              SERIAL PRIMARY KEY,
    payout_key                      CHAR(36) NOT NULL,
    company_key                     CHAR(36) NOT NULL,
    account_key                     CHAR(36) NOT NULL,
    purpose_id                      INTEGER NOT NULL REFERENCES payout_purpose(id),
    destination                     JSONB NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES payout_status(id),
    amount_minor                    BIGINT NOT NULL CHECK (amount_minor > 0),
    last_attempt_at                 TIMESTAMPTZ,
    failure_reason                  VARCHAR(255),
    transaction_key                 CHAR(36),
    idempotency_key                 VARCHAR(50) NOT NULL,
    payload_hash                    CHAR(64) NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(payout_key),
    UNIQUE(transaction_key),
    CONSTRAINT uq_payout_idempotency UNIQUE(company_key, idempotency_key)
);

CREATE TABLE payout_attempt(
    id                              SERIAL PRIMARY KEY,
    payout_id                       INTEGER NOT NULL REFERENCES payout(id),
    result_id                       INTEGER NOT NULL REFERENCES payout_result(id),
    attempt_number                  INTEGER NOT NULL CHECK (attempt_number > 0),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(payout_id, attempt_number)
);

CREATE TABLE payment_status_event(
    id                              SERIAL PRIMARY KEY,
    payment_id                      INTEGER NOT NULL REFERENCES payment(id),
    status_id                       INTEGER NOT NULL REFERENCES payment_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMPTZ NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW())
);

CREATE TABLE payout_status_event(
    id                              SERIAL PRIMARY KEY,
    payout_id                       INTEGER NOT NULL REFERENCES payout(id),
    status_id                       INTEGER NOT NULL REFERENCES payout_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMPTZ NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT(NOW())
);

CREATE INDEX idx_payment_status_release ON payment (status_id, release_at);
CREATE INDEX idx_payment_company_created_at ON payment (company_key, created_at);
CREATE INDEX idx_payout_status_last_attempt ON payout (status_id, last_attempt_at);
CREATE INDEX idx_payout_company_created_at ON payout (company_key, created_at);
CREATE INDEX idx_payout_attempt_payout ON payout_attempt (payout_id);