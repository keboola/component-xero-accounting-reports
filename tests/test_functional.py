from pathlib import Path

import pytest
from datadirtest.vcr import get_test_cases, VCRTestDataDir

FUNCTIONAL_DIR = str(Path(__file__).parent / "functional")
COMPONENT_SCRIPT = str(Path(__file__).parent.parent / "src" / "component.py")


@pytest.mark.parametrize("test_name", get_test_cases(FUNCTIONAL_DIR))
def test_functional(test_name):
    test = VCRTestDataDir(
        data_dir=str(FUNCTIONAL_DIR / test_name),
        component_script=COMPONENT_SCRIPT,
        vcr_mode="replay",
    )
    test.setUp()
    try:
        test.compare_source_and_expected()
    finally:
        test.tearDown()
