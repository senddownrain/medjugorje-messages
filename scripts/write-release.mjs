import { writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
const sha = process.env.GITHUB_SHA || execFileSync('git', ['rev-parse', 'HEAD'], { encoding:'utf8' }).trim();
const files = await Promise.all(['ru','be','uk','hr','en','sk','lv','index'].map(async language => {
  const bytes = await readFile(new URL(`../data/${language}.json`, import.meta.url));
  return [`${language}.json`, createHash('sha256').update(bytes).digest('hex')];
}));
await writeFile(new URL('../public/release.json', import.meta.url), JSON.stringify({ sha, source_sha256:Object.fromEntries(files) })+'\n');
