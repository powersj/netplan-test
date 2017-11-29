"""Control an image for testing."""
import logging
import os
import shlex
import shutil
import signal
import subprocess

from .utils import subp


class BaseImage(object):
    """Base Image Object."""

    def __init__(self, base_image_path, results_dir):
        """Clone pristine image to create base image.

        image_name  bionic-server-cloudimg-amd64.img
        directory   results/20171128091153
        path        results/20171128091153/bionic-server-cloudimg-amd64.img

        @param base_image_path: base image path
        @param results_dir: where to store image for run.
        """
        self.log = logging.getLogger('netplan_test')
        self.image_name = os.path.basename(base_image_path)
        self.directory = results_dir
        self.path = os.path.join(results_dir, self.image_name)

        self.log.debug('creating base image: %s', (self.image_name))
        shutil.copyfile(base_image_path, self.path)

    def __del__(self):
        """Clean up the base image at end."""
        if os.path.exists(self.path):
            os.remove(self.path)


class TestImage(object):
    """Test Image Object."""

    def __init__(self, base_image, test_yaml_path):
        """Create test image backed by original image.

        test_name   basic
        directory   results/20171128091153/basic
        path        results/20171128091153/basic/image.qcow

        @param base_image: BaseImage object to use for backing image
        @param test_yaml_path: path to test yaml file
        """
        self.log = logging.getLogger('netplan_test')
        self.test_name = os.path.basename(test_yaml_path).strip('.yaml')
        self.directory = os.path.join(base_image.directory, self.test_name)
        self.path = os.path.join(self.directory, 'image.qcow')
        self.path_seed = None

        self.log.info('running test: %s', (self.test_name))
        os.mkdir(self.directory)

        self.log.debug('creating test image')
        subp(['qemu-img', 'create', '-f', 'qcow2', '-b',
              os.path.abspath(base_image.path),
              os.path.abspath(self.path)])
        self.push_file(test_yaml_path, '/etc/netplan/netplan.yaml')
        self.execute(['netplan', 'apply'])

    def __del__(self):
        """Clean up the backing image, leave everything else."""
        if os.path.exists(self.path):
            os.remove(self.path)
        if os.path.exists(self.path_seed):
            os.remove(self.path_seed)

    def collect(self):
        """Will mount and collect varous files from image."""
        self.log.debug('collecting results')
        log_dir = '/var/tmp/'
        out, _ = self.execute(['ls', log_dir])
        for file in out.splitlines():
            self.pull_file(os.path.join(log_dir, file),
                           os.path.join(self.directory, file))

    def execute(self, cmd):
        """Execute command in image.

        @param cmd: command to run
        """
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        return self._mount_image_callback(cmd)

    def launch(self):
        """Will launch VM with configured parameters and wait for shutdown.

        Added 5 minute timeout will automaticaly kill the process if needed.
        """
        log_console = os.path.join(self.directory, 'console.log')
        self.path_seed = self._generate_seed()

        disk = ('file=%s,id=disk00,if=none,format=qcow2,index=0,'
                'cache=unsafe' % (self.path))
        seed = ('file=%s,id=disk01,if=none,format=raw,index=1,'
                'cache=unsafe' % (self.path_seed))

        storage = [
            '-device', 'virtio-scsi-pci,id=virtio-scsi',
            '-drive', disk,
            '-device', 'virtio-blk,drive=disk00,serial=image.qcow',
            '-drive', seed,
            '-device', 'virtio-blk,drive=disk01,serial=seed.img'
        ]

        network = [
            '-device', 'virtio-net-pci,netdev=net00,mac=52:54:00:12:34:04',
            '-netdev', 'type=user,id=net00',
            '-device', 'virtio-net-pci,netdev=net01,mac=52:54:00:12:34:05',
            '-netdev', 'type=user,id=net01',
            '-device', 'virtio-net-pci,netdev=net02,mac=52:54:00:12:34:06',
            '-netdev', 'type=user,id=net02',
            '-device', 'virtio-net-pci,netdev=net03,mac=52:54:00:12:34:07',
            '-netdev', 'type=user,id=net03',
        ]

        base_cmd = [
            'qemu-system-x86_64', '-enable-kvm',
            '-vnc', 'none', '-nographic', '-serial', 'file:%s' % log_console,
            '-m', '2G', '-smp', '2'
        ]

        self.log.debug('launching image')
        process = subprocess.Popen(base_cmd + storage + network,
                                   close_fds=True, preexec_fn=os.setsid,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)

        try:
            process.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)
            process.communicate()

    def pull_file(self, remote_path, local_path):
        """Pull a file from image.

        This is taken directly from cloud-init integration testing.

        @param remote_path: image path to file
        @param local_path: local path to pull file to
        """
        cmd = ["sh", "-c", 'exec cat "$1"', 'read_data', remote_path]
        out, _ = self._mount_image_callback(cmd)
        with open(local_path, 'wt') as file:
            file.write(out)

    def push_file(self, local_path, remote_path):
        """Push file to image.

        This is taken directly from cloud-init integration testing.

        @param local_path: local path to file
        @param remote_path: remote path to push file to
        """
        cmd = ["sh", "-c", 'exec cat >"$1"', 'write_data', remote_path]
        with open(local_path, "rb") as file:
            self._mount_image_callback(cmd, stdin=file.read())

    def _generate_seed(self):
        """Generate nocloud seed with preformatted user-data.

        @return: path to seed for NoCloud KVM
        """
        self.log.debug('generating seed image')
        user_data = './netplan_test/user-data.yaml'
        seed_file = os.path.join(self.directory, 'seed.img')

        out, err = subp(['cloud-localds', seed_file, user_data])

        if err:
            self.log.fatal(out)
            self.log.fatal(err)

        return seed_file

    def _mount_image_callback(self, command, stdin=None):
        """Run mount-image-callback.

        @param command: command to run
        @param stdin: optional, standard intput to pass into command
        @return: tuple of stdout and stderr
        """
        mic_chroot = ['sudo', 'mount-image-callback', '--system-mounts',
                      '--system-resolvconf', self.path,
                      '--', 'chroot', '_MOUNTPOINT_']

        out, err = subp(mic_chroot + list(command), data=stdin)

        if not isinstance(out, str):
            out = out.decode("utf-8")
        if not isinstance(err, str):
            err = err.decode("utf-8")

        return (out, err)
