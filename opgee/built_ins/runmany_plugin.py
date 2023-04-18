"""
.. Temporary plugin to run many (e.g., thousands) of fields in parallel using dask.

.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..core import magnitude, Timer
from ..subcommand import SubcommandABC
from ..log import getLogger, setLogFile

_logger = getLogger(__name__)

class Result():
    def __init__(self, analysis_name, field_name, energy_data, emissions_data, error=None):
        self.analysis_name = analysis_name
        self.field_name = field_name
        self.energy = energy_data
        self.emissions = emissions_data
        self.error = error

    def __str__(self):
        return f"<Result analysis:{self.analysis_name} field:{self.field_name} error:{self.error}>"

def total_emissions(proc, gwp):
    rates = proc.emissions.rates(gwp)
    total = rates.loc["GHG"].sum()
    return magnitude(total)

def energy_and_emissions(field, gwp):
    import pandas as pd

    procs = field.processes()
    energy_by_proc = {proc.name: magnitude(proc.energy.rates().sum()) for proc in procs}
    energy_data = pd.Series(energy_by_proc, name=field.name)

    emissions_by_proc = {proc.name: total_emissions(proc, gwp) for proc in procs}
    emissions_data = pd.Series(emissions_by_proc, name=field.name)
    return energy_data, emissions_data

def run_field(analysis_name, field_name, xml_string):
    from ..config import setParam
    from ..model_file import ModelFile

    setParam('OPGEE.XmlSavePathname', '')  # avoid writing /tmp/final.xml since no need

    try:
        mf = ModelFile.from_xml_string(xml_string, add_stream_components=False,
                                       use_class_path=False,
                                       use_default_model=True,
                                       analysis_names=[analysis_name],
                                       field_names=[field_name])

        analysis = mf.model.get_analysis(analysis_name)
        field = analysis.get_field(field_name)

        field.run(analysis)
        energy_data, emissions_data = energy_and_emissions(field, analysis.gwp)
        result = Result(analysis_name, field_name, energy_data, emissions_data)

    except Exception as e:
        result = Result(analysis_name, field_name, None, None, error=str(e))

    return result


def run_parallel(model_xml_file, analysis_name, field_names, max_results=None):
    from dask.distributed import as_completed

    from ..model_file import extracted_model
    from ..mcs.distributed_mcs_dask import Manager

    mgr = Manager(cluster_type='local')

    timer = Timer('run_parallel').start()

    # Put the log for the monitor process in the simulation directory.
    # Workers will set the log file to within the directory for the
    # field it's currently running.
    # log_file = f"{sim_dir}/opgee-mcs.log"
    # setLogFile(log_file, remove_old_file=True)

    # N.B. start_cluster saves client in self.client and returns it as well
    client = mgr.start_cluster()

    futures = []

    # Submit all the fields to run on worker tasks
    for field_name, xml_string in extracted_model(model_xml_file, analysis_name,
                                                  field_names=field_names,
                                                  as_string=True):

        future = client.submit(run_field, analysis_name, field_name, xml_string)
        futures.append(future)

    energy_cols = []
    emission_cols = []
    errors = []

    count = 0   # used if we're returning results in batches

    # Wait for and process results
    for future, result in as_completed(futures, with_results=True):
        if max_results and count == 0:
            energy_cols.clear()
            emission_cols.clear()
            errors.clear()

        if result.error:
            _logger.error(f"Failed: {result}")
            errors.append(result)
        else:
            _logger.debug(f"Succeeded: {result}")

            energy_cols.append(result.energy)
            emission_cols.append(result.emissions)

        if max_results:
            if count == max_results:
                count = 0
                # return the next batch
                yield energy_cols, emission_cols, errors
            else:
                count += 1

    _logger.debug("Workers finished")

    mgr.stop_cluster()
    _logger.info(timer.stop())

    if count:
        yield energy_cols, emission_cols, errors
    else:
        return energy_cols, emission_cols, errors


def run_serial(model_xml_file, analysis_name, field_names):
    from ..model_file import extracted_model

    timer = Timer('run_serial').start()

    energy_cols = []
    emission_cols = []
    errors = []

    for field_name, xml_string in extracted_model(model_xml_file, analysis_name,
                                                  field_names=field_names,
                                                  as_string=True):
        result = run_field(analysis_name, field_name, xml_string)
        if result.error:
            _logger.error(f"Failed: {result}")
            errors.append(result)
        else:
            energy_cols.append(result.energy)
            emission_cols.append(result.emissions)

    _logger.info(timer.stop())
    return energy_cols, emission_cols, errors


class RunManyCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run thousands of fields in parallel using dask.'''}
        super().__init__('runmany', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        parser.add_argument('-a', '--analysis',
                            help='''The name to give the <Analysis> element. Default is the file basename 
                            with the extension removed. Default is the first analyses found in the given 
                            model XML file.''')

        parser.add_argument('-b', '--batch-start', default=0, type=int,
                            help='''The value to use to start numbering batch result files.
                            Default is zero. Ignored unless -N/--save-after is specified.''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help=f'''A comma-delimited list of fields to run. Default is to
                            run all fields indicated in the named analysis.''')

        parser.add_argument('-m', '--model', required=True,
                            help=f'''[Required] The pathname of a model XML file to process.''')

        parser.add_argument('-N', '--save-after', type=int,
                            help='''Write a results to a new file after the given number of results are 
                            returned. Implies --parallel.''')

        parser.add_argument('-n', '--count', type=int, default=0,
                            help='''The number of fields to run from the named analysis.
                            Default is 0, which means run all fields.''')

        parser.add_argument('-o', '--output', required=True,
                            help='''[Required] The pathname of the CSV files to create containing energy and 
                            emissions results for each field. This argument is used as a basename,
                            with the suffix '.csv' replaced by '-energy.csv' and '-emissions.csv' to
                            store the results. Each file has fields in columns and processes in rows.''')

        parser.add_argument('-p', '--parallel', action='store_true',
                            help='''Run the fields in parallel locally using dask.''')

        parser.add_argument('-S', '--start-with',
                            help='''The name of a field to start with. Use this to resume a run after a failure.
                            Can be combined with -n/--count to run a large number of fields in smaller batches.''')

        parser.add_argument('-s', '--skip-fields', action=ParseCommaList,
                            help='''Comma-delimited list of field names to exclude from analysis''')

        return parser

    def run(self, args, tool):
        import os
        import pandas as pd
        from ..config import getParam, setParam, pathjoin
        from ..error import CommandlineError
        from ..model_file import analysis_names, fields_for_analysis

        setParam('OPGEE.XmlSavePathname', '')   # avoid writing /tmp/final.xml since no need

        model_xml_file = args.model

        analysis_name = args.analysis or analysis_names(model_xml_file)[0]
        all_fields = fields_for_analysis(model_xml_file, analysis_name)

        field_names = [name.strip() for name in args.fields] if args.fields else None
        if field_names:
            unknown = set(field_names) - set(all_fields)
            if unknown:
                raise CommandlineError(f"Fields not found in {model_xml_file}: {unknown}")
        else:
            field_names = all_fields

        if args.start_with:
            # skip all before the named field
            i = field_names.index(args.start_with)
            field_names = field_names[i:]

        if args.count:
            field_names = field_names[:args.count]

        skip = args.skip_fields
        if skip:
            field_names = [name.strip() for name in field_names if name not in skip]

        def _save_cols(columns, csvpath):
            df = pd.concat(columns, axis='columns')
            df.index.name = 'process'
            df.sort_index(axis='rows', inplace=True)

            print(f"Writing '{csvpath}'")
            df.to_csv(csvpath)

        def _save_errors(errors, csvpath):
            """Save a description of all field run errors"""
            with open(csvpath, 'w') as f:
                f.write('analysis,field,error\n')
                for result in errors:
                    f.write(f"{result.analysis_name},{result.field_name},{result.error}\n")

        temp_dir = getParam('OPGEE.TempDir')
        dir_name, filename = os.path.split(args.output)
        subdir = pathjoin(temp_dir, dir_name)
        basename, ext = os.path.splitext(filename)

        save_after = args.save_after
        if save_after:
            batch = args.batch_start   # used in naming result files

            for vectors in run_parallel(model_xml_file, analysis_name, field_names,
                                        max_results=save_after):

                energy_cols, emissions_cols, errors = vectors

                _save_cols(energy_cols,    pathjoin(subdir, f"{basename}-energy-{batch}{ext}"))
                _save_cols(emissions_cols, pathjoin(subdir, f"{basename}-emissions-{batch}{ext}"))
                _save_errors(errors,       pathjoin(subdir, f"{basename}-errors-{batch}.csv"))

                batch += 1

        else:
            # If not running in batches, save all results at the end
            run_func = run_parallel if args.parallel else run_serial
            energy_cols, emissions_cols, errors = run_func(model_xml_file, analysis_name,
                                                           field_names)

            # Insert "-energy" or "-emissions" between basename and extension
            _save_cols(energy_cols,    pathjoin(subdir, f"{basename}-energy{ext}"))
            _save_cols(emissions_cols, pathjoin(subdir, f"{basename}-emissions{ext}"))
            _save_errors(errors,       pathjoin(subdir, f"{basename}-errors.csv"))
