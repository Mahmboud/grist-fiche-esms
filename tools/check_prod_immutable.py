"""Fail if any frozen production widget/dependency has changed."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((root/'tools/prod-immutable.json').read_text())
if len(sys.argv)>1:
    prior=subprocess.run(['git','show',sys.argv[1]+':tools/prod-immutable.json'],cwd=root,capture_output=True,text=True)
    if prior.returncode==0:
        old=json.loads(prior.stdout)
        assert all(manifest.get(k)==v for k,v in old.items()),'Frozen manifest entries cannot be changed or removed'
errors=[name for name,sha in manifest.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha]
if errors:raise SystemExit('PROD immutable: '+', '.join(errors))
print(f'{len(manifest)} production widgets/dependencies unchanged')
