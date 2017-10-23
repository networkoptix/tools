import bz2


def decode_artifact_data(artifact):
    if artifact.encoding == 'bz2':
        return bz2.decompress(artifact.data)
    elif not artifact.encoding:
        return artifact.data
    else:
        assert False, 'Unknown artifact encoding: %r' % artifact.encoding
