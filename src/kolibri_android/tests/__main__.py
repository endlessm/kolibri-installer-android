import unittest
from pathlib import Path


def main():
    this_dir = Path(__file__).parent

    selftest_loader = unittest.TestLoader()
    selftests = selftest_loader.discover(this_dir)

    selftest_runner = unittest.runner.TextTestRunner()
    selftest_runner.run(selftests)

    selftest_suite = unittest.TestSuite()


if __name__ == "__main__":
    main()
