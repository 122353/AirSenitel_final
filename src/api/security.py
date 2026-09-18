import os

def is_production_mode() -> bool:
    env = os.environ.get('AIRSENTINEL_ENV', 'local')
    has_cloud_run = 'K_SERVICE' in os.environ
    return env != 'local' or has_cloud_run

def authority_dashboard_production_ready() -> bool:
    auth_required = os.environ.get('AIRSENTINEL_AUTH_REQUIRED', 'false').lower() == 'true'
    trust_iam = os.environ.get('AIRSENTINEL_TRUST_CLOUD_RUN_IAM', 'false').lower() == 'true'
    return auth_required and trust_iam
