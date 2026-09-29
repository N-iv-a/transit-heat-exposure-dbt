// Browser smoke test of the built map (not part of check.sh: needs node + playwright).
//   NODE_PATH=/opt/node22/lib/node_modules PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
//   node smoke_test.mjs [screenshot_dir]
// Opens dist/site over http and dist/milan_heat_map.html over file://, at 1200 and
// 375 px, and checks: no console errors, every view opens, the Heatmap button
// toggles in all views, the sun compass exists only in the main and Exposure
// views, the shadow overlay follows the hour, the tooltip has the 7-hour strip,
// the priority list moves the map, unlinked stops are drawn as hollow circles.
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, 'dist');
const shots = process.argv[2] || null;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const f = path.join(dist, 'site', decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  fs.readFile(f, (e, b) => { if (e) { res.writeHead(404); res.end(); } else { res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' }); res.end(b); } });
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/index.html`;
const targets = [['site', base], ['single', 'file://' + path.join(dist, 'milan_heat_map.html')]];

let failures = 0;
const check = (ok, msg) => { if (!ok) { failures++; console.log('  FAIL', msg); } };
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });

for (const [name, url] of targets) {
  for (const width of [1200, 375]) {
    if (process.env.ONLY && process.env.ONLY !== `${name}:${width}`) continue;
    console.log(`${name} @ ${width}px`);
    const page = await browser.newPage({ viewport: { width, height: width > 500 ? 900 : 800 } });
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(url);
    await page.waitForSelector('#stats .stat', { timeout: 30000 });
    await page.waitForTimeout(2500);
    const shot = async n => { if (shots && name === 'site') await page.screenshot({ path: path.join(shots, `t17_${n}.png`) }); };
    const layerIds = () => page.evaluate(() => window.__deck.props.layers.map(l => l.id));
    const compass = () => page.evaluate(() => !document.getElementById('compass-box').hidden);
    const clickBtn = (group, text) => page.locator(`#${group} button`).filter({ hasText: new RegExp('^' + text + '$') }).first().click();

    await shot(`initial_${width}`);
    check(await compass(), 'compass visible in main');
    check((await layerIds()).includes('stops-unlinked'), 'hollow unlinked circles layer in main');
    check((await page.locator('#legend-body').innerText()).includes('not linked to a GTFS stop'), 'legend entry for unlinked stops');
    check((await page.locator('#priority-list li').count()) === 20, 'priority list has 20 rows');
    check(await page.locator('#hour-buttons button').count() === 8, '8 hour buttons');

    // shadow follows the hour
    await clickBtn('hour-buttons', '13:00');
    const vis = async () => page.evaluate(() => window.__deck.props.layers.filter(l => l.id.startsWith('shadow-') && l.props.visible).map(l => l.id));
    const v13 = await vis(); await clickBtn('hour-buttons', '18:00'); const v18 = await vis();
    check(v13.join() === 'shadow-13' && v18.join() === 'shadow-18', `shadow layer per hour (${v13} / ${v18})`);
    await clickBtn('hour-buttons', 'Average');
    check((await vis()).length === 7, 'average shows all 7 shadow layers');

    // priority list moves the map
    const before = await page.evaluate(() => window.__viewState || null);
    await page.locator('#priority-list button').nth(2).click();
    await page.waitForTimeout(1500);
    const after = await page.evaluate(() => window.__viewState);
    check(after && (!before || Math.abs(after.zoom - before.zoom) > 0.5 || Math.abs(after.longitude - before.longitude) > 1e-4), 'priority click moved the view');
    check(await page.locator('#priority-list button[aria-current="true"]').count() === 1, 'selected priority item marked');
    check((await layerIds()).includes('pick-ring'), 'selected stop highlighted');
    await clickBtn('hour-buttons', '15:00');
    check((await page.locator('#priority-title').innerText()).includes('15:00'), 'priority list follows the hour');

    // tooltip with hour strip: hover the highlighted stop (map is centred on it)
    await page.locator('#deck-container').scrollIntoViewIfNeeded(); await page.waitForTimeout(500);
    const box = await page.locator('#deck-container').boundingBox();
    let tip = '';
    for (const [dx, dy] of [[0,0],[3,0],[-3,0],[0,3],[0,-3],[5,5],[-5,-5],[6,-4]]) {
      await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
      await page.waitForTimeout(300);
      tip = await page.evaluate(() => document.querySelector('.deck-tooltip')?.innerText || '');
      if (tip) break;
    }
    check(/13\s*14\s*15\s*16\s*17\s*18\s*19/.test(tip.replace(/\n/g, ' ')) && /score/.test(tip) && /wait/.test(tip), `tooltip has the 7-hour strip (${JSON.stringify(tip.slice(0, 60))})`);
    await page.mouse.move(2, 2);

    for (const [label, hasCompass] of [['Exposure', true], ['Wait', false], ['Trees', false], ['Sun \u00d7 wait', true]]) {
      await clickBtn('view-buttons', label);
      await page.waitForTimeout(label === 'Trees' ? 6000 : 1200);
      check(await compass() === hasCompass, `${label}: compass ${hasCompass ? 'present' : 'absent'}`);
      check(await page.evaluate(() => document.getElementById('priority').hidden) === (label !== 'Sun \u00d7 wait'), `${label}: priority panel visibility`);
      if (label === 'Exposure') { await shot(`exposure_${width}`); check((await layerIds()).some(i => i === 'shadow-13'), 'Exposure has shadow layers'); }
      if (label === 'Trees') { await shot(`trees_${width}`); check((await layerIds()).includes('trees-all'), 'trees loaded'); }
      if (label === 'Wait') check(!(await layerIds()).some(i => i.startsWith('shadow-')), 'Wait has no shadow');
      // heatmap on/off
      await page.locator('#heat-toggle').click(); await page.waitForTimeout(600);
      const on = (await layerIds()).includes('heatmap');
      await page.locator('#heat-toggle').click(); await page.waitForTimeout(300);
      const off = !(await layerIds()).includes('heatmap');
      check(on && off, `${label}: heatmap on/off`);
      if (label === 'Exposure' && width === 1200) { await page.locator('#heat-toggle').click(); await page.waitForTimeout(800); await shot('exposure_heat_1200'); await page.locator('#heat-toggle').click(); }
    }
    check(errors.length === 0, 'console errors: ' + errors.join(' | ').slice(0, 300));
    console.log(errors.length ? `  errors: ${errors.length}` : '  ok (0 console errors)');
    await page.close();
  }
}
await browser.close(); server.close();
console.log(failures ? `${failures} FAILED` : 'ALL OK');
process.exit(failures ? 1 : 0);
