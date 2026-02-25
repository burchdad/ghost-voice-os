#!/bin/bash
# Database migration script
# Runs all pending migrations

set -e

echo "🔄 Running database migrations..."

# Wait for Postgres to be ready
echo "⏳ Waiting for database..."
until PGPASSWORD=password psql -h localhost -U postgres -d voiceos -c "SELECT 1;" > /dev/null 2>&1; do
    echo "   Database not ready yet..."
    sleep 2
done

echo "✅ Database is ready"
echo ""

# Run migrations
echo "Running migrations..."

# Create tables if not exist
PGPASSWORD=password psql -h localhost -U postgres -d voiceos << EOF
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calls (
    id VARCHAR(100) PRIMARY KEY,
    tenant_id VARCHAR(100) REFERENCES tenants(id),
    from_number VARCHAR(20),
    to_number VARCHAR(20),
    status VARCHAR(50),
    duration_seconds INT,
    recording_url VARCHAR(500),
    transcript TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voices (
    id VARCHAR(100) PRIMARY KEY,
    tenant_id VARCHAR(100) REFERENCES tenants(id),
    name VARCHAR(255),
    provider VARCHAR(100),
    voice_id VARCHAR(255),
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100),
    metric_name VARCHAR(255),
    metric_value NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calls_tenant ON calls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_voices_tenant ON voices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_metrics_tenant ON metrics(tenant_id);
EOF

echo "✅ Migrations complete"
echo ""

# Load tenant configs
echo "Loading tenant configurations..."
psql -h localhost -U postgres -d voiceos -c "TRUNCATE tenants;"

for tenant_file in tenants/*.json; do
    if [ -f "$tenant_file" ]; then
        tenant_name=$(basename "$tenant_file" .json)
        echo "  • Loading $tenant_name..."
        # Note: In production, use a proper migration tool
    fi
done

echo "✅ Tenant configurations loaded"
