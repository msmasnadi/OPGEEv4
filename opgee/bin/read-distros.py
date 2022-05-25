import pandas as pd

df = pd.read_csv('/Users/rjp/Projects/OPGEE Python/parameter_distributions.csv').fillna('')

# See https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.truncnorm.html

for row in df.itertuples(index=False, name='row'):
    shape = row.distribution_type
    name = row.variable_name
    low = row.low_bound
    high = row.high_bound
    mean = row.mean
    stdev = row.SD
    default = row.default_value
    prob_of_yes = row.prob_of_yes

    if low == '' and high == '' and mean == '' and prob_of_yes == '':
        print(f"{name} depends on other distributions / smart defaults")

    elif shape == 'Binary':
        if prob_of_yes == 0 or prob_of_yes == 1:
            print(f"* Ignoring distribution on {name}, Binary distribution has prob_of_yes = {prob_of_yes}")
        else:
            print(f"{name} = weighted_binary(prob_of_one={prob_of_yes})")

    elif shape == 'Uniform':
        if low == high:
            print(f"* Ignoring distribution on {name}, Uniform high and low bounds are both {low}")
        else:
            print(f"{name} = uniform({low}, {high})")

    elif shape == 'Triangular':
        print(f"{name} = triangular({low}, {default}, {high})")

    elif shape == 'Normal':
        if stdev == 0.0:
            print(f"* Ignoring distribution on {name}, Normal has stdev = 0")
        else:
            print(f"{name} = normal({mean}, {stdev}, minimum={low}, maximum={high})")

    elif shape == 'Lognormal':
        # Uses mean and stdef of underlying normal, not of the lognormal
        print(f"{name} = lognormal({mean}, {stdev})")

    else:
        raise Exception(f"Unknown distribution shape: '{shape}'")
