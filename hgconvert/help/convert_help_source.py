import hgext.convert.convcmd

from hgext.convert.hg import mercurial_source as basesource


class convert_help_source(basesource):

    @staticmethod
    def filtered(revs):
        passed = []
        for rev in revs:
            if 'help/' in rev[0]:
                passed.append(rev)
        return passed

    def getchanges(self, version, full):
        # returns (filename, rev) list and target, source dictionary
        # files not included in the list is just ignored
        changes = super(convert_help_source, self).getchanges(version, full)
        changes = (self.filtered(changes[0]), changes[1], changes[2])
        return changes


hgext.convert.convcmd.source_converters.append(('convert_help_source', convert_help_source, 'branchsort'))
