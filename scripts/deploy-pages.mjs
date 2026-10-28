import { execFileSync } from 'node:child_process';
import { build } from './build.mjs';

// Manual publish of dist/ to the gh-pages branch (alternative to the Actions workflow).
const dist = await build({ quiet: true });
const run = (...a) => execFileSync('git', a, { cwd: dist, stdio: 'inherit' });
const remote = execFileSync('git', ['remote', 'get-url', 'origin']).toString().trim();
run('init', '-q');
run('checkout', '-q', '-b', 'gh-pages');
run('add', '-A');
run('commit', '-q', '-m', 'Deploy');
run('push', '-f', remote, 'gh-pages');
