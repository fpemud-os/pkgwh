
class Manifests:                    # FIXME: change to klass.ImmutableInstance, we don't use _immutable_attr_dict because we want a obvious class name

    def __init__(self):
        self.disabled = None
        self.strict = None
        self.thin = None
        self.signed = None
        self.hashes = None
        self.required_hashes = None

