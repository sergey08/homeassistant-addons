"""Test GUI-selected folder storage without making any Supervisor API changes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from folder_options import save_local_vault


class FolderOptionsTests(unittest.TestCase):
    def test_save_calls_only_own_options_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "share"
            target = root / "notes"
            target.mkdir(parents=True)
            class FakeResponse:
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self,*args): return b'{"result":"ok"}'
            with patch("folder_options.urlopen", return_value=FakeResponse()) as open_url:
                result=save_local_vault(str(target),token="test-token",root=root)
                self.assertEqual(result,str(target))
                request=open_url.call_args.args[0]
                self.assertEqual(request.full_url,"http://supervisor/addons/self/options")
                self.assertEqual(json.loads(request.data),{"options":{"storage_mode":"local","vault_path":str(target)}})
            with patch("folder_options.urlopen") as open_url:
                with self.assertRaises(ValueError):
                    save_local_vault(str(Path(folder)),token="test-token",root=root)
                open_url.assert_not_called()

if __name__ == "__main__":
    unittest.main()
