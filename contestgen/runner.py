import argparse
import os
import shutil
import sys
import threading
import yaml
from collections import OrderedDict
from subprocess import Popen, PIPE
from contestgen import __version__
from contestgen.utilities import configure_yaml  # noqa: F401
from contestgen.utilities.logger import logger, logger_format_fields, setup_logger
# PyYAML 3.12 compatibility
try:
    from yaml import FullLoader as DefaultLoader
except ImportError:
    from yaml import Loader as DefaultLoader


def record_test(configuration, test_name, command):
    """
    Record the input and output of the given command, placing it within a a
    test recipe

    :param command: list of strings forming a complete command to run
    :param test_name: name to save the test results under
    :return: 0 for success, otherwise return an error message
    """
    class RecorderPipe(threading.Thread):
        """
        Custom thread with a pipe for intercepting stdin ina  subprocess
        """
        def __init__(self):
            """
            Initialize the thread
            """
            threading.Thread.__init__(self)
            self.daemon = True

            self.lines = []
            self.process = None

            self.rd, self.wd = os.pipe()
            self.rpipe = os.fdopen(self.rd)
            self.wpipe = os.fdopen(self.wd, 'w')

            self.start()

        def fileno(self):
            """
            Returns the file descriptor of the read-end of the pipe

            :return: file descriptor
            """
            return self.rd

        def run(self):
            """
            Method for the running thread. Will yield until the external
            subprocess is hooked in and will continuw while the write-end of the
            pipe is open and the subprocess is still running.
            """
            while self.process is None:
                pass

            # TODO: potential race condition here? investigate later.
            while self.wpipe is not None and self.process.poll() is None:
                s = input()
                self.wpipe.write(s + '\n')
                self.wpipe.flush()
                self.lines.append(s)
                # TODO: is this necessary? investigate later.
                self.check()

        def check(self):
            """
            Check if the subprocess is opened, and if it is not, cleanup
            """
            if self.process.poll() is not None:
                self.close()

        def close(self):
            """
            Close both ends of the pipe and set the write-end to None
            """
            self.rpipe.close()
            self.wpipe.close()
            self.wpipe = None

    def get_files(root):
        files = []
        for el in os.listdir(root):
            full_path = os.path.join(root, el)
            if os.path.isfile(full_path):
                files.append(full_path)
            else:
                files.extend(get_files(full_path))
        return files

    logger.debug('Starting test with command "{}"'.format(command))
    recorder_pipe = RecorderPipe()

    files = set(get_files('.'))

    proc = Popen(command, stdin=recorder_pipe, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    recorder_pipe.process = proc
    stdout, stderr = proc.communicate()
    logger.debug('Test complete... writing to recipe...')

    new_files = set(get_files('.')) - files

    if os.path.exists(configuration):
        with open(configuration, 'r') as recipe:
            test_matrix = yaml.load(open(configuration, 'r'), Loader=DefaultLoader)
        if test_name in test_matrix['test-cases']:
            return '{} is already a test case! Choose a new name!'.format(test_name)
        test_matrix['test-cases'][test_name] = OrderedDict()
        test_case = test_matrix['test-cases'][test_name]
        if command[0] != test_matrix['executable']:
            test_case['executable'] = command[0]
    else:
        test_matrix = OrderedDict()
        test_matrix['executable'] = command[0]
        test_matrix['test-cases'] = OrderedDict()
        test_matrix['test-cases'][test_name] = OrderedDict()
        test_case = test_matrix['test-cases'][test_name]

    test_case['return-code'] = proc.returncode

    argv = command[1:]
    if argv:
        test_case['argv'] = command[1:]
    if recorder_pipe.lines:
        test_case['stdin'] = '\n'.join(recorder_pipe.lines)
    if stdout:
        test_case['stdout'] = stdout
    if stderr:
        test_case['stderr'] = stderr

    if new_files:
        test_case['ofstreams'] = []
        for new_file in new_files:
            dir_name, file_name = os.path.split(new_file)
            base_file = os.path.join(dir_name, 'contest_' + file_name)
            shutil.move(new_file, base_file)
            test_case['ofstreams'].append(OrderedDict())
            test_case['ofstreams'][-1]['base-file'] = base_file
            test_case['ofstreams'][-1]['test-file'] = new_file

    recipe = open(configuration, 'w')
    yaml.dump(test_matrix, recipe)
    return 0


def test():
    """Run the specified test configuration"""
    parser = argparse.ArgumentParser(__file__)
    parser.add_argument('configuration', help='path to a YAML test configuration file')
    parser.add_argument('test_name', help='name for the test being generated; name must be unused already')
    parser.add_argument('generate', nargs='+', help='executable and arguments to generate a test for')
    parser.add_argument('--verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('--version', action='version', version='contest.py v{}'.format(__version__.__version__))
    inputs = parser.parse_args()

    setup_logger(inputs.verbose)

    return record_test(inputs.configuration, inputs.test_name, inputs.generate)


if __name__ == '__main__':
    sys.exit(test())
