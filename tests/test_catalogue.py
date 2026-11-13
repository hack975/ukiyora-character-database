from pathlib import Path
import sqlite3,unittest
DB=Path(__file__).resolve().parents[1]/'data/ukiyora_characters.sqlite'
class CatalogueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB.exists(): raise AssertionError('Run python scripts/build_database.py')
        cls.db=sqlite3.connect(DB)
    @classmethod
    def tearDownClass(cls): cls.db.close()
    def test_record_counts(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM series').fetchone()[0],67)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM characters').fetchone()[0],2002)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM character_forms').fetchone()[0],1089)
    def test_search(self):
        self.assertGreater(self.db.execute('SELECT COUNT(*) FROM character_search_fts WHERE character_search_fts MATCH ?', ('"goku"*',)).fetchone()[0],0)
        self.assertGreater(self.db.execute('SELECT COUNT(*) FROM character_search_fts WHERE character_search_fts MATCH ?', ('"naruto"*',)).fetchone()[0],0)
    def test_forms_belong_to_characters(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM character_forms f LEFT JOIN characters c ON c.id=f.character_id WHERE c.id IS NULL').fetchone()[0],0)
    def test_no_false_verifications(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM characters WHERE profile_status='verified'").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM character_forms WHERE verification_status='verified'").fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feats_ledger').fetchone()[0],0)
    def test_no_fake_portraits(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM characters WHERE portrait_status='approved'").fetchone()[0],0)
if __name__=='__main__':unittest.main()
