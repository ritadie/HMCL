"""Detect upstream changes, apply the reviewed patch, and package release sources."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

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
    executables = list((SOURCE / 'HMCL/build/libs').glob('HMCL-*.exe'))
    if len(executables) != 1:
        raise RuntimeError(f'Expected one EXE, found {len(executables)}')
    shutil.copy2(executables[0], dist / executables[0].name)
    # An independent source snapshot makes GitHub's automatic source archives
    # match this build, even when upstream has advanced beyond the maintenance branch.
    git('add', '--', TARGET, cwd=SOURCE)
    tree = git('write-tree', cwd=SOURCE)
    source_date = git('show', '-s', '--format=%cI', 'HEAD', cwd=SOURCE)
    source_commit = subprocess.check_output(
        ['git', '-c', 'user.name=github-actions[bot]',
         '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
         'commit-tree', tree, '-m', f'Unofficial patched source for upstream {os.environ["UPSTREAM_SHA"]}'],
        cwd=SOURCE, text=True,
        env={**os.environ, 'GIT_AUTHOR_DATE': source_date, 'GIT_COMMITTER_DATE': source_date}).strip()
    tag_ref = 'refs/tags/' + os.environ['RELEASE_TAG']
    git('update-ref', tag_ref, source_commit, cwd=SOURCE)
    git('bundle', 'create', str(dist / 'source.bundle'), tag_ref, cwd=SOURCE)
    notes = (
        '# Unofficial HMCL local-downloads build\n\n'
        'Modified version: the network-region download gate returns false. '
        'Machine-region detection and original copyright notices are retained.\n\n'
        f'Upstream commit: `{os.environ["UPSTREAM_SHA"]}`\n\n'
        f'Maintenance commit: `{os.environ["GITHUB_SHA"]}`\n\n'
        'Download the EXE below. GitHub Source code (zip/tar.gz) contains the exact patched source. '
        'Compilation and HMCL tests passed; GUI installation and game launch were not verified in CI.\n\n'
        'Microsoft login and CurseForge require separately configured API credentials. '
        'This build is unofficial and is not signed by the HMCL project.\n')
    (dist / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')


if __name__ == '__main__':
    {'detect': detect, 'prepare': prepare, 'package': package}[sys.argv[1]]()
