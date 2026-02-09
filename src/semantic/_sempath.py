# Path setup for installed semantic scripts.
# Copyright 2026 ITTH GmbH & Co. KG
import os
import sys

_mydir = os.path.dirname(os.path.abspath(__file__))
if _mydir not in sys.path:
    sys.path.insert(0, _mydir)
_filterdir = os.path.join(os.path.dirname(_mydir), 'recoll', 'filters')
if os.path.isdir(_filterdir) and _filterdir not in sys.path:
    sys.path.insert(0, _filterdir)
