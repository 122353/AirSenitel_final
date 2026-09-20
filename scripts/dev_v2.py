"""Start both local services using explicit, never-printed configuration.

Existing key files and ZIP .env can be loaded into process memory only. Nothing
is copied to the checkout or browser except the Clerk *publishable* key.
"""
import argparse
import os
import subprocess
import sys
import zipfile
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def configuration(args):
    env = os.environ.copy()
    for path in args.env_file:
        env.update({k: v for k, v in dotenv_values(path).items() if v is not None})
    if args.source_zip:
        with zipfile.ZipFile(args.source_zip) as archive:
            values = dotenv_values(stream=StringIO(archive.read('.env').decode('utf-8-sig')))
            if values.get('OPENAQ_API_KEY'):
                env['OPENAQ_API_KEY'] = values['OPENAQ_API_KEY']
    env['AIRSENTINEL_ENV'] = 'local'
    env['AIRSENTINEL_STORE'] = args.store
    env['AIRSENTINEL_SQLITE_PATH'] = str(ROOT / '.local' / 'evidence.sqlite3')
    env['CLERK_AUTHORIZED_PARTIES'] = 'http://localhost:3000'
    env['VITE_CLERK_PUBLISHABLE_KEY'] = env.get('VITE_CLERK_PUBLISHABLE_KEY') or env.get('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY', '')
    if not env.get('CLERK_SECRET_KEY') or not env.get('VITE_CLERK_PUBLISHABLE_KEY'):
        raise SystemExit('Missing Clerk configuration. Supply an existing private --env-file; never put keys in source.')
    if args.store == 'postgres' and not env.get('DATABASE_URL'):
        raise SystemExit('Postgres selected but DATABASE_URL is missing.')
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', action='append', default=[])
    parser.add_argument('--source-zip')
    parser.add_argument('--store', choices=['sqlite', 'postgres'], default='sqlite')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--initialize-store', action='store_true')
    args = parser.parse_args()
    env = configuration(args)
    if args.check:
        print('Local configuration verified; secret values not displayed.')
        return
    if args.initialize_store:
        subprocess.run([sys.executable, '-c', 'from src.services.case_store_v2 import initialize_store; from src.services.devices_v2 import initialize_devices; initialize_store(); initialize_devices(); print("Evidence and device tables initialized")'], cwd=ROOT, env=env, check=True)
        return
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT, env=env))
        # Calling node directly avoids shell interpolation of environment values.
        processes.append(subprocess.Popen(['node', str(ROOT / 'dashboard/node_modules/vite/bin/vite.js'), '--host', 'localhost', '--port', '3000', '--strictPort'], cwd=ROOT / 'dashboard', env=env))
        print('AirSentinel local review: http://localhost:3000. Press Ctrl+C to stop both services.', flush=True)
        while all(process.poll() is None for process in processes):
            try:
                processes[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == '__main__':
    main()
