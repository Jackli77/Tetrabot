"""Run every Tetrabot test module.  Usage: python tests\\run_all.py"""
import os
import sys

# Make the project root importable regardless of the current directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import test_db_updates, test_models, test_transport, test_views


def main():
    test_models.run()
    test_views.run()
    test_transport.run()
    test_db_updates.run()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
