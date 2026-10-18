"""Detector tests driver: runs every part as one suite (``!`` + ``/``)."""
from tests import (
    test_detectors_part1,
    test_detectors_part2,
    test_detectors_part3,
    test_detectors_part4,
)


def run():
    test_detectors_part1.check_imports()
    test_detectors_part1.check_registry()
    test_detectors_part2.check_prefix_dispatch()
    test_detectors_part2.check_context_normalisation()
    test_detectors_part3.check_respond_factories()
    test_detectors_part3.check_slash_dispatch_and_context()
    test_detectors_part4.check_prefix_detector_steps()
    test_detectors_part4.check_prefix_detector_dispatch()
    test_detectors_part4.check_legacy_imports_are_gone()
    print("test_detectors: all passed")
