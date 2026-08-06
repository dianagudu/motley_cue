"""The AUDIT log level.

Records of what motley_cue actually *decided* for a user -- as opposed to how it
got there -- should stay visible whatever verbosity an operator configures.

Both the logger and every handler filter on level, and the highest level that
can be configured is CRITICAL, so a level above it passes unconditionally. This
keeps audit records in the normal log, in context, without a second log file;
should one be wanted later, give this level its own handler.
"""

import logging

AUDIT = logging.CRITICAL + 10
logging.addLevelName(AUDIT, "AUDIT")


def audit(log: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Log an audit record, visible regardless of the configured log_level.

    Takes the caller's own logger so that `%(name)s` still identifies the
    module. `stacklevel=2` attributes the record to the caller rather than to
    this helper.
    """
    log.log(AUDIT, msg, *args, stacklevel=2, **kwargs)
