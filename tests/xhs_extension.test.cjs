const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function fixture() {
  const created = [], updated = [], removed = [], scripts = [];
  const session = {};
  const noop = {addListener() {}};
  const chrome = {
    runtime: {id: 'test-extension', onMessage: noop, onInstalled: noop, onStartup: noop,
      getPlatformInfo: async () => ({os:'win'})},
    alarms: {onAlarm: noop},
    windows: {getLastFocused: async () => ({id: 7, incognito: false})},
    storage: {session: {
      get: async key => ({[key]: session[key]}),
      set: async values => Object.assign(session, values)
    }},
    tabs: {
      create: async options => {created.push(options); return {id: 88};},
      get: async id => ({id, url: 'https://www.xiaohongshu.com/explore/1234567890abcdef12345678'}),
      update: async (...args) => updated.push(args),
      remove: async id => removed.push(id)
    },
    scripting: {executeScript: async options => {scripts.push(options); return [{result:{content:true}}];}}
  };
  const context = vm.createContext({chrome, URL, Date, Set, Error, setTimeout,
    AbortSignal, crypto: require('node:crypto').webcrypto});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../chrome_extension/background.js'), 'utf8'), context);
  const run = code => vm.runInContext(code, context);
  return {run, created, updated, removed, scripts, session, chrome, context};
}
const command = (op, extra = {}) => JSON.stringify({op, deadline: Date.now() + 30000, ...extra});

test('capture opens inactive in the existing window and owns only that tab', async () => {
  const f = fixture();
  assert.equal(await f.run(`handleCommand(${command('open', {url:'https://xhslink.cn/o/example'})})`), 88);
  assert.deepEqual(JSON.parse(JSON.stringify(f.created)), [{windowId:7, url:'https://xhslink.cn/o/example', active:false}]);
  await f.run(`handleCommand(${command('navigate', {url:'https://www.xiaohongshu.com/explore/abcdef'})})`);
  assert.equal(f.updated[0][0], 88);
  assert.equal(f.scripts[0].target.tabId, 88);
  await f.run(`handleCommand(${command('close')})`);
  assert.deepEqual(f.removed, [88]);
  assert.deepEqual(JSON.parse(JSON.stringify(f.session.ownedTabs)), []);
});

test('rejects unrelated URLs, unsupported commands and expired work before accessing tabs', async () => {
  const f = fixture();
  for (const url of ['https://example.org/', 'https://www.xiaohongshu.com.evil.org/', 'file:///tmp/x']) {
    await assert.rejects(f.run(`handleCommand(${command('open', {url})})`));
  }
  await assert.rejects(f.run('handleCommand({op:"open",url:"https://www.xiaohongshu.com/",deadline:0})'));
  await assert.rejects(f.run(`handleCommand(${command('execute', {script:'arbitrary JS'})})`));
  assert.equal(f.created.length, 0);
  assert.equal(f.scripts.length, 0);
});

test('a closed capture tab is never replaced by the currently selected user tab', async () => {
  const f = fixture();
  await f.run(`handleCommand(${command('open', {url:'https://www.xiaohongshu.com/'})})`);
  f.chrome.tabs.get = async () => {throw new Error('No such tab');};
  await assert.rejects(f.run(`handleCommand(${command('snapshot')})`));
  assert.equal(f.created.length, 1);
  assert.equal(f.scripts.length, 0);
});

test('only the requested note is read, with zero counts preserved', () => {
  const f = fixture();
  const noteId = '1234567890abcdef12345678';
  f.run(`globalThis.location = {href:'https://www.xiaohongshu.com/explore/${noteId}', pathname:'/explore/${noteId}'};
    globalThis.document = {title:'note', body:{innerText:'不要删除'}, querySelector:()=>null, querySelectorAll:()=>[]};
    globalThis.window = {__INITIAL_STATE__:{note:{noteDetailMap:{
      other:{note:{noteId:'other', interactInfo:{likedCount:999}}},
      '${noteId}':{note:{noteId:'${noteId}', interactInfo:{likedCount:13,commentCount:11,collectedCount:0}}}
    }}}};`);
  const value = JSON.parse(JSON.stringify(f.run(`snapshot('${noteId}')`)));
  assert.equal(value.note.interactInfo.likedCount, 13);
  assert.equal(value.note.interactInfo.collectedCount, 0);
  assert.equal(f.run('snapshot("absent").note'), null);
});

test('connection dispatches task commands, returns results and cleans up after disconnect', async () => {
  const f = fixture();
  const commands = ['open', 'snapshot', 'close'].map((op, index) => ({
    id: String(index), op, deadline: Date.now() + 30000, url:'https://www.xiaohongshu.com/'
  }));
  const results = [];
  f.context.fetch = async (url, options) => {
    const endpoint = new URL(url).pathname;
    assert.equal(options.headers['X-URLHeat-Extension'], 'test-extension');
    if (endpoint === '/session') return {ok:true, json:async () => ({token:'test-task-token'})};
    assert.equal(options.headers.Authorization, 'Bearer test-task-token');
    if (endpoint === '/result') {
      results.push(JSON.parse(options.body));
      return {ok:true, json:async () => ({ok:true})};
    }
    if (!commands.length) throw new Error('Task finished, bridge closed');
    return {ok:true, json:async () => ({command:commands.shift()})};
  };
  await f.run('connect()');
  assert.equal(results.length, 3);
  assert.equal(results[0].value, 88);
  assert.equal(results[1].value.content, true);
  assert.equal(results[2].value, true);
  assert.equal(f.created[0].active, false);
  assert.deepEqual(f.removed, [88]);
  assert.equal(f.run('running'), false);
});
