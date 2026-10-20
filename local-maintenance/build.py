"""Build this unofficial patch using a project-local or explicitly supplied JDK."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
jdks = list((root / '.local' / 'jdk').glob('*/bin/javac.exe'))
if jdks:
    env['JAVA_HOME'] = str(jdks[0].parents[1])
if not env.get('JAVA_HOME'):
    sys.exit('Set JAVA_HOME to a JDK 17+ installation, or prepare .local/jdk first.')
env['GRADLE_USER_HOME'] = str(root / '.local' / 'gradle')
env['VERSION_TYPE'] = 'unofficial'
env['VERSION_ROOT'] = '3.17.local-downloads'
env['GITHUB_SHA'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
with (root / '.local' / 'build.log').open('w', encoding='utf-8') as log:
    result = subprocess.run(['cmd.exe', '/d', '/c', 'gradlew.bat', '--no-daemon', '--console=plain',
                             ':HMCL:makeExecutables', ':HMCL:test', *sys.argv[1:]],
                            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
print('Build exit code:', result.returncode)
print('Log:', root / '.local' / 'build.log')
sys.exit(result.returncode)
