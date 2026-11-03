-- The check log: one row per payload or photo check. Photos and payloads are not stored, only the
-- SHA-256 of the input, the risk and the signals raised, so a check can be tied to the photo kept
-- with the inspection record.
CREATE TABLE checks (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    risk TEXT NOT NULL,
    signals TEXT NOT NULL
);
CREATE INDEX checks_created ON checks (created_at);
CREATE INDEX checks_risk ON checks (risk);
