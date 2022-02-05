from opgee import ureg
from opgee.import_export import ImportExport

def test_import():
    obj = ImportExport()

    obj.add_import("proc1", ImportExport.ELECTRICITY, ureg.Quantity(100., "kWh/day"))

    obj.add_import("proc2", ImportExport.ELECTRICITY, ureg.Quantity(200., "kWh/day"))
    obj.add_import("proc2", ImportExport.NATURAL_GAS, ureg.Quantity(2000., "mmbtu/day"))

    obj.add_export("proc2", ImportExport.NATURAL_GAS, ureg.Quantity(450., "mmbtu/day"))

    df = obj.imports_exports()

    imports = df[ImportExport.IMPORT]
    exports = df[ImportExport.EXPORT]
    net_imp = df[ImportExport.NET_IMPORTS]

    assert imports[ImportExport.NATURAL_GAS] == ureg.Quantity(2000., "mmbtu/day")
    assert imports[ImportExport.ELECTRICITY] == ureg.Quantity(300., "kWh/day")

    assert exports[ImportExport.NATURAL_GAS] == ureg.Quantity(450., "mmbtu/day")

    assert net_imp[ImportExport.NATURAL_GAS] == (ureg.Quantity(2000, "mmbtu/day") - ureg.Quantity(450, "mmbtu/day"))

    proc1_imp = obj.proc_imports("proc1")
    proc2_imp = obj.proc_imports("proc2")
    proc2_exp = obj.proc_exports("proc2")

    proc1_imp[ImportExport.ELECTRICITY] == ureg.Quantity(100., "kWh/day")

    proc2_imp[ImportExport.ELECTRICITY] == ureg.Quantity(200., "kWh/day")
    proc2_exp[ImportExport.NATURAL_GAS] == ureg.Quantity(450., "mmbtu/day")
