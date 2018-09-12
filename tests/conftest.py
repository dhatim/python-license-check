import os
import tempfile

import pytest


@pytest.fixture
def tmpfile():
    fd, filepath = tempfile.mkstemp()
    yield (os.fdopen(fd, "w"), filepath)
    try:
        os.close(fd)
    except OSError:
        pass  # It may already be closed
    os.remove(filepath)
