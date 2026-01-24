-- Seed core infrastructure accounts for double-entry ledger
-- SYSTEM: Used for fee collection, rounding, etc.
-- SETTLEMENT: Used as the counterparty for external pay-ins/payouts

-- Insert Settlement Account for NGN
INSERT INTO accounts (id, owner_id, currency, account_type, is_active, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000001', NULL, 'NGN', 'SETTLEMENT', TRUE, NOW())
ON CONFLICT (owner_id, currency) WHERE owner_id IS NULL DO NOTHING;

-- Insert System Revenue Account for NGN
INSERT INTO accounts (id, owner_id, currency, account_type, is_active, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000002', NULL, 'NGN', 'SYSTEM', TRUE, NOW())
ON CONFLICT (owner_id, currency) WHERE owner_id IS NULL DO NOTHING;
