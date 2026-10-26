import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync('frontend/js/app.js','utf8');
const helper=source.match(/function escapeHtml\(value\) \{[\s\S]*?\n\}/)[0];
test('untrusted repository/skill/path labels cannot become bridge-capable HTML',()=>{
 const context=vm.createContext({});vm.runInContext(helper,context);
 const result=context.escapeHtml('<img src=x onerror="window.pywebview.api.install_update()">');
 assert.ok(!result.includes('<')&&!result.includes('>')&&!result.includes('"'));
 assert.match(result,/&lt;img/);
 for(const name of ['repo.name','repo.rel_path','repo.current_branch','skill.name','item.name','cfg.skills_sync.skills_lib','cfg.skills_sync.git_repo']){
  assert.ok(source.includes('${escapeHtml('+name+')}'),name);
  assert.ok(!source.includes('${'+name+'}'),name);
 }
});
