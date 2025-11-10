-- Create schemas within the catalog

-- Use the existing workspace catalog
USE CATALOG afga_dev;

-- Bronze schema (raw ingested data)
CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Bronze layer - raw ingested finance transactions';

-- Silver schema (validated and transformed data)
CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Silver layer - validated and enriched invoices with governance signals';

-- Gold schema (embeddings and vector search)
CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Gold layer - finance embeddings and vector search artifacts';

-- Verify schemas were created
SHOW SCHEMAS IN afga_dev;

-- Grant usage (for production - skip for testing)
-- GRANT USE SCHEMA ON SCHEMA bronze TO `service_principal_aks@tenant.onmicrosoft.com`;
-- GRANT USE SCHEMA ON SCHEMA silver TO `service_principal_aks@tenant.onmicrosoft.com`;
-- GRANT USE SCHEMA ON SCHEMA gold TO `service_principal_aks@tenant.onmicrosoft.com`;

