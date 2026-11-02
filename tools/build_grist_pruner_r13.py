"""Bundle Grist's unchanged outgoing-row filtering methods for a regression test.

Usage: python build_grist_pruner_r13.py GRIST_RUNTIME OUTPUT_DIR NODE_MODULES
Runtime is pinned to 2afde758fefeff32579639be58c2855804e85859.
Deps: esbuild, lodash, grainjs. Only logging is stubbed; ACL evaluation is native.
"""
import pathlib,re,sys,subprocess
runtime=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();deps=pathlib.Path(sys.argv[3]).resolve();out.mkdir(exist_ok=True,parents=True)
assert subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip()=='2afde758fefeff32579639be58c2855804e85859'
s=(runtime/'app/server/lib/GranularAccess.ts').read_text();methods=[]
for name in ['_pruneRows','_filterRowsAndCells','_getForbiddenRows','_removeRowsAt','_removeRows','_makeAdditions','_makeRemovals','_makeColumnUpdate']:
 m=re.search(r'^  private (?:async )?'+name+r'\(',s,re.M);assert m,name
 end=re.search(r'^  \}$',s[m.start():],re.M);assert end
 methods.append(s[m.start():m.start()+end.end()])
entry='''import { PermissionInfo } from 'app/server/lib/PermissionInfo';
import { RecordView, EmptyRecordView } from 'app/common/RecordView';
import { compilePredicateFormula } from 'app/common/PredicateFormula';
import { parsePermissions } from 'app/common/ACLPermissions';
import { isDataAction,isSomeAddRecordAction,isSomeRemoveRecordAction,isSchemaAction,getTableId,getRowIdsFromDocAction,getActionColValues,getRowIds } from 'app/common/DocActions';
import { isNonNullish,pruneArray } from 'app/common/gutil';
import { GristObjCode } from 'app/plugin/GristData';
import cloneDeep from 'lodash/cloneDeep';
export {PermissionInfo,RecordView,EmptyRecordView,compilePredicateFormula,parsePermissions};
export class NativePruner {
'''+ '\n'.join(methods)+'\n}\n'
(out/'pruner-entry.ts').write_text(entry)
(out/'build-pruner.cjs').write_text('''const path=require('path');const [runtime,out,deps]=process.argv.slice(2);require(path.join(deps,'esbuild')).build({entryPoints:[path.join(out,'pruner-entry.ts')],outfile:path.join(out,'native-pruner.cjs'),bundle:true,platform:'node',format:'cjs',tsconfigRaw:{compilerOptions:{baseUrl:runtime,paths:{'app/*':['app/*']}}},nodePaths:[deps],logOverride:{'direct-eval':'silent'},plugins:[{name:'test-logger',setup(b){b.onResolve({filter:/^app\\/server\\/lib\\/log$/},()=>({path:'log',namespace:'test-log'}));b.onLoad({filter:/.*/,namespace:'test-log'},()=>({contents:'export default {warn(){},error(){},info(){},debug(){}};'}))}}]}).catch(e=>{console.error(e);process.exitCode=1});''')
subprocess.run(['node',str(out/'build-pruner.cjs'),str(runtime),str(out),str(deps)],check=True)
print(out/'native-pruner.cjs')
