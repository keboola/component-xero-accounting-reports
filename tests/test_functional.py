import unittest
from pathlib import Path

from datadirtest.vcr import VCRDataDirTester


class TestComponent(unittest.TestCase):
    def test_functional(self):
        functional_tests = VCRDataDirTester(
            data_dir=str(Path(__file__).parent / "functional"),
            component_script=str(Path(__file__).parent.parent / "src" / "component.py"),
        )
        functional_tests.run()


if __name__ == "__main__":
    unittest.main()
