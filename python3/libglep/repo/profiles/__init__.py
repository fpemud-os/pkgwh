
class KnownProfile:                    # FIXME: change to klass.ImmutableInstance, we don't use _immutable_attr_dict because we want a obvious class name

    STATUS_STABLE = "stable"
    STATUS_EXPERIMENTAL = "exp"
    STATUS_DEVELOPING = "dev"

    def __init__(self, arch, path, status, deprecated):
        self.arch = arch
        self.path = path
        self.status = status              # enum STATUS_
        self.deprecated = deprecated      # bool
