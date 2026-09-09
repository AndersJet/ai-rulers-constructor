"""Version identity and compatibility at public generation/package boundaries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/ai-rulers-init'
sys.path.insert(0, str(SKILL / 'scripts'))


class VersionContractTest(unittest.TestCase):
    def run_cli(self, skill, *args):
        result = subprocess.run([sys.executable, str(skill / 'scripts/rulers_init.py'), *map(str,args)],
            capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(0,result.returncode,result.stderr or result.stdout)
        return result.stdout

    def test_legacy_entry_formats_merge_into_unversioned_block(self):
        from rulers_lib.root_entry import merge_managed_block, has_valid_managed_block
        for version in (2,3):
            original=f'before\n<!-- ai-rulers-init:begin version={version} -->\nold\n<!-- ai-rulers-init:end -->\nafter\n'
            result=merge_managed_block(original,'documents/rulers')
            self.assertIn('<!-- ai-rulers-init:begin -->',result)
            self.assertNotIn('version=',result)
            self.assertTrue(result.startswith('before\n') and result.endswith('after\n'))
            self.assertTrue(has_valid_managed_block(result))
            self.assertEqual(result,merge_managed_block(result,'documents/rulers'))

    def test_legacy_installation_upgrades_without_duplicate_version(self):
        with tempfile.TemporaryDirectory(prefix='version-upgrade-') as td:
            target=Path(td).resolve()
            (target/'AGENTS.md').write_text('# Preserve human instructions\n')
            self.run_cli(SKILL,'plan','--project-root',target,'--output',target/'old-plan.json')
            self.run_cli(SKILL,'apply','--plan',target/'old-plan.json')
            self.run_cli(SKILL,'review-profile','--project-root',target,'--reviewed-by','test-owner','--evidence','synthetic-test')
            self.run_cli(SKILL,'mark-runtime-ready','--project-root',target)
            # Reproduce the stored schema-3 shape shipped before version consolidation.
            state_path=target/'documents/rulers/RULERS_STATE.json'
            legacy=json.loads(state_path.read_text())
            legacy['template_version']=legacy['template']['version']
            legacy['template']['fingerprint']='sha256:'+'0'*64
            state_path.write_text(json.dumps(legacy))
            entry=target/'AGENTS.md'
            entry.write_text(entry.read_text().replace('<!-- ai-rulers-init:begin -->','<!-- ai-rulers-init:begin version=3 -->'))
            self.run_cli(SKILL,'plan','--project-root',target,'--operation','upgrade','--output',target/'upgrade.json')
            self.run_cli(SKILL,'apply','--plan',target/'upgrade.json','--reviewed-by','test-owner','--evidence','synthetic-test')
            state=json.loads(state_path.read_text())
            self.assertNotIn('template_version',state)
            self.assertIn('<!-- ai-rulers-init:begin -->',entry.read_text())
            self.assertIn('Preserve human instructions',entry.read_text())
            self.assertEqual('reviewed',state['profile']['status'])
            reported=self.run_cli(SKILL,'--version').strip().split()[-1]
            self.assertEqual(reported,state['template']['version'])
            self.assertIn('Version: '+reported,(target/'documents/rulers/AGENTS.md').read_text())

    def test_package_rejects_manually_versioned_template_header(self):
        with tempfile.TemporaryDirectory(prefix='version-package-') as td:
            copy=Path(td)/'ai-rulers-init';shutil.copytree(SKILL,copy,ignore=shutil.ignore_patterns('__pycache__'))
            p=copy/'templates/runtime/AGENTS.md.tmpl'
            text=p.read_text()
            import re
            p.write_text(re.sub(r'Version: [^。]+','Version: 0.0.0',text,count=1))
            result=subprocess.run([sys.executable,'-m','scripts.package_skill','--skill-root',str(copy),'--output',str(Path(td)/'bad.skill')],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode)
            self.assertIn('RELEASE_VERSION',result.stderr)
            self.assertFalse((Path(td)/'bad.skill').exists())

    def test_module_apply_rejects_unknown_protocol_before_other_inputs(self):
        with tempfile.TemporaryDirectory(prefix='module-protocol-') as td:
            for version in (True,2,None):
                path=Path(td)/'plan.json'
                path.write_text(json.dumps({'operation':'register','module_plan_version':version}))
                result=subprocess.run([sys.executable,str(SKILL/'scripts/rulers_init.py'),'module-apply','--plan',str(path)],capture_output=True,text=True)
                self.assertNotEqual(0,result.returncode)
                self.assertIn('Unsupported module_plan_version',result.stderr)

    def test_export_reader_rejects_unknown_protocol(self):
        from rulers_lib.module_exports import read_export_snapshot
        with tempfile.TemporaryDirectory(prefix='export-protocol-') as td:
            path=Path(td)/'snapshot.json'
            for version in (True,2,None):
                path.write_text(json.dumps({'export_version':version}))
                with self.assertRaisesRegex(ValueError,'Unsupported export_version'):
                    read_export_snapshot(path)
