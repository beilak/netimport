"""Compatibility wrapper for policy violation helpers."""

from netimport_lib.policy import violations as _violations


EXTERNAL_LIB_NODE_TYPE = _violations.EXTERNAL_LIB_NODE_TYPE
UNRESOLVED_PREFIX = _violations.UNRESOLVED_PREFIX
Violation = _violations.Violation
build_violations = _violations.build_violations
build_violations_payload = _violations.build_violations_payload
