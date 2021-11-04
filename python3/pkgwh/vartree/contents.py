
import os
import stat

from snakeoil import data_source
from snakeoil.chksum import get_handler
from snakeoil.fileutils import AtomicWriteFile, readlines_utf8

from .. import os_data
from ..fs import fs
from ..fs.contents import ContentsSet


class ContentsFile:
    """class wrapping a contents file"""

    def __init__(self, path):
        self._path = path

    def read(self):
        return None

    def write(self, entry_set):

        return AtomicWriteFile(self._path, uid=os_data.root_uid, gid=os_data.root_gid, perms=0o644)


    def add(self, obj):
        if obj.is_reg:
            # strict checks
            if obj.chksums is None or "md5" not in obj.chksums:
                raise TypeError("fsFile objects need to be strict")

        ContentsSet.add(self, obj)

    def _get_fd(self, write=False):
        if isinstance(self._source, str):
            if write:
                return AtomicWriteFile(
                    self._source, uid=os_data.root_uid,
                    gid=os_data.root_gid, perms=0o644)
            return readlines_utf8(self._source, True)
        fobj = self._source.text_fileobj(writable=write)
        if write:
            fobj.seek(0, 0)
            fobj.truncate(0)
        return fobj

    def flush(self):
        return self._write()

    def _iter_contents(self):
        self.clear()
        for line in self._get_fd():
            if not line:
                continue
            s = line.split(" ")
            if s[0] in ("dir", "dev", "fif"):
                path = ' '.join(s[1:])
                if s[0] == 'dir':
                    obj = fs.fsDir(path, strict=False)
                elif s[0] == 'dev':
                    obj = LookupFsDev(path, strict=False)
                else:
                    obj = fs.fsFifo(path, strict=False)
            elif s[0] == "obj":
                path = ' '.join(s[1:-2])
                obj = fs.fsFile(
                    path, chksums={"md5":int(s[-2], 16)},
                        mtime=int(s[-1]), strict=False)
            elif s[0] == "sym":
                try:
                    p = s.index("->")
                    obj = fs.fsLink(' '.join(s[1:p]), ' '.join(s[p+1:-1]),
                        mtime=int(s[-1]), strict=False)

                except ValueError:
                    # XXX throw a corruption error
                    raise
            else:
                raise Exception(f"unknown entry type {line!r}")

            yield obj

    def _write(self):
        md5_handler = get_handler('md5')
        outfile = None
        try:
            outfile = self._get_fd(True)

            for obj in sorted(self):

                if obj.is_reg:
                    s = " ".join(("obj", obj.location,
                        md5_handler.long2str(obj.chksums["md5"]),
                        str(int(obj.mtime))))

                elif obj.is_sym:
                    s = " ".join(("sym", obj.location, "->",
                                   obj.target, str(int(obj.mtime))))

                elif obj.is_dir:
                    s = "dir " + obj.location

                elif obj.is_dev:
                    s = "dev " + obj.location

                elif obj.is_fifo:
                    s = "fif " + obj.location

                else:
                    raise Exception(f"unknown type {type(obj)}: {obj}")
                outfile.write(s + "\n")
            outfile.close()

        finally:
            # if atomic, it forces the update to be wiped.
            del outfile
