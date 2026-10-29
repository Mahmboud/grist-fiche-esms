// Uses Grist's actual TypeScript compiler, RecordView and permission parser.
const fs=require('fs'),assert=require('assert');const f=JSON.parse(fs.readFileSync(process.argv[2]));const G=require(process.argv[3]);const checks=[];
function record(r){return new G.RecordView(['TableData','Test',[r.id||1],Object.fromEntries(Object.entries(r).filter(([k])=>k!=='id').map(([k,v])=>[k,[Array.isArray(v)&&v[0]!=='L'?['L',...v]:v]]))],0)}
function user(opts={}){return {Access:opts.role||'editors',IsLoggedIn:opts.logged!==false,Email:'demande-test@example.invalid',droits_supp:record({id:1,ACCES:true,ACCES_LISTE_ESMS:true,ACCES_ARBORESCENCE:true,SIEGE:false,DNGU:false,UGECAM:1,SITE_PRINCIPAL:4,SITES_RESP_AIRMES:[],AUTODIAGS_AUTORISES:[1],...opts.rights}),demande_acces:record({STATUT:opts.valid===false?'À valider':'Validé'})}}
function perms(acl,table,u,r,n=r,column='*'){
 const ids=acl.resources.filter(x=>x.tableId===table&&x.colIds===column).map(x=>x.id);assert(ids.length,'Ressource manquante '+table+':'+column);const rules=acl.rules.filter(x=>ids.includes(x.resource)).sort((a,b)=>a.rulePos-b.rulePos),out={};
 for(const rule of rules){const matches=!rule.aclFormula||G.compilePredicateFormula(typeof rule.aclFormulaParsed==='string'?JSON.parse(rule.aclFormulaParsed):rule.aclFormulaParsed)({user:u,rec:record(r),newRec:record(n)});if(matches)for(const [k,v] of Object.entries(G.parsePermissions(rule.permissionsText)))if(v&&!out[k])out[k]=v}
 return out;
}
const mine=f.tables.CONTACTS.find(r=>r.id===1),other=f.tables.CONTACTS.find(r=>r.id!==1),pending=user({valid:false});
assert.equal(perms(f.acl,'CONTACTS',pending,mine).read,'allow');assert.equal(perms(f.acl,'CONTACTS',pending,mine,mine,'MON_PROFIL_JSON').read,'allow');checks.push('Contact existant sans demande validée : lecture de sa propre fiche et de son préremplissage');
for(const annuaire of [false,true]){const u=user({rights:{ACCES_CONTACTS:annuaire}});assert.equal(perms(f.acl,'CONTACTS',u,other,other,'MON_PROFIL_JSON').read,'deny');assert.equal(perms(f.acl,'CONTACTS',u,mine,mine,'MON_PROFIL_JSON').read,'allow')}checks.push('Accès annuaire activé ou non : le champ personnel d’autrui reste censuré');
assert.equal(perms(f.acl,'CONTACTS',user({logged:false}),mine,mine,'MON_PROFIL_JSON').read,'deny');assert.equal(perms(f.acl,'CONTACTS',pending,mine,mine,'MON_PROFIL_JSON').update,'deny');assert.equal(perms(f.acl,'CONTACTS',pending,mine).update,'deny');checks.push('Aucune ouverture aux anonymes ni droit de modifier ses habilitations');
assert.equal(perms(f.acl,'CONTACTS',user({role:'owners'}),other,other,'MON_PROFIL_JSON').read,'allow');checks.push('Propriétaire : accès conservé aux fiches et aux formules');
for(const t of ['GristHidden_SITES','GristHidden_UGECAM','GristHidden_PROFIL_SESSION'])assert.equal(perms(f.acl,t,pending,{}).read,'deny');checks.push('Trois tables techniques toujours réellement masquées aux éditeurs');
console.log(JSON.stringify({passed:checks.length,checks},null,2));
