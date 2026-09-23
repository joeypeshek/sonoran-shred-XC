const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path'),root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const seed=JSON.parse(html.match(/<script id="seed" type="application\/json">(.*?)<\/script>/s)[1]),nodes={};
function node(id){return nodes[id]??={value:'',textContent:id==='seed'?JSON.stringify(seed):'',innerHTML:'',style:{setProperty(){}},dataset:{},hidden:false,removeAttribute(){},showModal(){this.open=true;},close(){this.open=false;},click(){return this.onclick?.();}};}
const context={console,structuredClone,JSON,Date,Set,Number,String,Error,URL,Blob,crypto:require('crypto').webcrypto,
  location:{protocol:'file:',hash:'',href:'file:///index.html'},
  window:{addEventListener(){}},
  document:{getElementById:node,querySelectorAll:()=>[],documentElement:{style:{setProperty(){}}},addEventListener(){},hidden:false},
  setTimeout:()=>1,setInterval:()=>1,clearTimeout(){},confirm:()=>true};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),context);
const run=code=>vm.runInContext(code,context);
(async()=>{
  assert.equal(run('officer'),false);assert.equal(run('editing'),false);
  nodes.editToggle.onclick();assert.equal(nodes.loginDialog.open,true);
  assert.equal(run('validate(data).members.length'),17);
  assert.equal((nodes.roster.innerHTML.match(/<tr>/g)||[]).length,17);
  run("save()");assert.equal(run('dirty'),false);
  run("officer=true;editing=true;sharedVersion=0;data.members[0].volunteer='complete';data.members[0].note='Keep';save()");
  assert.equal(run('dirty'),true);
  run("applyRegistrations({eventId:'76688',syncedAt:new Date().toISOString(),entries:[{name:'New Arrival',team:'UA Cycling',category:'Cat 1',date:''}],review:[]})");
  assert.equal(run("data.members.find(m=>m.id==='avery paris').volunteer"),'complete');
  assert.equal(run("data.members.find(m=>m.id==='avery paris').note"),'Keep');
  assert.equal(run('dirty'),true);
  run("client={rpc:async(name,args)=>({data:{state:args.p_state,version:1},error:null})}");
  await run('saveOnline()');assert.equal(run('dirty'),false);assert.equal(run('sharedVersion'),1);
  run("data.design.heading='Draft';save();client={rpc:async()=>({error:{code:'40001',message:'Conflict'}})}");
  await run('saveOnline()');assert.equal(run('dirty'),true);assert.equal(run('conflict'),true);assert.equal(run('data.design.heading'),'Draft');
  assert.equal(nodes.saveOnline.disabled,true);
  run("officer=false;dirty=false;let called=false;client={rpc:async()=>{called=true}};");
  await run('saveOnline()');assert.equal(run('called'),false);
  console.log('PASS: read-only visitor, sign-in UI, roster, local draft, feed preservation, shared save, conflict retention, unauthorized save guard.');
})().catch(e=>{console.error(e);process.exitCode=1;});
