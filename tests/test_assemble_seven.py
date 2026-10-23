import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.assemble_seven import LANGUAGES, assemble

def msg(lang, ident="260925m", date="2026-09-25"):
    text=lang+" translation text"
    return {"id":ident,"date":date,"type":"monthly","language":lang,"visionary":"marija",
            "source_url":"https://www.medjugorje.ws/"+lang+"/messages/"+ident+"/",
            "title":"Message","text":text,"source_id":ident,"status":"contains_message",
            "text_sha256":hashlib.sha256(text.encode()).hexdigest()}
def write(path,val):
    path.write_text(json.dumps(val),encoding="utf-8")

class SevenLanguageTests(unittest.TestCase):
    def prepare(self,folder):
        base=msg("ru")
        index={"verified":False,"unique_records":1,"messages":[{
            "id":base["id"],"date":base["date"],"type":"monthly","visionary":"marija",
            "translations":{}}]}
        for lang in LANGUAGES:
            m=msg(lang)
            write(folder/(lang+".json"),{"language":lang,"verified":False,"messages":[m]})
            if lang in ("ru","be","uk"):
                index["messages"][0]["translations"][lang]={
                    "present":True,"has_text":True,"source_url":m["source_url"],
                    "text_sha256":m["text_sha256"]}
        write(folder/"index.json",index)
        return index

    def test_original_metadata_is_unchanged(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            old=self.prepare(folder)
            original=copy.deepcopy(old["messages"][0]["translations"])
            result=assemble(folder,folder/"candidate")
            self.assertEqual(result["union_unique_records"],1)
            self.assertEqual(result["all_seven_with_text"],1)
            updated=json.loads((folder/"candidate/index.json").read_text())
            for lang in ("ru","be","uk"):
                self.assertEqual(updated["messages"][0]["translations"][lang],original[lang])
            self.assertTrue(updated["messages"][0]["translations"]["lv"]["has_text"])

    def test_rejects_mutated_legacy_text(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);self.prepare(folder)
            source=json.loads((folder/"ru.json").read_text())
            source["messages"][0]["text"]="changed"
            write(folder/"ru.json",source)
            with self.assertRaisesRegex(ValueError,"SHA"):
                assemble(folder,folder/"candidate")

    def test_rejects_wrong_new_date(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);self.prepare(folder)
            source=json.loads((folder/"lv.json").read_text())
            source["messages"][0]["date"]="2026-08-25"
            write(folder/"lv.json",source)
            with self.assertRaisesRegex(ValueError,"Date/type mismatch"):
                assemble(folder,folder/"candidate")

if __name__ == "__main__":
    unittest.main()
