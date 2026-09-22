#!/usr/bin/env node
// Native HA frontend acceptance against the disposable lab only.
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
let chromium;
try { ({chromium}=require('playwright-core')); }
catch { ({chromium}=createRequire(path.resolve(path.dirname(process.execPath),'../node_modules/playwright/package.json'))('playwright')); }
const [url,stateFile,outputDir] = process.argv.slice(2);
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(url)) throw Error('Disposable loopback lab required');
const {token,entry_id}=JSON.parse(await fs.readFile(stateFile,'utf8'));
const browser=await chromium.launch({headless:true});
const errors=[];
try {
 const context=await browser.newContext({colorScheme:'dark'});
 await context.addInitScript(({url,token})=>{
  window.__rejections=[];window.addEventListener('unhandledrejection',event=>window.__rejections.push(JSON.stringify(event.reason)));
  localStorage.setItem('hassTokens',JSON.stringify({hassUrl:url,access_token:token,token_type:'Bearer',expires_in:86400,expires:Date.now()+86400000,clientId:url+'/'}));
 },{url,token});
 const page=await context.newPage();
 const wsFailures=[];
 page.on('websocket',socket=>{
  const requests=new Map();
  socket.on('framesent',frame=>{try{const m=JSON.parse(frame.payload);if(m.id)requests.set(m.id,m.type);}catch{}});
  socket.on('framereceived',frame=>{try{const m=JSON.parse(frame.payload);if(m.success===false)wsFailures.push({type:requests.get(m.id),error:m.error});}catch{}});
 });
 page.on('pageerror',e=>errors.push({message:e.message,stack:e.stack}));
 await fs.mkdir(outputDir,{recursive:true});
 await page.goto(url+'/robbie-lab/cleaning');
 await page.waitForTimeout(4000);
 await page.screenshot({path:path.join(outputDir,'initial.png')});
 console.log('Native browser initial:', new URL(page.url()).pathname, (await page.locator('body').innerText()).slice(0,900));
 const card=page.locator('robbie-advanced-cleaning-card');
 await card.waitFor({timeout:60000});
 await page.locator('#ha-launch-screen').waitFor({state:'hidden'});
 await fs.mkdir(outputDir,{recursive:true});
 const api=async(route,data)=>{
  const response=await fetch(url+route,{method:data?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},...(data?{body:JSON.stringify(data)}:{})});
  if(!response.ok)throw Error(route+': '+response.status);
  return response.json();
 };
 const service=(domain,name,data)=>api('/api/services/'+domain+'/'+name,data);
 const states=await api('/api/states');
 const status=states.find(x=>x.attributes?.entry_id===entry_id&&x.entity_id.endsWith('_planner_status'));
 const mission=status.attributes.missions[0];
 await page.screenshot({path:path.join(outputDir,'idle.png')});
 // The real installation uses 06:00 weekly vacuum/mop runs with presence wait.
 // The lab keeps test identities and native fixture commands for these guards.
 await service('input_number','set_value',{entity_id:'input_number.home_occupants',value:2});
 // The HTTP restart phase will still verify the pre-existing persisted skip.
 // Exercise UI states before that phase, then re-arm the same future skip.
 await service('robbie_advanced_cc','run_next',{entry_id,mission_id:mission.id});
 await service('robbie_advanced_cc','run_next',{entry_id,mission_id:mission.id});
 for(const [language,width] of [['de',390],['en',1280]]){
  await page.setViewportSize({width,height:844});
  await page.evaluate(language=>document.querySelector('home-assistant').hass.callWS({type:'frontend/set_user_data',key:'language',value:{language}}),language);
  await page.reload();await card.waitFor();await page.locator('#ha-launch-screen').waitFor({state:'hidden'});
  await page.screenshot({path:path.join(outputDir,`${language}-waiting.png`)});
  await card.locator('[data-mode-toggle]').click();
  await card.locator('[data-close-dialog]').waitFor();
  await page.screenshot({path:path.join(outputDir,`${language}-menu.png`)});
  await card.locator('[data-close-dialog]').click();
 }
 await card.locator('[data-action="skip"]').click();
 await page.waitForFunction(id=>document.querySelector('home-assistant').hass.states[id].state==='skipped',status.entity_id);
 await page.screenshot({path:path.join(outputDir,'en-skipped.png')});
 await service('robbie_advanced_cc','run_next',{entry_id,mission_id:mission.id,manual:true});
 await page.waitForFunction(id=>document.querySelector('home-assistant').hass.states[id].state==='running',status.entity_id);
 await page.screenshot({path:path.join(outputDir,'en-running.png')});
 await card.locator('[data-action="skip"]').click();
 await page.waitForFunction(()=>document.querySelector('home-assistant').hass.states['vacuum.valetudo_fixture_robot'].state==='returning');
 await page.screenshot({path:path.join(outputDir,'en-returning.png')});
 await service('robbie_advanced_cc_test_fixture','set_state',{entity_id:'vacuum.valetudo_fixture_robot',state:'docked'});
 await page.waitForFunction(id=>document.querySelector('home-assistant').hass.states[id].state==='skipped',status.entity_id);
 const final=await api('/api/states/'+status.entity_id);assert.equal(final.attributes.active_mission_id,null);
 await service('robbie_advanced_cc','postpone_next',{entry_id,minutes:37});
 await service('robbie_advanced_cc','skip_next',{entry_id});
 console.log('Browser diagnostics:',JSON.stringify({errors,wsFailures,rejections:await page.evaluate(()=>window.__rejections)}));
 assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(outputDir,'result.json'),JSON.stringify({native_frontend:true,ha_version:await page.evaluate(()=>document.querySelector('home-assistant').hass.config.version),viewports:[390,1280],states:['waiting','skipped','running','returning'],page_errors:errors,simulated_hardware:true,passed:true},null,2));
 console.log('Native HA browser acceptance passed');
} finally {await browser.close();}
