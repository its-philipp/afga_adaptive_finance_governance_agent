-- Unity Catalog setup for Adaptive Finance Governance AFGA
-- This script uses the default workspace catalog created by Databricks

-- OPTION 1: Use existing afga_dev catalog (Recommended)
-- The workspace automatically creates this catalog when using Terraform/scripts.
-- No action needed - proceed to schemas.sql

-- OPTION 2: Create custom catalog (Advanced - requires storage location)
-- Only use this if you need a separate catalog:
-- CREATE CATALOG IF NOT EXISTS afga_dev
-- MANAGED LOCATION 'abfss://unity-catalog@<your-storage-account>.dfs.core.windows.net/afga_dev'
-- COMMENT 'Adaptive Finance Governance AFGA - Unity Catalog';

-- For this project, we use: afga_dev (existing catalog)
-- Proceed to schemas.sql to create bronze/silver/gold schemas

