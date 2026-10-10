import json, os, tempfile, unittest
import _path  # noqa
from pixel_td.save import SaveStore


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.st = SaveStore(self.tmp)

    def test_empty(self):
        self.assertEqual(self.st.load(), {})

    def test_roundtrip_with_big_ints(self):
        data = {"meta": {"ap": 5}, "run": {"gold": 10 ** 500, "wave": 3}}
        self.assertTrue(self.st.write(data))
        back = self.st.load()
        self.assertEqual(back["run"]["gold"], 10 ** 500)
        self.assertEqual(back["version"], 1)

    def test_backup_fallback_on_corruption(self):
        self.st.write({"meta": {"ap": 1}})
        self.st.write({"meta": {"ap": 2}})                # first write is now .bak
        with open(self.st.path, "w") as f:
            f.write("{ not json")
        self.assertEqual(self.st.load()["meta"]["ap"], 1)

    def test_wipe(self):
        self.st.write({"a": 1})
        self.st.wipe()
        self.assertEqual(self.st.load(), {})

    def test_env_override(self):
        os.environ["PIXEL_TD_HOME"] = self.tmp
        try:
            self.assertEqual(SaveStore().dir, self.tmp)
        finally:
            del os.environ["PIXEL_TD_HOME"]


if __name__ == "__main__":
    unittest.main()
