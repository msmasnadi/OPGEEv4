import re
from opgee.mcs.distributed_mcs import Manager, RemoteError, FieldResult
from .utils_for_tests import tmpdir

# def test_dist_mcs():
#     sim_dir = tmpdir('test-sim')
#     mgr = Manager()
#     mgr.run_mcs(sim_dir)

def test_remote_error():
    field_name = 'field_1'
    err_msg = "Short message"
    e = RemoteError(err_msg, field_name)
    s = str(e)
    assert s ==  f"<RemoteError field='{field_name} msg='{err_msg}'>"

def test_field_result():
    field_name = 'field_10'
    duration = 10.6
    err_msg = 'no message'
    e = RemoteError(err_msg, field_name)
    res = FieldResult(field_name, duration, error=e)

    s = str(res)
    pat = f'<FieldResult {field_name} in .*; error:.*>'
    assert re.match(pat, s) is not None

    assert res.duration == duration and res.field_name == field_name and res.error == e
