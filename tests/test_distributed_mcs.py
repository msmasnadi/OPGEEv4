import re
from opgee.mcs.distributed_mcs_dask import RemoteError, FieldStatus

def test_remote_error():
    field_name = 'field_1'
    err_msg = "Short message"
    e = RemoteError(err_msg, field_name)
    s = str(e)
    assert s ==  f"<RemoteError field='{field_name}' msg='{err_msg}'>"

def test_field_status():
    field_name = 'field_10'
    duration = 10.6
    err_msg = 'no message'
    completed = 10
    e = RemoteError(err_msg, field_name)
    res = FieldStatus(field_name, duration, completed, error=e)

    s = str(res)
    pat = f'<FieldStatus {completed} trials of {field_name} in .*; task_count:0 error:.*>'
    assert re.match(pat, s) is not None

    assert res.duration == duration and res.field_name == field_name and res.error == e
