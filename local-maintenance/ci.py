"""Detect upstream changes, apply the reviewed patch, and package release sources."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream-source'
PATCH = ROOT / 'local-maintenance/official-release.patch'
TARGET = 'HMCL/src/main/java/org/jackhuang/hmcl/util/RegionUtils.java'
METADATA = 'HMCL/src/main/java/org/jackhuang/hmcl/Metadata.java'
TARGETS = sorted([TARGET, METADATA])


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def github_json(path):
    request = urllib.request.Request(
        'https://api.github.com' + path,
        headers={'Authorization': f'Bearer {os.environ["GH_TOKEN"]}',
                 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def detect():
    releases = github_json('/repos/HMCL-dev/HMCL/releases?per_page=100')
    candidates = [r for r in releases if not r['draft']
                  and re.fullmatch(r'v\d+(?:\.\d+){2,3}', r['tag_name'])]
    if not candidates:
        raise RuntimeError('No supported official release found')
    latest = max(candidates, key=lambda r: r['published_at'])
    tag = latest['tag_name']
    version = tag[1:]
    version_root, build_number = version.rsplit('.', 1)
    refs = dict(line.split()[::-1] for line in git(
        'ls-remote', 'https://github.com/HMCL-dev/HMCL.git',
        f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}').splitlines())
    sha = refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}', ''))
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Official release tag did not resolve to a commit')
    try:
        previous = github_json(f'/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/tags/{tag}')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        previous = None
    changed = previous is None or previous['draft']
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'upstream={sha}\ntag={tag}\nchanged={str(changed).lower()}\n'
                     f'version={version}\nversion_root={version_root}\nbuild_number={build_number}\n')
    print(f'Upstream: {sha}; release: {tag}; build required: {changed}')


def prepare():
    subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=SOURCE, check=True)
    subprocess.run(['git', 'apply', str(PATCH)], cwd=SOURCE, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=SOURCE, check=True)
    changed = git('diff', '--name-only', cwd=SOURCE).splitlines()
    if changed != TARGETS:
        raise RuntimeError(f'Unexpected patch scope: {changed}')
    if not re.search(r'public static boolean isIsChinaMainlandNetwork\(\)\s*\{\s*return false;\s*\}',
                     (SOURCE / TARGET).read_text(encoding='utf-8')):
        raise RuntimeError('Expected download decision missing')
    if 'public static final String NAME = "HMCL Modified";' not in (SOURCE / METADATA).read_text(encoding='utf-8'):
        raise RuntimeError('Modified application name missing')


def package():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    executables = list((SOURCE / 'HMCL/build/libs').glob('HMCL-*.exe'))
    if len(executables) != 1:
        raise RuntimeError(f'Expected one EXE, found {len(executables)}')
    shutil.copy2(executables[0], dist / executables[0].name)
    # An independent source snapshot makes GitHub's automatic source archives
    # match this build, even when upstream has advanced beyond the maintenance branch.
    git('add', '--', *TARGETS, cwd=SOURCE)
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
        f'<!-- build-key:{os.environ["UPSTREAM_SHA"]}:{os.environ["GITHUB_SHA"]} -->\n\n'
        'Download the EXE below. GitHub Source code (zip/tar.gz) contains the exact patched source. '
        'Compilation and HMCL tests passed; GUI installation and game launch were not verified in CI.\n\n'
        'Microsoft login and CurseForge require separately configured API credentials. '
        'This build is unofficial and is not signed by the HMCL project.\n')
    (dist / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')


if __name__ == '__main__':
    {'detect': detect, 'prepare': prepare, 'package': package}[sys.argv[1]]()
