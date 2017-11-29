#!/usr/bin/env python3
"""Central runner for framework."""
from .images import BaseImage, TestImage
from .utils import find_pristine_image, find_tests, setup_results_dir


def collect(release, image, tests, results_dir):
    """Boot and collect data from images with configs.

    @param release: optional, release to test, defautls to latest
    @param image: optional, path to image to use for testing
    @param tests: optional, specify specific tests to run
    @param results_dir: optional, path to store results
    """
    results_dir = setup_results_dir(results_dir)
    base_image_path = find_pristine_image(release, image)
    base_image = BaseImage(base_image_path, results_dir)

    tests = find_tests(tests)
    for test_yaml_path in tests:
        test_image = TestImage(base_image, test_yaml_path)
        test_image.launch()
        test_image.collect()


def run(release, image, tests, results_dir):
    """Wrap around collect and verifing.

    @param release: optional, release to test, defautls to latest
    @param image: optional, path to image to use for testing
    @param tests: optional, specify specific tests to run
    @param results_dir: optional, path to store results
    """
    collect(release, image, tests, results_dir)
    verify(results_dir)


def verify(results_dir):
    """Verify results.

    @param results_dir: optional, path to store results
    """
    print('verifing: %s' % (results_dir))
