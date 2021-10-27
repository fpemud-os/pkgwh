#!/usr/bin/env python3

# Copyright (c) 2005-2014 Fpemud <fpemud@sina.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class InvalidCP(ValueError):
    """CP with unsupported characters or format."""

    def __init__(self, cp_str, err=None):
        self.atom = cp_str
        self.err = err
        super().__init__(str(self))

    def __str__(self):
        msg = f'invalid CP: {self.cp_str!r}'
        if self.err is not None:
            msg += f': {self.err}'
        return msg


class InvalidCPV(ValueError):
    """CPV with unsupported characters or format."""

    def __init__(self, cpv_str, err=None):
        self.atom = cpv_str
        self.err = err
        super().__init__(str(self))

    def __str__(self):
        msg = f'invalid CPV: {self.cpv_str!r}'
        if self.err is not None:
            msg += f': {self.err}'
        return msg


class InvalidPkgWildcard(ValueError):
    # FIXME
    pass


class InvalidPkgAtom(ValueError):
    """Package atom doesn't follow required specifications."""

    def __init__(self, atom, err=None):
        self.atom = atom
        self.err = err
        super().__init__(str(self))

    def __str__(self):
        msg = f'invalid package atom: {self.atom!r}'
        if self.err is not None:
            msg += f': {self.err}'
        return msg


class ProfileError(Exception):
    pass


class ProfileNotExistError(ProfileError):
    """Profile for a nonexistent directory."""

    def __init__(self, dirpath):
        self.dirpath = dirpath

    def __str__(self):
        return f"nonexistent profile directory {self.dirpath!r}"


class ProfileParseError(ProfileError):
    """Profile property file parse failed."""

    def __init__(self, filename, error, line=None, lineno=None):
        if line is not None:
            assert lineno is not None
        else:
            assert lineno is None

        self._filename = filename
        self._error = error
        self._line = line
        self._lineno = lineno

    def __str__(self):
        ret = "failed parsing %s: %s" % (self._filename, self._error)
        if self._line is not None:
            ret += ", line %d: %d" % (self._lineno, self._line)
        return ret
