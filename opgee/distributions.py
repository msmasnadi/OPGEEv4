#
# Default parameter distributions. User can redefine distributions for any attribute,
# overriding the defaults defined here.
#
from scipy.stats import lognorm, triang, uniform, norm
from smart_defaults import Distribution, SmartDefault

# TBD: How to handle distributions on tabular data?
#      Define an attribute that's set from a cell in a table? Cumbersome.
#      @Distribution.register_cell(tbl_name, row_id, col_id) ->

# TBD: If deps lack class name, use class name of target attribute
#      Possibly "Field" should be default class of target attribute?
@SmartDefault.register("Field.WOR-MEAN", deps=["age"])
def wor_mean_dist(age):
    return # something

@SmartDefault.register("Field.WOR-SD", deps=["age"])
def wor_sd_dist(age):
    return # something

@Distribution.register("Field.WOR", deps=["WOR-MEAN", "WOR-SD"])
def wor_dist(mu, sd):
    return norm(loc=mu, scale=sd)


