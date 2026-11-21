-- ═══════════════════════════════════════════════════════════════════════════
-- BDX-INTELLIGENCE — reset bdx_readonly login + user mapping + CONNECT grants
-- ═══════════════════════════════════════════════════════════════════════════
-- Prefer the automated host script (injects SAP_DB_PASSWORD from .env):
--   pwsh ./scripts/Fix-DevSapAccess.ps1
--
-- Manual (SSMS on LDSAP as Windows admin LEISINGER\aeyhorn):
--   1. Replace __SAP_DB_PASSWORD__ with the value of SAP_DB_PASSWORD from the
--      DEV host .env (byte-identical — do not retype from memory).
--   2. File → Open → this file → F5.
--
-- Never commit a real password into this file.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Server login: password (matches .env), unlock, no lockout/expiry ────
ALTER LOGIN [bdx_readonly]
    WITH PASSWORD = N'__SAP_DB_PASSWORD__' UNLOCK,
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF,
         DEFAULT_DATABASE = [DEV_SBO_LEISINGER];
GO

-- ── 2. CONNECT on master (needed for the initial server handshake) ────────
USE [master];
GRANT CONNECT TO [bdx_readonly];
GO

-- ── 3. User mapping + db_datareader + CONNECT in DEV_SBO_LEISINGER ────────
USE [DEV_SBO_LEISINGER];
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'bdx_readonly')
    CREATE USER [bdx_readonly] FOR LOGIN [bdx_readonly];
ALTER ROLE [db_datareader] ADD MEMBER [bdx_readonly];
GRANT CONNECT TO [bdx_readonly];
-- Ensure CONNECT is not blocked by a prior DENY CONTROL mistake
IF EXISTS (
    SELECT 1 FROM sys.database_permissions p
    JOIN sys.database_principals dp ON dp.principal_id = p.grantee_principal_id
    WHERE dp.name = N'bdx_readonly' AND p.permission_name = N'CONTROL' AND p.state_desc = N'DENY'
)
    REVOKE CONTROL FROM [bdx_readonly];
GO

-- ── 4. (Later, for PROD) same mapping in SBO_LEISINGER ────────────────────
-- USE [SBO_LEISINGER];
-- IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'bdx_readonly')
--     CREATE USER [bdx_readonly] FOR LOGIN [bdx_readonly];
-- ALTER ROLE [db_datareader] ADD MEMBER [bdx_readonly];
-- GRANT CONNECT TO [bdx_readonly];
-- GO

-- ── 5. VERIFY everything (all 3 result grids must show bdx_readonly) ──────
SELECT name, default_database_name, is_disabled,
       LOGINPROPERTY(name,'IsLocked') AS is_locked,
       LOGINPROPERTY(name,'BadPasswordCount') AS bad_pw_count
FROM sys.server_principals WHERE name = N'bdx_readonly';
GO

USE [DEV_SBO_LEISINGER];
SELECT dp.name AS db_user, dp.type_desc,
       p.permission_name, p.state_desc AS perm_state
FROM sys.database_principals dp
LEFT JOIN sys.database_permissions p
     ON p.grantee_principal_id = dp.principal_id AND p.permission_name = N'CONNECT'
WHERE dp.name = N'bdx_readonly';
GO

USE [DEV_SBO_LEISINGER];
SELECT dp.name AS db_user, rp.name AS role_name
FROM sys.database_principals dp
JOIN sys.database_role_members drm ON drm.member_principal_id = dp.principal_id
JOIN sys.database_principals rp ON rp.principal_id = drm.role_principal_id
WHERE dp.name = N'bdx_readonly';
GO
