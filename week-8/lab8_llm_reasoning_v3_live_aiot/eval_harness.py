"""Lab 8 v3 - Evaluation harness (C7).

Runs every scenario timeline step through all three tiers
(sensor-only / sensor+AI / sensor+AI+LLM) and measures, against the
GROUND_TRUTH labels:

  * accuracy        - exact-match rate of each tier vs expected risk
  * mean risk gap   - mean |risk_order(pred) - risk_order(expected)| (how far off)
  * LLM-changed     - how often the LLM tier changed the rule-based (AI) risk
  * latency         - avg LLM latency per mode

Usage:
    python eval_harness.py                # LLM tier = mock only (offline, free)
    python eval_harness.py --modes mock,api   # also evaluate Gemini (uses quota)

Writes outputs/eval_report.csv and prints a summary table.
"""
from __future__ import annotations

import sys
from statistics import mean

from app import (
    SCENARIOS, GROUND_TRUTH, OUTPUT_DIR, risk_order,
    sensor_only_decision, sensor_ai_decision, build_context_packet, reason_with_llm,
    write_csv_row,
)


def parse_modes(argv: list[str]) -> list[str]:
    for i, a in enumerate(argv):
        if a == '--modes' and i + 1 < len(argv):
            return [m.strip() for m in argv[i + 1].split(',') if m.strip()]
        if a.startswith('--modes='):
            return [m.strip() for m in a.split('=', 1)[1].split(',') if m.strip()]
    return ['mock']


def gap(pred: str, expected: str) -> int:
    return abs(risk_order(pred) - risk_order(expected))


def main() -> None:
    modes = parse_modes(sys.argv[1:])
    report_path = OUTPUT_DIR / 'eval_report.csv'
    if report_path.exists():
        report_path.unlink()

    # accumulators
    sensor_hits, ai_hits = [], []
    sensor_gaps, ai_gaps = [], []
    llm_hits = {m: [] for m in modes}
    llm_gaps = {m: [] for m in modes}
    llm_lat = {m: [] for m in modes}
    llm_changed = {m: 0 for m in modes}
    total_steps = 0

    for sid, scen in SCENARIOS.items():
        timeline = scen['timeline']
        gt = GROUND_TRUTH.get(sid, [])
        for i, step in enumerate(timeline):
            expected = gt[i] if i < len(gt) else ''
            sensors = dict(step)
            s_risk = sensor_only_decision(sensors, sid)['risk_level']
            a_risk = sensor_ai_decision(sensors, sid)['risk_level']
            total_steps += 1
            if expected:
                sensor_hits.append(s_risk == expected); sensor_gaps.append(gap(s_risk, expected))
                ai_hits.append(a_risk == expected); ai_gaps.append(gap(a_risk, expected))

            row = {'scenario_id': sid, 'step': i, 'expected': expected,
                   'sensor_risk': s_risk, 'ai_risk': a_risk}
            for m in modes:
                ctx = build_context_packet(sensors, sid)
                res = reason_with_llm(ctx, mode=m)
                l_risk = res['final_decision']['risk_level']
                row[f'{m}_risk'] = l_risk
                row[f'{m}_latency_ms'] = res['latency_ms']
                llm_lat[m].append(res['latency_ms'])
                if l_risk != a_risk:
                    llm_changed[m] += 1
                if expected:
                    llm_hits[m].append(l_risk == expected); llm_gaps[m].append(gap(l_risk, expected))
            write_csv_row(report_path, row)

    def pct(xs): return f'{100 * mean(xs):.0f}%' if xs else 'n/a'
    def avg(xs): return f'{mean(xs):.2f}' if xs else 'n/a'

    print(f'\n=== Lab 8 eval ({total_steps} steps across {len(SCENARIOS)} scenarios) ===')
    print(f'{"tier":<22}{"accuracy":<12}{"mean risk gap":<16}{"avg latency":<14}')
    print('-' * 64)
    print(f'{"sensor_only":<22}{pct(sensor_hits):<12}{avg(sensor_gaps):<16}{"-":<14}')
    print(f'{"sensor+ai":<22}{pct(ai_hits):<12}{avg(ai_gaps):<16}{"-":<14}')
    for m in modes:
        label = f'sensor+ai+llm:{m}'
        print(f'{label:<22}{pct(llm_hits[m]):<12}{avg(llm_gaps[m]):<16}{avg(llm_lat[m]) + " ms":<14}')
    print('-' * 64)
    for m in modes:
        print(f'LLM tier ({m}) changed the rule-based risk on {llm_changed[m]}/{total_steps} steps')
    print(f'\nWrote {report_path}')


if __name__ == '__main__':
    main()
