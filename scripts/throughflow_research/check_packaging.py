"""Inspect a built wheel and smoke-test it outside the checkout with Python -I."""
import argparse
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True)
    args = parser.parse_args()
    wheels = sorted((ROOT / 'build/throughflow_research/wheels').glob('sunimuhendis-*.whl'))
    if len(wheels) != 1:
        raise RuntimeError('Expected exactly one SuniMuhendis wheel, found {}'.format(len(wheels)))
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
    baseline = json.loads((ROOT / 'reports/throughflow_phase_0_2/heat_exchanger_baseline.json').read_text(encoding='utf-8'))
    case = baseline['cases'][0]
    code = '''import json, sys
from pathlib import Path
import sunimuhendis
from sunimuhendis import make_env, list_environments
from sunimuhendis.prompts.templates import build_heat_exchanger_prompt
payload = json.loads(sys.stdin.read())
assert "site-packages" in str(Path(sunimuhendis.__file__).resolve())
assert "turbodesign" not in sys.modules
result = make_env("heat_exchanger").evaluate("consumer", payload["task"], "design", payload["design"])
assert result.status == "success"
assert build_heat_exchanger_prompt(payload["task"])
print(json.dumps({"import_path":sunimuhendis.__file__, "environments":list_environments(), "status":result.status, "score":result.score.normalized_total, "metrics":result.metrics, "nasa_imported":"turbodesign" in sys.modules}))
'''
    with tempfile.TemporaryDirectory(prefix='sunimuhendis-consumer-') as cwd:
        run = subprocess.run([args.python, '-I', '-c', code], input=json.dumps(case), capture_output=True, text=True, cwd=cwd, timeout=60)
    if run.returncode:
        raise RuntimeError(run.stderr)
    result = json.loads(run.stdout)
    payload = {'wheel': wheel.name, 'files': files, 'consumer': result,
               'prompts_shipped': any(p.startswith('sunimuhendis/prompts/') for p in files),
               'harness_shipped': any(p.startswith(('sunimuhendis/model_clients/', 'sunimuhendis/baselines/')) for p in files),
               'baseline_score_identical': result['score'] == case['result']['score']['normalized_total'],
               'baseline_metrics_identical': result['metrics'] == case['result']['metrics']}
    assert payload['prompts_shipped'] and not payload['harness_shipped']
    assert payload['baseline_score_identical'] and payload['baseline_metrics_identical']
    output = ROOT / 'reports/throughflow_phase_0_2/packaging_baseline.json'
    output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k not in ('files', 'consumer')}))


if __name__ == '__main__':
    main()
