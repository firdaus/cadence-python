import os

import thriftrw

this_dir = os.path.dirname(__file__)
cadence_thrift_file = os.path.join(this_dir, "thrift/cadence.thrift")
cadence_thrift = thriftrw.load(cadence_thrift_file)
