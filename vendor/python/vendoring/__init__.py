"""Vendoring protocol: check a consumer's vendored packages against their pins.

A consumer repository copies each upstream package directory byte-for-byte and
records, per package, the upstream repository, the upstream commit, the local
root that acts as the include path, and the SHA-256 of every vendored file.
`check_vendored_sync` verifies that every pinned file exists with the pinned
digest and that no unlisted source file sits inside a vendored package
directory, so no local patch can land unnoticed.

The package decides nothing about the code it checks. Drift is reported; what
a consumer does about it is the consumer's policy.
"""
