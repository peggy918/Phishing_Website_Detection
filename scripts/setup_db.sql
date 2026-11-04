-- Creates the PhishGuard database and the application login. Run once with Windows authentication:
--   sqlcmd -S localhost -E -C -i "scripts\setup_db.sql" -v APP_PASSWORD="your-password"
-- Put the same password in DB_PASSWORD in .env. The login can only read and write data;
-- tables are created by alembic using Windows authentication.
--
-- Keep this file ASCII only. sqlcmd reads files in the system code page (cp950 here), so UTF-8
-- Chinese comments can swallow the following line and silently skip statements.
:On Error exit

IF DB_ID(N'PhishGuard') IS NULL
    CREATE DATABASE PhishGuard COLLATE Chinese_Taiwan_Stroke_CI_AS;
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'phishguard_app')
    CREATE LOGIN phishguard_app WITH PASSWORD = N'$(APP_PASSWORD)', DEFAULT_DATABASE = PhishGuard, CHECK_POLICY = ON;
GO
USE PhishGuard;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'phishguard_app')
    CREATE USER phishguard_app FOR LOGIN phishguard_app;
ALTER ROLE db_datareader ADD MEMBER phishguard_app;
ALTER ROLE db_datawriter ADD MEMBER phishguard_app;
GO
PRINT 'PhishGuard database and login are ready.';
GO
