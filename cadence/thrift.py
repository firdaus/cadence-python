import os

import thriftrw

this_dir = os.path.dirname(__file__)
cadence_thrift = os.path.join(this_dir, "thrift/cadence.thrift")
cadence = thriftrw.load(cadence_thrift)
