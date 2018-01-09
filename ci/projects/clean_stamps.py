# manage 'clean' stamps
# store file into working directory of master and node containing timestamp of last performed clean
# check if those stamps matching, passing stamps from master to node in state
# if they do not match - this means clean build was requested after current workspace was cleared last time

import os.path
import time
import logging

log = logging.getLogger(__name__)


CLEAN_STAMP_PATH = 'clean.stamp'
CLEAN_BUILD_STAMP_PATH = 'clean-build.stamp'


class CleanStamps(object):

    def __init__(self, state):
        self._state = state

    def init_master(self, params):
        new_stamp = int(time.time())
        self._load_all_clean_stamps()
        if params.clean or params.clean_only or not self._state.clean_stamp:
            self._state.clean_stamp = new_stamp
            self._save_clean_stamp()
        if params.clean_build or not self._state.clean_build_stamp:
            self._state.clean_build_stamp = new_stamp
            self._save_clean_build_stamp()

    def check_must_clean_node(self):
        node_clean_stamp = self._load_clean_stamp()  # stamp of this node
        if node_clean_stamp and node_clean_stamp != self._state.clean_stamp:
            log.info('This node was cleaned before last clean was requested - cleaning working dir now')
            return True
        if not node_clean_stamp:  # workspace was clean - save stamp to this node
            self._save_clean_stamp()
        return False

    def must_do_clean_build(self, params):
        clean_build = params.clean_build
        node_clean_build_stamp = self._load_clean_build_stamp()  # stamp of this node
        if not clean_build and node_clean_build_stamp and node_clean_build_stamp != self._state.clean_build_stamp:
            log.info("This node's build dir was cleaned before last clean build was requested - cleaning it now")
            clean_build = True
        self._save_clean_build_stamp()
        return clean_build

    def _load_all_clean_stamps(self):
        self._state.clean_stamp = self._load_clean_stamp()
        self._state.clean_build_stamp = self._load_clean_build_stamp()

    def _load_clean_stamp(self):
        return self._load_stamp(CLEAN_STAMP_PATH)

    def _load_clean_build_stamp(self):
        return self._load_stamp(CLEAN_BUILD_STAMP_PATH)

    def _save_clean_stamp(self):
        self._save_stamp(self._state.clean_stamp, CLEAN_STAMP_PATH)

    def _save_clean_build_stamp(self):
        self._save_stamp(self._state.clean_build_stamp, CLEAN_BUILD_STAMP_PATH)

    def _load_stamp(self, file_path):
        if not os.path.isfile(file_path):
            return None
        with open(file_path) as f:
            return int(f.read().strip())

    def _save_stamp(self, stamp, file_path):
        if not stamp: return  # do not save None
        with open(file_path, 'w') as f:
            f.write(str(stamp))
