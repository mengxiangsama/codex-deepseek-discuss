"""Offline order-event benchmark. Never calls a model or executes model output."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, data):
    # Do not silently overwrite previous evidence.
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def reference(events):
    status, stock, refunds, seen = 'pending', 9, 0, set()
    for event in events:
        kind, event_id = event['kind'], event['id']
        if event_id in seen:
            continue
        seen.add(event_id)
        if kind == 'timeout' and status == 'pending':
            status, stock = 'closed', stock + 1
        elif kind == 'payment':
            if status == 'pending':
                status = 'paid'
            elif status == 'closed':
                refunds += 1
    return {'status': status, 'stock': stock, 'refunds': refunds}

def grade(suite, answers):
    if not isinstance(answers, dict) or set(answers) != {c['id'] for c in suite['cases']}:
        raise ValueError('Answers must contain exactly the case IDs.')
    rows = []
    for case in suite['cases']:
        actual = answers[case['id']]
        expected = reference(case['events'])
        # bool is not an integer inventory/refund count.
        valid = (isinstance(actual, dict) and set(actual) == set(expected)
                 and type(actual['stock']) is int and type(actual['refunds']) is int)
        rows.append({'case': case['id'], 'passed': bool(valid and actual == expected),
                     'actual': actual, 'expected': expected})
    return rows

def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite non-negative number.')
    return value

def summarize(records):
    groups = {}
    for r in records:
        if r['kind'] != 'model_run':
            raise ValueError('Offline checks are not model runs.')
        if r['arm'] not in ('single', 'dual'):
            raise ValueError('Unknown arm.')
        groups.setdefault(r['suite_sha256'], {'single': [], 'dual': []})[r['arm']].append(r)
    output = []
    for suite_hash, arms in groups.items():
        result = {'suite_sha256': suite_hash, 'comparable': bool(arms['single'] and arms['dual']), 'arms': {}}
        for arm, runs in arms.items():
            costs = [r['cost_usd'] for r in runs]
            elapsed = [number(r['elapsed_seconds'], 'elapsed') for r in runs]
            for cost in costs:
                if cost is not None:
                    number(cost, 'cost')
            result['arms'][arm] = {
                'runs': len(runs), 'passed_cases': sum(sum(x['passed'] for x in r['scores']) for r in runs),
                'total_cases': sum(len(r['scores']) for r in runs),
                'elapsed_seconds': elapsed,
                'total_cost_usd': sum(costs) if runs and all(x is not None for x in costs) else None,
                'cost_note': 'Unknown stays null; subscription cost is not assumed zero.'}
        output.append(result)
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('start')
    start.add_argument('--arm', choices=['single', 'dual'], required=True)
    start.add_argument('--model', required=True, help='Exact Codex host model/settings, if known')
    start.add_argument('--suite', default=str(ROOT / 'orders.json'))
    start.add_argument('--out', required=True)
    finish = sub.add_parser('finish')
    finish.add_argument('--start', required=True)
    finish.add_argument('--answers', required=True)
    finish.add_argument('--evidence', required=True, help='Locally reviewed, sanitized transcript text')
    finish.add_argument('--cost-usd', type=float, help='Whole run cost only if known, otherwise omit')
    finish.add_argument('--out', required=True)
    report = sub.add_parser('report')
    report.add_argument('records', nargs='+')
    args = parser.parse_args()
    if args.command == 'start':
        suite = Path(args.suite).resolve()
        write(args.out, {'kind': 'started', 'arm': args.arm, 'host_model': args.model,
                         'suite': str(suite), 'suite_sha256': digest(suite),
                         'started_at': datetime.now(timezone.utc).isoformat()})
    elif args.command == 'finish':
        start = read(args.start)
        if start['kind'] != 'started' or digest(start['suite']) != start['suite_sha256']:
            raise ValueError('Invalid start or suite changed.')
        if not Path(args.evidence).read_text(encoding='utf-8').strip():
            raise ValueError('Evidence cannot be empty.')
        end = datetime.now(timezone.utc)
        elapsed = number((end - datetime.fromisoformat(start['started_at'])).total_seconds(), 'elapsed')
        cost = None if args.cost_usd is None else number(args.cost_usd, 'cost')
        scores = grade(read(start['suite']), read(args.answers))
        write(args.out, {**start, 'kind': 'model_run', 'finished_at': end.isoformat(),
                        'elapsed_seconds': elapsed, 'cost_usd': cost,
                        'evidence_sha256': digest(args.evidence), 'answers_sha256': digest(args.answers),
                        'scores': scores})
    else:
        print(json.dumps(summarize([read(p) for p in args.records]), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
