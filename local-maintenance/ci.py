"""Detect upstream changes, apply the reviewed patch, and package release sources."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream-source'
PATCH = ROOT / 'local-maintenance/region-downloads.patch'
TARGET = 'HMCL/src/main/java/org/jackhuang/hmcl/util/RegionUtils.java'


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def detect():
    sha = git('ls-remote', 'https://github.com/HMCL-dev/HMCL.git', 'refs/heads/main').split()[0]
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Invalid upstream SHA')
    tag = f'local-{sha[:12]}-{os.environ["GITHUB_SHA"][:12]}'
    request = urllib.request.Request(
        f'https://api.github.com/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/tags/{tag}',
        headers={'Authorization': f'Bearer {os.environ["GH_TOKEN"]}',
                 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            changed = json.load(response)['draft']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        changed = True
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'upstream={sha}\ntag={tag}\nchanged={str(changed).lower()}\n')
    print(f'Upstream: {sha}; release: {tag}; build required: {changed}')


def prepare():
    subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=SOURCE, check=True)
    subprocess.run(['git', 'apply', str(PATCH)], cwd=SOURCE, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=SOURCE, check=True)
    changed = git('diff', '--name-only', cwd=SOURCE).splitlines()
    if changed != [TARGET]:
        raise RuntimeError(f'Unexpected patch scope: {changed}')
    if not re.search(r'public static boolean isIsChinaMainlandNetwork\(\)\s*\{\s*return false;\s*\}',
                     (SOURCE / TARGET).read_text(encoding='utf-8')):
        raise RuntimeError('Expected download decision missing')


def package():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    artifacts = list((SOURCE / 'HMCL/build/libs').glob('HMCL-*'))
    for extension in ('.exe', '.jar', '.sh'):
        if not any(p.suffix == extension for p in artifacts):
            raise RuntimeError(f'Missing artifact: {extension}')
    for path in artifacts:
        if path.is_file():
            shutil.copy2(path, dist / path.name)
    metadata = dict(upstream_repository='https://github.com/HMCL-dev/HMCL',
                    upstream_sha=os.environ['UPSTREAM_SHA'],
                    maintenance_repository=os.environ['GITHUB_REPOSITORY'],
                    maintenance_sha=os.environ['GITHUB_SHA'],
                    patch_sha256=hashlib.sha256(PATCH.read_bytes()).hexdigest(),
                    workflow_run=f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}')
    (dist / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    with zipfile.ZipFile(dist / 'patched-source.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        # Use the Git index to exclude build outputs while reading the patched working files.
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=SOURCE).decode().split('\0')
        for name in filter(None, tracked):
            archive.write(SOURCE / name, 'source/' + name)
        for path in (ROOT / 'local-maintenance').rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                archive.write(path, 'maintenance/' + path.relative_to(ROOT).as_posix())
        archive.write(ROOT / '.github/workflows/local-downloads-release.yml', 'maintenance/workflow.yml')
        archive.writestr('provenance.json', json.dumps(metadata, indent=2))
    notes = (
        '# Unofficial HMCL local-downloads build\n\n'
        'Modified version: the network-region download gate returns false. '
        'Machine-region detection and original copyright notices are retained.\n\n'
        f'Upstream commit: `{metadata["upstream_sha"]}`\n\n'
        f'Maintenance commit: `{metadata["maintenance_sha"]}`\n\n'
        'Includes EXE/JAR/SH, checksums, exact patched source and build provenance. '
        'Compilation and HMCL tests passed; GUI installation and game launch were not verified in CI.\n\n'
        'Microsoft login and CurseForge require separately configured API credentials. '
        'This build is unofficial and is not signed by the HMCL project.\n')
    (dist / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
                   for p in sorted(dist.iterdir()) if p.is_file() and p.name != 'SHA256SUMS')
    (dist / 'SHA256SUMS').write_text(sums, encoding='utf-8')


if __name__ == '__main__':
    {'detect': detect, 'prepare': prepare, 'package': package}[sys.argv[1]]()
