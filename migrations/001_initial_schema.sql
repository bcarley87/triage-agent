-- 001_initial_schema.sql
-- Initial schema for triage agent

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE patients (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           TEXT        NOT NULL,
    dob            DATE        NOT NULL,
    phone          TEXT,
    email          TEXT,
    address        TEXT,
    specialty      TEXT        NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Urgency status values: pending | in_progress | completed | dismissed
CREATE TABLE followup_candidates (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id     UUID        NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    trigger_reason TEXT        NOT NULL,
    trigger_date   DATE        NOT NULL,
    urgency_score  NUMERIC(4,1),
    context_json   JSONB,
    status         TEXT        NOT NULL DEFAULT 'pending',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- channel values: phone | sms | email
CREATE TABLE outreach_log (
    id                 UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id       UUID        NOT NULL REFERENCES followup_candidates(id) ON DELETE CASCADE,
    channel            TEXT        NOT NULL,
    message_sent       TEXT        NOT NULL,
    sent_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_received  TIMESTAMPTZ,
    response_text      TEXT
);

-- action values: approve | edit | dismiss | escalate
CREATE TABLE nurse_actions (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID        NOT NULL REFERENCES followup_candidates(id) ON DELETE CASCADE,
    nurse_id     TEXT        NOT NULL,
    action       TEXT        NOT NULL,
    edit_diff    JSONB,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_followup_candidates_patient_id ON followup_candidates(patient_id);
CREATE INDEX idx_followup_candidates_status     ON followup_candidates(status);
CREATE INDEX idx_outreach_log_candidate_id      ON outreach_log(candidate_id);
CREATE INDEX idx_nurse_actions_candidate_id     ON nurse_actions(candidate_id);
