import glob
from snakeoil import klass
from snakeoil import osutils
from snakeoil.data_source import local_source
from ._metadata_xml import MetaDataXML
from ._digest import Manifest
from ... import CPV


class Package(metaclass=klass.immutable_instance):

    def __init__(self, repo, cp_obj):
        self._repo = repo
        self._cpObj = cp_obj

        self.ebuild_files = []
        self.manifest = None
        self.metadata_xml = None

    @property
    def metadata_xml(self):
        # FIXME: should support lazy-loading and weak-reference through decoration
        #        return None if no meatadata.xml
        fullfn = osutils.pjoin(self._repo.get_package_dirpath(), "metadata.xml")
        return MetaDataXML(fullfn)

    @property
    def manifest(self):
        # FIXME: should support lazy-loading and weak-reference through decoration
        #        return None if no Manifest, possible?
        fullfn = osutils.pjoin(self._repo.get_package_dirpath(), "Manifest")
        return Manifest(fullfn, thin=self._repo.manifests.thin, enforce_gpg=False)       # FIXME: enforce_gpg needs modification?

    def get_CP(self):
        return self._cpObj

    def get_CPVs(self):
        cpv_pattern = osutils.pjoin(self.location, self._cpObj.category, self._cpObj.package, f"*.{self._repo._extension}")
        ret = glob.glob(cpv_pattern)                                                            # list all ebuild files
        assert all(x.startswith(self._cpObj.package) for x in ret)
        ret = [x[len(self._cpObj.package):len(self._repo._extension)*-1] for x in ret]
        return tuple([CPV(self._cpObj.category, self._cpObj.package, x, _do_check=False) for x in ret])       # FIXME: why convert to tuple? for performance? for read-only?

    def get_ebuild_filename(self, cpv_obj):
        return f"{cpv_obj.package}-{cpv_obj.fullver}.{self.extension}"

    def get_ebuild_filepath(self, cpv_obj):
        return osutils.pjoin(self.location, cpv_obj.category, cpv_obj.package, self._get_ebuild_filename(cpv_obj))

    def get_ebuild_src(self, pkg):
        return local_source(self._get_ebuild_filepath(pkg), encoding='utf8')
