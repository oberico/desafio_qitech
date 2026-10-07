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

CREATE TABLE payment_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payment_status (enumerator) VALUES
('pending'),
('held'),
('settled'),
('refunded');

CREATE TABLE payout_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO payout_status (enumerator) VALUES
('pending'),
('settled'),
('needs_action'),
('failed');

CREATE TABLE payment_transition(
    id                              SERIAL PRIMARY KEY,
    from_status_id                  INTEGER NOT NULL REFERENCES payment_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES payment_status(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO payment_transition (from_status_id, to_status_id) VALUES
((SELECT id FROM payment_status WHERE enumerator = 'pending'),
 (SELECT id FROM payment_status WHERE enumerator = 'held')),
((SELECT id FROM payment_status WHERE enumerator = 'pending'),
 (SELECT id FROM payment_status WHERE enumerator = 'settled')),
((SELECT id FROM payment_status WHERE enumerator = 'pending'),
 (SELECT id FROM payment_status WHERE enumerator = 'refunded')),
((SELECT id FROM payment_status WHERE enumerator = 'held'),
 (SELECT id FROM payment_status WHERE enumerator = 'settled')),
((SELECT id FROM payment_status WHERE enumerator = 'held'),
 (SELECT id FROM payment_status WHERE enumerator = 'refunded'));

CREATE TABLE payout_transition(
    id                              SERIAL PRIMARY KEY,
    from_status_id                  INTEGER NOT NULL REFERENCES payout_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES payout_status(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(from_status_id, to_status_id),
    CHECK (from_status_id <> to_status_id)
);

INSERT INTO payout_transition (from_status_id, to_status_id) VALUES
((SELECT id FROM payout_status WHERE enumerator = 'pending'),
 (SELECT id FROM payout_status WHERE enumerator = 'settled')),
((SELECT id FROM payout_status WHERE enumerator = 'pending'),
 (SELECT id FROM payout_status WHERE enumerator = 'needs_action')),
((SELECT id FROM payout_status WHERE enumerator = 'needs_action'),
 (SELECT id FROM payout_status WHERE enumerator = 'pending')),
((SELECT id FROM payout_status WHERE enumerator = 'needs_action'),
 (SELECT id FROM payout_status WHERE enumerator = 'failed'));

CREATE TABLE external_bank_account(
    id                              SERIAL PRIMARY KEY,
    company_key                     CHAR(36) NOT NULL,
    bank                            VARCHAR(10) NOT NULL,
    branch                          VARCHAR(10) NOT NULL,
    account_number                  VARCHAR(20) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE payment(
    id                              SERIAL PRIMARY KEY,
    payment_key                     CHAR(36) NOT NULL,
    company_key                     CHAR(36) NOT NULL,
    account_key                     CHAR(36) NOT NULL,
    transaction_key                 CHAR(36),
    origin_id                       INTEGER NOT NULL REFERENCES origin(id),
    method                          VARCHAR(30),
    status_id                       INTEGER NOT NULL REFERENCES payment_status(id),
    amount_minor                    BIGINT NOT NULL,
    fee_bps                         INTEGER,
    fee_minor                       BIGINT,
    release_at                      TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(payment_key),
    UNIQUE(transaction_key)
);

CREATE TABLE payout(
    id                              SERIAL PRIMARY KEY,
    payout_key                      CHAR(36) NOT NULL,
    company_key                     CHAR(36) NOT NULL,
    external_bank_account_id        INTEGER NOT NULL REFERENCES external_bank_account(id),
    transaction_key                 CHAR(36),
    status_id                       INTEGER NOT NULL REFERENCES payout_status(id),
    amount_minor                    BIGINT NOT NULL,
    version                         INTEGER NOT NULL DEFAULT 1,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(payout_key),
    UNIQUE(transaction_key)
);

CREATE TABLE payout_attempt(
    id                              SERIAL PRIMARY KEY,
    payout_id                       INTEGER NOT NULL REFERENCES payout(id),
    result_id                       INTEGER NOT NULL REFERENCES payout_result(id),
    attempt_number                  INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE payment_status_event(
    id                              SERIAL PRIMARY KEY,
    payment_id                      INTEGER NOT NULL REFERENCES payment(id),
    status_id                       INTEGER NOT NULL REFERENCES payment_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE payout_status_event(
    id                              SERIAL PRIMARY KEY,
    payout_id                       INTEGER NOT NULL REFERENCES payout(id),
    status_id                       INTEGER NOT NULL REFERENCES payout_status(id),
    reason                          VARCHAR(255),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE idempotency(
    id                              SERIAL PRIMARY KEY,
    idempotency_key                 VARCHAR(80) NOT NULL,
    payload_hash                    CHAR(64) NOT NULL,
    payment_key                     CHAR(36),
    status_http                     SMALLINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(idempotency_key)
);

CREATE INDEX idx_payment_status_release ON payment (status_id, release_at);
CREATE INDEX idx_payment_company ON payment (company_key);
CREATE INDEX idx_payout_attempt_payout ON payout_attempt (payout_id);
CREATE INDEX idx_external_bank_account_company ON external_bank_account (company_key);