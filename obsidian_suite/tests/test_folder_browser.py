"""Ingress folder browsing must not escape the /share root."""
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Import onboarding without installing optional add-on dependencies.
for module_name, symbol in [("settings_import","import_settings_json"),("couchdb_check","check_couchdb"),("tunnel_key","store_runtime_key")]:
    module = types.ModuleType(module_name)
    setattr(module, symbol, lambda *args, **kwargs: None)
    setattr(module, {"settings_import":"SettingsImportError","couchdb_check":"CouchCheckError","tunnel_key":"TunnelKeyError"}[module_name], type("FakeError",(Exception,),{}))
    sys.modules[module_name] = module
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location("ingress_test",Path(__file__).resolve().parents[1]/"onboarding.py")
app=importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class BrowseTests(unittest.TestCase):
    def test_folder_navigation_and_escape_prevention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"share"
            root.mkdir()
            (root/"notes"/"projects").mkdir(parents=True)
            outside=Path(tmp)/"private"
            outside.mkdir()
            (root/"alias").symlink_to(outside, target_is_directory=True)
            path,children=app.shared_folders(root)
            self.assertEqual(path,str(root.resolve()))
            self.assertEqual(children,[str(root/"notes")])
            path,children=app.shared_folders(root,str(root/"notes"))
            self.assertEqual(children,[str(root/"notes"/"projects")])
            for bad in (str(outside),str(root/"alias"),str(root/"alias"/"nested"),"relative/path"):
                with self.subTest(path=bad),self.assertRaises((ValueError,FileNotFoundError)):
                    app.shared_folders(root,bad)

if __name__=="__main__":
    unittest.main()
