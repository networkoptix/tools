from pony.orm import desc, select, exists, raw_sql
from .. import models


ARTIFACT_COMPRESS_RATIO = 10  # Just some value from some small artifact. For large artifacts seen ratio 55
ARTIFACT_LINE_LENGTH = 220    # Mean artifact line lengh from same random artifact, for first 1000 lines
MAX_INLINE_ARTIFACT_LINE_COUNT = 1000


class ArtifactRec(object):

    def __init__(self, artifact_id, artifact_name, is_error, type_name, content_type, is_inline):
        self.id = artifact_id
        self.name = artifact_name
        self.is_error = is_error
        self.is_inline = is_inline
        self.disposition = artifact_disposition(content_type)
        if type_name not in ['output', 'traceback', 'core']:
            self.name += ' ' + type_name


class RunNode(object):

    def __init__(self, path_tuple, run, artifacts=None, lazy=False, has_children=False):
        self.path_tuple = path_tuple
        self.run = run
        self.artifacts = artifacts or []
        self.children = []  # RunNode list
        self.lazy = lazy  # children must by retrieved using ajax if True
        self._has_children = has_children

    @property
    def has_children(self):
        return self.children or self._has_children


def artifact_disposition(content_type):
    if content_type.startswith('text/') or content_type == 'application/json':
        return 'inline'
    else:
        return 'attachment'

def can_show_artifact_inline(content_type, data_len):
    if artifact_disposition(content_type) != 'inline':
        return False
    if (data_len * ARTIFACT_COMPRESS_RATIO) / ARTIFACT_LINE_LENGTH > MAX_INLINE_ARTIFACT_LINE_COUNT:
        return False
    return True

def load_artifacts(root_run_list):
    run_id2artifacts = {}  # Run -> ArtifactRec list
    for run_id, artifact_id, artifact_name, is_error, data_len, type_name, content_type in select(
            (run.id, artifact.id, artifact.short_name, artifact.is_error,
                 raw_sql('length(artifact.data)'),
                 artifact.type.name, artifact.type.content_type)
            for artifact in models.Artifact
            for run in models.Run
            if (run.root_run in root_run_list or run in root_run_list) and artifact.run == run).order_by(2):
        is_inline = can_show_artifact_inline(content_type, data_len)
        rec = ArtifactRec(artifact_id, artifact_name, is_error, type_name, content_type, is_inline)
        run_id2artifacts.setdefault(run_id, []).append(rec)
    return run_id2artifacts

def load_root_run_node_list(page, page_size, branch=None, platform=None, version=None):
    query = select(run for run in models.Run if run.root_run is None)
    if branch:
        query = query.filter(branch=branch)
    if platform:
        query = query.filter(platform=platform)
    if version:
        query = query.filter(version=version)
    root_run_list = query.order_by(desc(models.Run.id)).page(page, page_size)
    run_id2artifacts = load_artifacts(root_run_list)
    run_has_children = dict(select((run.id, exists(run.children)) for run in models.Run if run in root_run_list))
    return [RunNode((run.path.rstrip('/'),), run, run_id2artifacts.get(run.id),
                    lazy=True, has_children=run_has_children[run.id])
                    for run in root_run_list]

def load_run_node_tree(root_run):
    run_id2artifacts = load_artifacts([root_run])
    root_node = RunNode((int(root_run.path.rstrip('/')),), root_run, run_id2artifacts.get(root_run.id))
    path2node = {root_node.path_tuple: root_node}
    for run in select(run for run in models.Run if run.root_run is root_run):
        path_tuple = tuple(map(int, run.path.rstrip('/').split('/')))
        path2node[path_tuple] = RunNode(path_tuple, run, run_id2artifacts.get(run.id))
    for path, node in path2node.items():
        if len(path) == 1: continue
        parent = path2node[path[:-1]]
        parent.children.append(node)
    for node in path2node.values():
        node.children = sorted(node.children, key=lambda node: node.path_tuple)
    return root_node
