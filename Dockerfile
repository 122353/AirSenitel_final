FROM python:3.11-slim

# Keep Python output visible in Cloud Run logs and avoid writing bytecode into
# the container filesystem. The service still treats its filesystem as ephemeral.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# Cloud Run uses the Google connector dependencies. Local-only builds can set
# this build argument to false, but the application keeps every connector
# disabled unless an explicit runtime environment flag enables it.
ARG INSTALL_GOOGLE_CONNECTORS=true

# This private image supports the API and authority-review dashboard only. The
# public dashboard uses Dockerfile.public and a temporary allowlisted context so
# internal CSV files cannot enter a public image.
ARG APP_TARGET=api
ENV APP_TARGET=${APP_TARGET}

COPY requirements.txt requirements-google-cloud.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_GOOGLE_CONNECTORS" = "true" ]; then \
         pip install --no-cache-dir -r requirements-google-cloud.txt; \
       fi

# Do not run the API as root. .dockerignore and .gcloudignore prevent local
# credentials, raw data and local report logs from entering the build context.
RUN addgroup --system airsentinel \
    && adduser --system --ingroup airsentinel --home /app airsentinel
COPY --chown=airsentinel:airsentinel . .

USER airsentinel
EXPOSE 8080

CMD ["sh", "-c", "case \"$APP_TARGET\" in api) exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} ;; authority-dashboard) if [ \"${AIRSENTINEL_ENABLE_AUTHORITY_DASHBOARD:-false}\" != \"true\" ] || [ \"${AIRSENTINEL_AUTH_REQUIRED:-false}\" != \"true\" ] || [ \"${AIRSENTINEL_TRUST_CLOUD_RUN_IAM:-false}\" != \"true\" ] || [ -z \"${AIRSENTINEL_CLOUD_RUN_AUTHORITY_ROLE:-}\" ]; then echo 'Refusing to start the authority dashboard without explicit private-authority safeguards.'; exit 78; fi; exec streamlit run authority_app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true --browser.gatherUsageStats=false ;; *) echo \"Unsupported private APP_TARGET: $APP_TARGET\"; exit 64 ;; esac"]
