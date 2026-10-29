import pathlib
root=pathlib.Path(__file__).resolve().parents[1];src=root/'widgets/moad-20261029-r7';out=root/'widgets/moad-20261029-r8';out.mkdir(exist_ok=True)
for name in ['mon-acces.html','moad-api.js','moad-ref-config.js']:
 s=(src/name).read_text()
 if name=='mon-acces.html':
  s=s.replace("const c=S.contacts.find(c=>+c.id===+S.profile?.CONTACT);","const c=S.self;")
  old="const profiles=await ft('PROFIL_SESSION');S.profile=!S.owner&&profiles.length===1?profiles[0]:null;S.email=S.profile?.EMAIL||'';const cfg=await loadMoadRefConfig();S.f=cfg.fonctions;[S.u,S.s,S.requests,S.contacts]=await Promise.all([ft('UGECAM'),ft('SITES'),ft('DEMANDES_ACCES'),ft('CONTACTS')]);show()"
  new="const cfg=await loadMoadRefConfig();S.f=cfg.fonctions;[S.u,S.s,S.requests,S.contacts]=await Promise.all([ft('UGECAM'),ft('SITES'),ft('DEMANDES_ACCES'),ft('CONTACTS')]);const personal=S.contacts.flatMap(r=>{if(typeof r.MON_PROFIL_JSON!=='string'||!r.MON_PROFIL_JSON)return [];try{const c=JSON.parse(r.MON_PROFIL_JSON);return c&&+c.id===+r.id?[c]:[]}catch{return []}});S.self=!S.owner&&personal.length===1?personal[0]:null;S.email=S.self?.EMAIL||'';show()"
  assert old in s;s=s.replace(old,new)
  s=s.replace("if(S.email)payload.EMAIL=S.email;","")
 (out/name).write_text(s)
print(out)
