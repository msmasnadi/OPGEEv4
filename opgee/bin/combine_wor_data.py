import pandas as pd

etc_dir = '/Users/rjp/repos/OPGEEv4/opgee/mcs/etc/'

norway_csv = etc_dir + 'Norway_historical_WOR.csv'
uk_csv = etc_dir + 'UK_Results_MATLAB.csv'
orig_csv = etc_dir + 'WOR_observations_long.csv'

norway_df = pd.read_csv(norway_csv)
norway_df.drop('year', axis='columns', inplace=True)

uk_df = pd.read_csv(uk_csv)
orig_df = pd.read_csv(orig_csv)

all = pd.concat([orig_df, norway_df, uk_df], axis="rows").dropna(axis='rows')
all = all.query("WOR > 0") # drop any remaining rows with zero or negative values for WOR

all_csv = etc_dir + 'all_wor.csv'
all.to_csv(all_csv, index=False)
