# BDX Intelligence – collector + API image
#
# NOTE: Inside a Linux container Windows integrated authentication against the
# SAP SQL Server is NOT available.  The container needs a SQL login
# (SAP_DB_TRUSTED_CONNECTION=no, SAP_DB_USER/SAP_DB_PASSWORD, e.g. bdx_readonly).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ACCEPT_EULA=Y

# Microsoft ODBC Driver 18 for SQL Server + unixODBC
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg2 ca-certificates apt-transport-https \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --upgrade pip && pip install ".[mqtt,kafka]"

# Non-root runtime user
RUN useradd --create-home --uid 10001 bdx && chown -R bdx:bdx /app
USER bdx

ENV SAP_DB_ODBC_DRIVER="ODBC Driver 18 for SQL Server" \
    LOG_FORMAT=json \
    API_HOST=0.0.0.0 \
    API_PORT=8085

EXPOSE 8085

# Default: API + dashboard.  Collector service overrides the command (see docker-compose.yml).
CMD ["bdx-collect", "serve"]
