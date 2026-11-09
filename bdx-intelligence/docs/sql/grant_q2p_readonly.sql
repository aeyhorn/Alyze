-- ═══════════════════════════════════════════════════════════════════════════════
-- BDX Intelligence – additional SELECT grants for Quote-to-Promise
--
-- Run on LDSAP against each company DB that already has [bdx_readonly].
-- Safe to re-run.  No write grants.
-- ═══════════════════════════════════════════════════════════════════════════════

USE [DEV_SBO_LEISINGER];
GRANT SELECT ON dbo.OITW TO [bdx_readonly];
GRANT SELECT ON dbo.OPOR TO [bdx_readonly];
GRANT SELECT ON dbo.POR1 TO [bdx_readonly];
GRANT SELECT ON dbo.OITT TO [bdx_readonly];
GRANT SELECT ON dbo.ITT1 TO [bdx_readonly];
GRANT SELECT ON dbo.ITM1 TO [bdx_readonly];
GRANT SELECT ON dbo.OPLN TO [bdx_readonly];
GO

USE [SBO_LEISINGER];
GRANT SELECT ON dbo.OITW TO [bdx_readonly];
GRANT SELECT ON dbo.OPOR TO [bdx_readonly];
GRANT SELECT ON dbo.POR1 TO [bdx_readonly];
GRANT SELECT ON dbo.OITT TO [bdx_readonly];
GRANT SELECT ON dbo.ITT1 TO [bdx_readonly];
GRANT SELECT ON dbo.ITM1 TO [bdx_readonly];
GRANT SELECT ON dbo.OPLN TO [bdx_readonly];
GO

PRINT 'Q2P SELECT grants applied.';
