"""Generate a capability observation table from actual subprocess probe records."""
import collections
import json
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / 'reports/throughflow_phase_0_2'


def describe(record):
    if record['status'] != 'completed':
        return record.get('error', record['status']).replace('\n', ' ').replace('|', '/')[:230]
    s = record['solves'][-1]
    return 'P={:.3f} kW; PR={:.6f}; row mdot spread={:.5f}%; eta_p={:.6f}'.format(
        s['power_W']/1000, s['pressure_ratio'], 100*s['row_massflow_spread_relative'], s['eta_polytropic'])


def main():
    groups = {}
    lines = ['# Throughflow capability observations', '',
             'These are observed executions, not certified support or physical validation.', '',
             'All scenarios use NASA commit `23c2b0bf781b4b030014f458ecfde872896777a2`.', '',
             'Explicit `fixed_streamlines` cases disable upstream streamline adjustment; they do not reduce the requested streamline count.', '',
             'Row massflow spread is `(max - min) / abs(mean)` over `total_massflow_no_coolant`. It is a diagnostic, not a full energy/radial-equilibrium acceptance test.', '']
    for directory in sorted((REPORTS / 'probes').iterdir()):
        if not directory.is_dir():
            continue
        records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('*.json'))]
        counts = dict(collections.Counter(r['status'] for r in records))
        times = [r['elapsed_seconds'] for r in records if 'elapsed_seconds' in r]
        memory = [r['peak_working_set_bytes'] for r in records if 'peak_working_set_bytes' in r]
        groups[directory.name] = {'counts': counts, 'cases': len(records),
                                 'median_process_elapsed_seconds': statistics.median(times) if times else None,
                                 'maximum_process_elapsed_seconds': max(times) if times else None,
                                 'max_peak_working_set_bytes': max(memory) if memory else None}
        lines += ['## ' + directory.name, '', json.dumps(groups[directory.name]), '',
                  '| Case | Observed status | Result / diagnostic |', '|---|---|---|']
        for r in records:
            lines.append('| {} | {} | {} |'.format(r['case']['id'],r['status'],describe(r)))
        lines.append('')
    xml = {}
    for p in sorted(REPORTS.glob('*.xml')):
        tree = ET.parse(p)
        suites = tree.findall('.//testsuite')
        xml[p.name] = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ('tests','failures','errors','skipped')}
        xml[p.name]['expected_failure_reasons'] = [n.attrib.get('message') for n in tree.findall('.//skipped') if n.attrib.get('type') == 'pytest.xfail']
    summary = {'groups': groups, 'test_reports': xml}
    (REPORTS/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (REPORTS/'capability_matrix.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
