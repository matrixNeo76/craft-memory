-- Sprint 10: Cavekit Workflow — spec-driven procedure mode
-- Aggiunge campi per workflow spec→plan→verify alle procedure.

ALTER TABLE procedures ADD COLUMN verify_command TEXT;
ALTER TABLE procedures ADD COLUMN acceptance_criteria TEXT;
ALTER TABLE procedures ADD COLUMN spec_text TEXT;
ALTER TABLE procedures ADD COLUMN mode TEXT DEFAULT 'manual';
