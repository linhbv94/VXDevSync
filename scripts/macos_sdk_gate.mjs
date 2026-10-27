#!/usr/bin/env node
// macOS suite baseline27.0. No metadata rewriting, downloads or global xcode-select.
import {execFileSync, spawnSync} from 'node:child_process';
import {existsSync, readdirSync, appendFileSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
const baseline = '27.0';
const args = process.argv.slice(2);
const run = (cmd, argv, env=process.env) => execFileSync(cmd, argv, {encoding:'utf8',env}).trim();
function checkSDK(env=process.env) {
  const version=run('xcrun',['--sdk','macosx','--show-sdk-version'],env);
  if(version!==baseline) throw Error(`macOS SDK ${version}, required ${baseline}. Select a matching DEVELOPER_DIR; no fallback.`);
  if(env.SDKROOT) { const selected=run('xcrun',['--sdk',env.SDKROOT,'--show-sdk-version'],env); if(selected!==baseline) throw Error('SDKROOT points at '+selected+', required '+baseline); }
  return run('xcrun',['--sdk','macosx','--show-sdk-path'],env);
}
function verify(binary) {
  const versions=[...run('xcrun',['vtool','-show-build',binary]).matchAll(/^\s*sdk\s+(\S+)/gm)].map(m=>m[1]);
  if(!versions.length || versions.some(v=>v!==baseline)) throw Error(`Artifact SDK mismatch ${binary}: ${versions.join(',')}`);
  console.log(`SDK ${baseline} PASS: ${binary}`);
}
try {
  if(process.platform!=='darwin') { console.log('macOS SDK gate: skipped on '+process.platform); }
  else if(args[0]==='--artifact') { if(!args[1]) throw Error('Missing artifact path'); verify(resolve(args[1])); }
  else if(args[0]==='--select-ci') {
    const current=process.env.DEVELOPER_DIR;
    const candidates=[current,...readdirSync('/Applications').filter(n=>n.startsWith('Xcode')&&n.endsWith('.app')).map(n=>join('/Applications',n,'Contents/Developer')),'/Library/Developer/CommandLineTools'].filter(Boolean);
    let selected;
    for(const dir of [...new Set(candidates)]) { try {const env={...process.env,DEVELOPER_DIR:dir}; delete env.SDKROOT; const sdk=checkSDK(env); selected={dir,sdk};break;}catch{} }
    if(!selected) throw Error('No installed toolchain contains required macOS SDK27.0. Install/provision the matching Xcode image; do not use latest/fallback.');
    if(!process.env.GITHUB_ENV) throw Error('--select-ci requires GITHUB_ENV');
    appendFileSync(process.env.GITHUB_ENV,`DEVELOPER_DIR=${selected.dir}\nSDKROOT=${selected.sdk}\n`);
    console.log('Selected SDK27.0: '+selected.dir);
  } else { console.log('SDK27.0 PASS: '+checkSDK()); }
} catch(error) {console.error(error.message);process.exit(1);}
