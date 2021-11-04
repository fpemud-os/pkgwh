"""
filesystem abstractions, and select operations
"""

from ._fs import FileEntry, DirEntry, SymlinkEntry, DevfileEntry, FifoEntry
from ._contents import ContentsSet, OrderedContentsSet
