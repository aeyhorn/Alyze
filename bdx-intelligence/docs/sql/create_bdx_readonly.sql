-- ═══════════════════════════════════════════════════════════════════════════════
-- BDX Intelligence – read-only SQL Server login for container deployment
--
-- Run this on the SAP SQL Server (LDSAP) as a sysadmin (e.g. sa or a domain
-- admin account).  It creates a SQL login with SELECT-only access to the OWOR
-- and OITM tables in both the DEV and PROD company databases.
--
-- Inside a Linux container Windows integrated authentication is not available,
-- so the collector needs this SQL login (SAP_DB_TRUSTED_CONNECTION=no).
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Create the server login (choose a strong password – store it in .env)
CREATE LOGIN [bdx_readonly]
    WITH PASSWORD = N'CHANGE_ME_TO_A_STRONG_PASSWORD',
    CHECK_EXPIRATION = OFF,
    CHECK_POLICY = ON;

-- 2. Grant SELECT on OWOR + OITM in the DEV company database
USE [DEV_SBO_LEISINGER];
CREATE USER [bdx_readonly] FOR LOGIN [bdx_readonly];
GRANT SELECT ON dbo.OWOR TO [bdx_readonly];
GRANT SELECT ON dbo.OITM TO [bdx_readonly];
-- Quote-to-Promise (stock, open POs, BOM, price lists)
GRANT SELECT ON dbo.OITW TO [bdx_readonly];
GRANT SELECT ON dbo.OPOR TO [bdx_readonly];
GRANT SELECT ON dbo.POR1 TO [bdx_readonly];
GRANT SELECT ON dbo.OITT TO [bdx_readonly];
GRANT SELECT ON dbo.ITT1 TO [bdx_readonly];
GRANT SELECT ON dbo.ITM1 TO [bdx_readonly];
GRANT SELECT ON dbo.OPLN TO [bdx_readonly];
-- Deny write operations explicitly (belt-and-suspenders).
-- IMPORTANT: do NOT deny CONTROL — CONTROL encompasses CONNECT + SELECT,
-- so DENY CONTROL would block the login from opening the database (error 18456 state 38).
DENY INSERT, UPDATE, DELETE, ALTER TO [bdx_readonly];

-- 3. Grant SELECT on OWOR + OITM (+ Q2P tables) in the PROD company database
USE [SBO_LEISINGER];
CREATE USER [bdx_readonly] FOR LOGIN [bdx_readonly];
GRANT SELECT ON dbo.OWOR TO [bdx_readonly];
GRANT SELECT ON dbo.OITM TO [bdx_readonly];
GRANT SELECT ON dbo.OITW TO [bdx_readonly];
GRANT SELECT ON dbo.OPOR TO [bdx_readonly];
GRANT SELECT ON dbo.POR1 TO [bdx_readonly];
GRANT SELECT ON dbo.OITT TO [bdx_readonly];
GRANT SELECT ON dbo.ITT1 TO [bdx_readonly];
GRANT SELECT ON dbo.ITM1 TO [bdx_readonly];
GRANT SELECT ON dbo.OPLN TO [bdx_readonly];
DENY INSERT, UPDATE, DELETE, ALTER TO [bdx_readonly];

-- 4. Verify
USE [DEV_SBO_LEISINGER];
EXECUTE AS LOGIN = 'bdx_readonly';
    SELECT TOP 1 DocEntry, Status, ItemCode FROM dbo.OWOR ORDER BY DocEntry DESC;
REVERT;
PRINT 'bdx_readonly login created and verified.';
