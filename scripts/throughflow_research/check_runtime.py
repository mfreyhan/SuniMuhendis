"""Record import and dependency health with an explicitly selected interpreter."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    code = 'import sys, json; print(json.dumps({"python":sys.version})); import turbodesign; print(turbodesign.__file__)'
    imported = subprocess.run([args.python, '-c', code], capture_output=True, text=True, timeout=90)
    checked = subprocess.run([args.python, '-m', 'pip', 'check'], capture_output=True, text=True, timeout=90)
    packages = subprocess.run([args.python, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True, timeout=90, check=True)
    payload = {'interpreter': args.python, 'import': {'returncode': imported.returncode, 'stdout': imported.stdout, 'stderr': imported.stderr},
               'pip_check': {'returncode': checked.returncode, 'stdout': checked.stdout, 'stderr': checked.stderr},
               'packages': json.loads(packages.stdout)}
    output = ROOT / 'reports/throughflow_phase_0_2' / ('runtime_' + args.label + '.json')
    output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(args.label, 'import return code:', imported.returncode, 'pip check:', checked.returncode)


if __name__ == '__main__':
    main()
