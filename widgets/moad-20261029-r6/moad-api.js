(function(root){'use strict';
const tables={SITES:'GristHidden_SITES',UGECAM:'GristHidden_UGECAM',PROFIL_SESSION:'GristHidden_PROFIL_SESSION',Autodiagnostic_DEV:'Autodiagnostic',Autodiagnostic_Historique_DEV:'Autodiagnostic_Historique',ARBORESCENCE_AIRMES_DEV:'ARBORESCENCE_AIRMES'};
const table=t=>tables[t]||t;
root.moadApi={fetchTable:t=>grist.docApi.fetchTable(table(t)),applyUserActions:(aa,options)=>grist.docApi.applyUserActions(aa.map(a=>{const copy=[...a];if(typeof copy[1]==='string')copy[1]=table(copy[1]);return copy}),options),listTables:async()=>{const actual=await grist.docApi.listTables();return [...new Set([...actual,...Object.keys(tables).filter(k=>actual.includes(tables[k]))])]},getAccessToken:o=>grist.docApi.getAccessToken(o)};
})(globalThis);
