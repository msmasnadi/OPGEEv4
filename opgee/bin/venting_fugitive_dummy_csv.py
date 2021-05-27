#!/usr/bin/env python
import pandas as pd
import numpy as np
from opgee.process import Process, _subclass_dict

N = 1000
d = _subclass_dict(Process)
columns = list(d.keys())

df = pd.DataFrame(data=[], columns=columns, index=range(N))

for name in columns:
    df[name] = np.random.uniform(0.001, 0.003, N)

df.to_csv('/tmp/venting_fugitives_by_process.csv', index=None)
