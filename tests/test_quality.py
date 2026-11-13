import sqlite3,unittest,tempfile
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
def load_script(name):
    spec=spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=module_from_spec(spec);spec.loader.exec_module(module)
    return module
class CatalogueQuality(unittest.TestCase):
    def test_integrity_audit(self):
        audit=load_script('audit_catalogue').inspect(ROOT/'data/ukiyora_characters.sqlite')
        self.assertGreaterEqual(audit['characters'],2002)
        self.assertEqual(audit['orphan_forms'],0)
        self.assertEqual(audit['broken_search_entries'],0)
        self.assertEqual(audit['invalid_approved_portraits'],0)
        self.assertEqual(audit['verified_feats'],0)
        self.assertGreater(len(audit['duplicate_name_examples_not_automatically_merged']),0)
    def test_portrait_manifest_rejects_unsafe_urls(self):
        image=load_script('import_portrait_manifest')
        self.assertFalse(image.public_https('http://example.com/image.jpg'))
        self.assertFalse(image.public_https('https://127.0.0.1/image.jpg'))
        self.assertFalse(image.public_https('https://localhost/a.png'))
        self.assertFalse(image.public_https('https://username:pwd@example.com/a.png'))
        self.assertTrue(image.public_https('https://images.example.org/image.png'))
    def test_duplicate_forms_are_audited(self):
        audit=load_script('audit_catalogue').inspect(ROOT/'data/ukiyora_characters.sqlite')
        self.assertIsInstance(audit['duplicate_form_candidates'],list)
if __name__=='__main__':unittest.main()

class SafeRebuild(unittest.TestCase):
    def test_rebuild_never_overwrites_without_force(self):
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from build_database import build
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'db.sqlite'
            build(dest)
            with sqlite3.connect(dest) as db:
                db.execute("INSERT INTO source_attributions(id,name) VALUES('editor-notes','important')")
            with self.assertRaises(FileExistsError):
                build(dest)
            with sqlite3.connect(dest) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM source_attributions WHERE id='editor-notes'").fetchone()[0],1)
