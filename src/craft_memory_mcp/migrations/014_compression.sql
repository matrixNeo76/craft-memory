-- Sprint 10: Compression Flag
-- Aggiunge colonna compressed alle memories per tracciare
-- se il contenuto è stato compresso con compress.py
-- 0 = non compresso (default, backward compatibile)
-- 1 = compresso con level=1

ALTER TABLE memories ADD COLUMN compressed INTEGER DEFAULT 0;
