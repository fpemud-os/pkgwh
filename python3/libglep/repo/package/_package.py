import glob
from snakeoil import klass
from snakeoil import osutils
from snakeoil.data_source import local_source
from ._metadata_xml import MetaDataXML
from ._digest import Manifest
from ... import CPV


class Package(metaclass=klass.immutable_instance):

    def __init__(self, repo, cp_obj):
        self.repo = repo
        self.cp_obj = cp_obj

        self.ebuild_files = []
        self.manifest = None
        self.metadata_xml = None

    @property
    def metadata_xml(self):
        # FIXME: should support lazy-loading and weak-reference through decoration
        #        return None if no meatadata.xml
        fullfn = osutils.pjoin(self.repo.get_package_dirpath(), "metadata.xml")
        return MetaDataXML(fullfn)

    @property
    def manifest(self):
        # FIXME: should support lazy-loading and weak-reference through decoration
        #        return None if no Manifest, possible?
        fullfn = osutils.pjoin(self.repo.get_package_dirpath(), "Manifest")
        return Manifest(fullfn, thin=self.repo.manifests.thin, enforce_gpg=False)       # FIXME: enforce_gpg needs modification?

    def get_CPVs(self):
        cpv_pattern = osutils.pjoin(self.location, self.cp_obj.category, self.cp_obj.package, f"*.{self.repo._extension}")
        ret = glob.glob(cpv_pattern)                                                            # list all ebuild files
        assert all(x.startswith(self.cp_obj.package) for x in ret)
        ret = [x[len(self.cp_obj.package):len(self.repo._extension)*-1] for x in ret]
        return tuple([CPV(self.cp_obj.category, self.cp_obj.package, x, _do_check=False) for x in ret])       # FIXME: why convert to tuple? for performance? for read-only?

    def get_ebuild_filename(self, cpv_obj):
        return f"{cpv_obj.package}-{cpv_obj.fullver}.{self.extension}"

    def get_ebuild_filepath(self, cpv_obj):
        return osutils.pjoin(self.location, cpv_obj.category, cpv_obj.package, self._get_ebuild_filename(cpv_obj))

    def get_ebuild_src(self, pkg):
        return local_source(self._get_ebuild_filepath(pkg), encoding='utf8')
