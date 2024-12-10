from opgee.import_export import ELECTRICITY, NATURAL_GAS, ImportExport
from opgee.units import ureg


def test_import():
    obj = ImportExport()

    obj.set_import("proc1", ELECTRICITY, ureg.Quantity(100., "kWh/day"))

    obj.set_import("proc2", ELECTRICITY, ureg.Quantity(200., "kWh/day"))
    obj.set_import("proc2", NATURAL_GAS, ureg.Quantity(2000., "mmbtu/day"))

    obj.set_export("proc2", NATURAL_GAS, ureg.Quantity(450., "mmbtu/day"))

    df = obj.imports_exports()

    imports = df[ImportExport.IMPORT]
    exports = df[ImportExport.EXPORT]
    net_imp = df[ImportExport.NET_IMPORTS]

    assert imports[NATURAL_GAS] == ureg.Quantity(2000., "mmbtu/day")
    assert imports[ELECTRICITY] == ureg.Quantity(300., "kWh/day")

    assert exports[NATURAL_GAS] == ureg.Quantity(450., "mmbtu/day")

    assert net_imp[NATURAL_GAS] == (ureg.Quantity(2000, "mmbtu/day") - ureg.Quantity(450, "mmbtu/day"))

    proc1_imp = obj.proc_imports("proc1")
    proc2_imp = obj.proc_imports("proc2")
    proc2_exp = obj.proc_exports("proc2")

    proc1_imp[ELECTRICITY] == ureg.Quantity(100., "kWh/day")

    proc2_imp[ELECTRICITY] == ureg.Quantity(200., "kWh/day")
    proc2_exp[NATURAL_GAS] == ureg.Quantity(450., "mmbtu/day")
