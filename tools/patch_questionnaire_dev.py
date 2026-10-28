"""Apply focus-safe text persistence to the isolated DEV questionnaire only."""
import pathlib,re
p=pathlib.Path(__file__).resolve().parents[1]/'dev/moad-airmes-20261028/target/autodiagnostic-questionnaire-v5-dev.html'
s=p.read_text()
if 'const drafts=new Map()' in s:raise SystemExit('Patch déjà appliqué')
start=s.index('async function saveField(');end=s.index('\nfunction explanation',start)
s=s[:start]+r'''
const drafts=new Map(),timers=new Map();let saveQueue=Promise.resolve();
const draftKey=(id,col)=>id+':'+col;
function restoreDrafts(){document.querySelectorAll('[data-text]').forEach(t=>{const d=drafts.get(draftKey(state.current?.id,t.dataset.text));if(d&&t.value!==d.value)t.value=d.value});let status=document.getElementById('text-save-status');if(!status){status=document.createElement('div');status.id='text-save-status';status.setAttribute('role','status');status.style.cssText='padding:8px;color:#9a3412;font:12px system-ui';app.prepend(status)}const failed=[...drafts.values()].filter(d=>d.error);status.textContent=failed.length?'Enregistrement impossible. Votre texte reste dans cette page ; cliquez sur Réessayer.':drafts.size?'Modifications en attente d’enregistrement.':'';if(failed.length){const b=document.createElement('button');b.textContent='Réessayer';b.onclick=()=>failed.forEach(d=>saveField(d.col,d.value,{quiet:true,rowId:d.id}));status.append(' ',b)}}
function saveField(col,value,opts={}){const id=opts.rowId||state.current?.id;if(!id)return Promise.resolve();const key=draftKey(id,col);if(!drafts.has(key))drafts.set(key,{id,col,value,error:false});state.dirty.add(key);const task=()=>persistField(id,col,value,opts);saveQueue=saveQueue.catch(()=>{}).then(task);return saveQueue}
async function persistField(id,col,value,opts){const key=draftKey(id,col),before={...(state.rows.find(r=>+r.id===+id)||{})};try{if(JSON.stringify(before[col])!==JSON.stringify(value)){await grist.docApi.applyUserActions([['UpdateRecord','Autodiagnostic_DEV',id,{[col]:value}]]);const row=state.rows.find(r=>+r.id===+id);if(row)row[col]=value;if(+state.current?.id===+id)state.current[col]=value;await logChange(before,{...before,[col]:value},col,before[col],value)}if(drafts.get(key)?.value===value)drafts.delete(key);if(!drafts.has(key))state.dirty.delete(key);state.lastSync=new Date();if(!opts.quiet)render();else restoreDrafts()}catch(e){const d=drafts.get(key);if(d)d.error=true;state.saving[col]='Erreur : '+e.message;restoreDrafts();console.error(e)}}
'''+s[end:]
start=s.index('function bind(){');end=s.index('\nasync function pull()',start)
s=s[:start]+r'''
function bind(){document.getElementById('site')?.addEventListener('change',e=>{state.current=state.rows.find(r=>+r.id===+e.target.value);state.section=0;render()});document.querySelectorAll('[data-sec]').forEach(b=>b.onclick=()=>{state.section=+b.dataset.sec;render()});document.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>saveField(b.dataset.choice,b.dataset.value));document.querySelectorAll('[data-multi]').forEach(b=>b.onclick=()=>{const col=b.dataset.multi,val=b.dataset.value,cur=listVals(state.current?.[col]);saveField(col,['L',...(cur.includes(val)?cur.filter(x=>x!==val):[...cur,val])])});document.querySelectorAll('[data-prio]').forEach(b=>b.onchange=()=>saveField(b.dataset.prio,b.value));document.querySelectorAll('[data-text]').forEach(t=>{const id=state.current.id,col=t.dataset.text,key=draftKey(id,col);t.oninput=()=>{drafts.set(key,{id,col,value:t.value,error:false});state.dirty.add(key);clearTimeout(timers.get(key));timers.set(key,setTimeout(()=>saveField(col,drafts.get(key)?.value??t.value,{quiet:true,rowId:id}),60000))};t.onblur=()=>{clearTimeout(timers.get(key));const d=drafts.get(key);if(d)saveField(col,d.value,{quiet:true,rowId:id})}});restoreDrafts()}
'''+s[end:]
s=s.replace("if(!state.current||state.dirty.size)return;", "if(!state.current||state.dirty.size||document.activeElement?.matches('textarea,[data-prio]'))return;")
# Display migration conflicts without exposing source answers to editors.
s=s.replace('const sections=visibleSections();',"const sections=visibleSections();")
s=s.replace('<div class="status">','<div class="status">${row.CONFLITS_MIGRATION?`<span class="pill">${row.CONFLITS_MIGRATION} champs en attente d’arbitrage de migration</span>`:\'\'}',1)
s=s.replace('if(fresh){state.rows=latest', "if(state.dirty.size||document.activeElement?.matches('textarea,[data-prio]'))return;if(fresh){state.rows=latest")
p.write_text(s)
