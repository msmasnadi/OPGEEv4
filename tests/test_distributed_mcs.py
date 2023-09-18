import re
from opgee.field import FieldResult

def test_field_status():
    analysis_name = 'test'
    field_name = 'field_10'
    result_type = 'simple'
    trial_num = 6
    err_msg = 'no message'

    res = FieldResult(analysis_name, field_name, result_type, trial_num=trial_num, error=err_msg)
    s = str(res)

    pat = f'<FieldResult ana:{analysis_name} fld:{field_name} trl:{trial_num} err:{err_msg} res:{result_type}>'
    assert re.match(pat, s) is not None

    assert res.energy is None and res.emissions is None

    energy = "energy proxy"
    emiss = "emiss proxy"
    res = FieldResult(analysis_name, field_name, result_type, energy_data=energy, emissions_data=emiss)

    assert res.energy == energy and res.emissions == emiss
