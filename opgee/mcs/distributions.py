#
# Default parameter distributions. User can redefine distributions for any attribute,
# overriding the defaults defined here.
#
from ..smart_defaults import SmartDefault
from .simulation import Distribution
from .distro import get_frozen_rv

# TBD: How to handle distributions on tabular data?
#      Define an attribute that's set from a cell in a table? Cumbersome.
#      @Distribution.register_cell(tbl_name, row_id, col_id) ->

# TBD: If deps lack class name, use class name of target attribute
#      Possibly "Field" should be default class of target attribute?
@SmartDefault.register("Field.WOR-MEAN", ["age"])
def wor_mean_dist(age):
    return # something

@SmartDefault.register("Field.WOR-SD", ["age"])
def wor_sd_dist(age):
    return # something

@Distribution.register("Field.WOR", ["WOR-MEAN", "WOR-SD"])
def wor_dist(mean, stdev):
    return get_frozen_rv('normal', mean=mean, stdev=stdev)


