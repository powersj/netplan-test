"""Various utility functions."""
from datetime import datetime
import glob
import logging
import os
import subprocess

import distro_info
from simplestreams import filters, mirrors, objectstores, util as s_util

LOG = logging.getLogger('netplan_test')


def find_pristine_image(release=None, image=None):
    """Determine what image to use as pristine and return.

    @param release: optional, release to test, defautls to latest
    @param image: optional, path to image to use for testing
    @return path to image to as pristine image
    """
    if not image:
        if not release:
            release = latest_ubuntu_release()
        image = latest_cloud_image(release)

    LOG.info('using image at %s', (image))
    return image


def find_tests(tests=None):
    """Determine what tests to run, return array of tests.

    @param tests: optional, list of test files to run
    @return list of test files to run
    """
    if not tests:
        tests = glob.glob('configs/*.yaml')

    LOG.info('running %s tests\n%s', len(tests), tests)
    return sorted(tests)


def latest_cloud_image(release):
    """Download cloud image of specified release using simplestreams.

    This expects to find only a single image for the release for the
    specific day.

    @param release: string of Ubuntu release image to find
    @return: path to unique image for specified release
    """
    LOG.info('finding pristine image for %s', (release))
    mirror_url = 'https://cloud-images.ubuntu.com/daily'
    mirror_dir = '/srv/netplan/'
    keyring = '/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg'
    (url, path) = s_util.path_from_mirror_url(mirror_url, None)

    ss_filter = filters.get_filters(['arch=%s' % system_architecture(),
                                     'release=%s' % release,
                                     'ftype=disk1.img'])
    mirror_config = {
        'filters': ss_filter,
        'keep_items': False,
        'max_items': 1,
        'checksumming_reader': True,
        'item_download': True
    }

    def policy(content, path=None):  # pylint: disable=unused-argument
        """Simplestreams policy function.

        @param content: signed content
        @param path: not used
        @return: policy for simplestreams
        """
        return s_util.read_signed(content, keyring=keyring)

    smirror = mirrors.UrlMirrorReader(url, policy=policy)
    tstore = objectstores.FileStore(mirror_dir)
    tmirror = mirrors.ObjectFilterMirror(config=mirror_config,
                                         objectstore=tstore)
    tmirror.sync(smirror, path)

    search_d = os.path.join(mirror_dir, '**', release, '**', '*.img')

    images = []
    for fname in glob.iglob(search_d, recursive=True):
        images.append(fname)

    if len(images) != 1:
        raise Exception('No unique images found')

    return images[0]


def latest_ubuntu_release():
    """Determine latest Ubuntu development release.

    When there is not a development release, then return latest stable.

    @return: string of latest release
    """
    try:
        return distro_info.UbuntuDistroInfo().devel()
    except distro_info.DistroDataOutdated:
        return distro_info.UbuntuDistroInfo().stable()


def setup_results_dir(results_dir=None):
    """Create base results directory for each run.

    Utilizes the format YYYYMMDDHHSS for base directory.

    @param results_dir: optional, path to store results
    @return path to results directory for this run
    """
    if not results_dir:
        results_dir = 'results'

    date = datetime.now().strftime("%Y%m%d%H%M%S")
    results_dir = os.path.join(results_dir, date)
    os.makedirs(results_dir)

    LOG.info('result stored in %s', (results_dir))
    return results_dir


def subp(cmd, data=None):
    """Run a command using subprocess.

    @param cmd: array with commands to run
    @param data: data to pass via stdin
    @return: tupple of stdout and stderr
    """
    if not data:
        devnull_fp = open(os.devnull)
        stdin = devnull_fp
    else:
        stdin = subprocess.PIPE

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, stdin=stdin)
    out, err = process.communicate(data)

    if out:
        out = out.strip().decode()
    if err:
        err = err.strip().decode()

    return out, err


def system_architecture():
    """Return system architecture from dpkg.

    @return: string of system architecture
    """
    out, _ = subp(['dpkg', '--print-architecture'])
    return out
