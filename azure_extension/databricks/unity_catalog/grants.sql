-- Unity Catalog grants for data access control
-- SKIP THIS FOR TESTING/DEMO - Not needed until production AKS deployment

-- For testing: You (workspace admin) already have full access to all schemas
-- For demo: Your credentials work perfectly

-- For production AKS deployment (later):
-- USE CATALOG afga_dev;
-- 
-- -- Grant read-only access to AKS workload identity for retrieval
-- GRANT SELECT ON SCHEMA silver TO `service_principal_aks@tenant.onmicrosoft.com`;
-- GRANT SELECT ON SCHEMA gold TO `service_principal_aks@tenant.onmicrosoft.com`;
-- 
-- -- Grant write access to Databricks job service principal for ingestion
-- GRANT ALL PRIVILEGES ON SCHEMA bronze TO `service_principal_databricks@tenant.onmicrosoft.com`;
-- GRANT ALL PRIVILEGES ON SCHEMA silver TO `service_principal_databricks@tenant.onmicrosoft.com`;
-- GRANT ALL PRIVILEGES ON SCHEMA gold TO `service_principal_databricks@tenant.onmicrosoft.com`;

-- NOTE: Service principals referenced above don't exist yet
-- Create them when deploying to production AKS

