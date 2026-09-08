"""Run the same all-keyword batch as the dashboard, with bounded waits and logs."""
import argparse
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE = 'http://127.0.0.1:8001'
ROOT = Path(__file__).resolve().parents[1]


def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def run(check=False):
    deadline = time.monotonic() + 3 * 60 * 60
    for attempt in range(60):
        try:
            progress = request('/api/collect-progress/')
            break
        except (OSError, ValueError):
            if attempt == 59:
                raise RuntimeError('Local web service did not become ready')
            time.sleep(2)
    if check:
        print('Scheduler connectivity verified; no collection triggered.')
        return
    # Wait for a manually started batch; never change its keyword selection.
    while True:
        while progress.get('running'):
            if time.monotonic() >= deadline:
                raise RuntimeError('Timed out waiting for the current batch')
            time.sleep(5)
            progress = request('/api/collect-progress/')
        try:
            started = request('/api/run-collect-daily-prices/', {})
            if not started.get('ok'):
                raise RuntimeError('Collection was not accepted')
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 409 or time.monotonic() >= deadline:
                raise
            time.sleep(5)
            progress = request('/api/collect-progress/')
    print('All-keyword batch started:', started.get('total'), flush=True)
    while True:
        time.sleep(5)
        progress = request('/api/collect-progress/')
        if not progress.get('running'):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Batch exceeded three hours; inspect the dashboard before retrying')
    result = {'finished_at': datetime.now().astimezone().isoformat(), **progress}
    (ROOT / '.local' / 'last-scheduled-collection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if progress.get('error') or progress.get('skipped'):
        raise RuntimeError('Batch completed with errors or skipped keywords; see last-scheduled-collection.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Check connectivity without collecting or writing prices')
    run(parser.parse_args().check)
