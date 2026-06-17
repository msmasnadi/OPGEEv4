# OPGEE v4

**Oil Production Greenhouse gas Emissions Estimator (OPGEE)** — a Python package for life-cycle
assessment (LCA) of oil and gas fields. OPGEEv4 translates a physical description of fields,
processes, and material/energy streams (in XML) into a runnable model that computes energy use,
greenhouse gas emissions, and carbon intensity (CI).

- **Source code repository:** https://github.com/msmasnadi/OPGEEv4
- **Documentation:** https://opgee.readthedocs.io/
- **License:** see [License](#license) below and `LICENSE.txt`

---

## Contents of this package

| Item | Location |
|------|----------|
| Source code | `opgee/` Python package |
| Command-line tool | `opg` (installed via `pip install -e .`) |
| Default LCA model and lookup tables | `opgee/etc/`, `opgee/tables/` |
| Demo dataset (single oil field) | `demo/demo_model.xml` |
| Demo run scripts | `demo/run_demo.sh`, `demo/run_demo.ps1` |
| Full documentation source | `docs/` |

---

## 1. System requirements

### Operating systems

OPGEEv4 has been developed and tested on:

| OS | Versions tested |
|----|-----------------|
| Microsoft Windows | Windows 10, Windows 11 |
| macOS | 12 (Monterey) and later |
| Linux | Ubuntu 20.04+, other x86_64 distributions |

### Python

| Component | Version |
|-----------|---------|
| Python | **3.11** (recommended; see `py3-opgee.yml`) |
| Python (CI-tested) | 3.9–3.11 |

Python 3.12+ is not currently supported by all pinned dependencies.

### Software dependencies

All dependencies are listed in `requirements.txt` (generated from `requirements.in`).
Key packages and pinned versions:

| Package | Version |
|---------|---------|
| chemicals | 1.2.0 |
| dash | 2.18.1 |
| dask | 2024.11.2 |
| fluids | 1.0.27 |
| lxml | 5.3.0 |
| networkx | 3.4.2 |
| numpy | 1.26.4 |
| pandas | 2.2.3 |
| pint | 0.24.4 |
| scipy | 1.14.1 |
| thermo | 0.3.0 |
| thermosteam | 0.46.0 |

The complete list is in `requirements.txt`. Anaconda/Miniconda (or Miniforge) is the
recommended way to install dependencies; see `py3-opgee.yml`.

### Hardware

No special hardware is required. A standard desktop or laptop with at least **4 GB RAM**
and **2 CPU cores** is sufficient for single-field runs. Large Monte Carlo studies or
multi-field batches benefit from additional cores and memory; optional SLURM cluster
support is available for HPC environments.

### Versions tested

| Platform | Python | OPGEE version |
|----------|--------|---------------|
| Windows 10/11 | 3.11 | 4.0+ |
| macOS | 3.11 | 4.0+ |
| Ubuntu (GitHub Actions) | 3.9, 3.11 | 4.0+ |

---

## 2. Installation guide

### Prerequisites

Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or
[Anaconda](https://www.anaconda.com/download) for your platform.

### Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/msmasnadi/OPGEEv4.git
   cd OPGEEv4
   ```

2. **Create the conda environment** (recommended)

   ```bash
   conda env create -f py3-opgee.yml
   conda activate opgee
   ```

3. **Install OPGEE in editable mode**

   ```bash
   pip install -e .
   ```

4. **Verify installation**

   ```bash
   opg --help
   ```

   You should see the `opg` subcommand list (`run`, `gui`, `graph`, `gensim`, etc.).

### Typical install time

On a normal desktop computer with a broadband connection:

| Step | Approximate time |
|------|------------------|
| Clone repository | < 1 minute |
| `conda env create` | 5–15 minutes |
| `pip install -e .` | < 1 minute |
| **Total** | **~6–16 minutes** |

Times depend on network speed and whether conda packages are cached locally.

### Alternative installation (pip only)

If you already have Python 3.11 with scientific packages installed:

```bash
pip install -r requirements.txt
pip install -e .
```

Using the conda environment file is preferred because it resolves binary dependencies
(e.g. `lxml`, `numba`) reliably across platforms.

---

## 3. Demo

The `demo/` directory contains a small, real OPGEE model describing one onshore oil field
(AES-E1, Egypt) with water reinjection and crude-oil stabilization. The model merges with
the built-in default model (`opgee/etc/opgee.xml`) at run time.

### Instructions to run on demo data

**Option A — bundled demo model (recommended for reviewers)**

```bash
conda activate opgee
cd OPGEEv4

# Linux / macOS
bash demo/run_demo.sh

# Windows PowerShell
powershell -File demo/run_demo.ps1

# Or run directly:
opg run -m demo/demo_model.xml -a demo -o demo/output --cluster-type serial
```

**Option B — built-in example (no extra input files)**

```bash
opg run -a example -o demo/output_builtin --cluster-type serial
```

This runs the pre-defined `gas_lifting_field` analysis from the default model.

### Expected output

After a successful run, the output directory contains CSV files. The primary result is
`carbon_intensity.csv`, with columns including:

| Column | Description |
|--------|-------------|
| `analysis` | Analysis name (`demo` or `example`) |
| `field` | Field name |
| `node` | System boundary or process node |
| `CI` | Carbon intensity (g CO₂-eq / MJ) |
| `unit` | Unit string for CI |

Example structure (values are illustrative; exact numbers depend on model version):

```csv
analysis,field,trial,name,value,unit,node
demo,demo-field,,CI,12.34,grams/MJ,TOTAL
demo,demo-field,,CI,10.11,grams/MJ,Production
...
```

Additional files may be written when detailed results are requested (`-r detailed`):

- `energy_use.csv` — energy consumption by process
- `emissions.csv` — emissions by process and gas species
- `gases.csv`, `streams.csv` — detailed flows

### Expected run time for demo

On a normal desktop computer (Intel Core i5 / Apple M1 class, single field, serial mode):

| Demo | Approximate time |
|------|------------------|
| `demo/demo_model.xml` (1 field) | 10–60 seconds |
| Built-in `example` analysis (1 field) | 10–60 seconds |

---

## 4. Instructions for use

### Running on your own data

1. **Prepare a model XML file** describing your field(s). Start from `opgee/etc/opgee.xml`
   or `demo/demo_model.xml`. Fields typically use `modifies="template"` and override
   attributes with `<A name="...">value</A>` elements. See the
   [XML format documentation](https://opgee.readthedocs.io/en/latest/opgee-xml.html).

2. **Define an analysis** that references your field(s) via `<FieldRef>`:

   ```xml
   <Analysis name="my-study">
     <A name="functional_unit">oil</A>
     <FieldRef name="my-field"/>
   </Analysis>
   ```

3. **Run the model:**

   ```bash
   opg run -m path/to/my_model.xml -a my-study -o results/ --cluster-type serial
   ```

   By default, your XML is merged with the built-in model. Use `--no-default-model` only
   if your file is fully self-contained.

4. **Inspect results** in `results/carbon_intensity.csv` and related CSV files.

5. **Optional — graphical interface:**

   ```bash
   opg gui -m path/to/my_model.xml
   ```

   Opens a browser-based GUI at http://127.0.0.1:8050 for viewing the process network,
   editing parameters, and running the model interactively.

### Other common workflows

| Task | Command |
|------|---------|
| Run multiple fields in parallel | `opg run -a my-study -o results/ -c dask` |
| Monte Carlo simulation | `opg gensim` then `opg run` with MCS options (see docs) |
| Merge XML model files | `opg merge file1.xml file2.xml -o merged.xml` |
| Convert CSV field data to XML | `opg csv2xml fields.csv -o fields.xml` |
| View process network graph | `opg graph --field my-field` |

Full subcommand reference: https://opgee.readthedocs.io/en/latest/opg.html

### (Optional) Reproduction instructions

To reproduce quantitative results reported in the accompanying manuscript:

1. Install OPGEE as described in [Section 2](#2-installation-guide).
2. Obtain the manuscript model XML file(s) and any supplementary CSV inputs from the
   manuscript supplementary data (or from the authors upon request).
3. Run the analysis named in the manuscript, for example:

   ```bash
   opg run -m manuscript_model.xml -a MANUSCRIPT_ANALYSIS -o reproduction/ --cluster-type serial
   ```

4. Compare `reproduction/carbon_intensity.csv` against published tables/figures.

For Monte Carlo results, use the `gensim` subcommand to generate trial XML files from
parameter distributions, then run with the appropriate `--num-trials` and cluster options.
See https://opgee.readthedocs.io/en/latest/monte-carlo.html.

> **Note:** Update the analysis name, model file path, and supplementary data location
> to match your manuscript before submission.

---

## License

OPGEE is distributed under the terms in **`LICENSE.txt`** (Stanford University open
redistribution license). Software may be downloaded, modified, and redistributed free
of charge subject to the conditions in that file, including retention of copyright notices
and notification to the OPGEE maintainers.

Portions of the code derived from [pygcam](https://github.com/rjplevin/pygcam) are
additionally available under the [MIT License](https://opensource.org/licenses/MIT).

For Nature submission: this license permits free academic use and redistribution with
attribution. Contact Adam Brandt (abrandt@stanford.edu) regarding commercial use or
endorsement questions.

---

## Code functionality in the manuscript

A complete description of OPGEE's algorithms and process logic is provided in the
accompanying manuscript:

| Item | Location in manuscript |
|------|------------------------|
| Model overview and carbon-intensity calculation | **Methods** section |
| Process equations and pseudocode | **Methods** section |
| Software architecture | **Methods** section and/or **Supplementary Information** |

> **Action for authors:** Replace the rows above with the exact section numbers/titles
> from your submitted manuscript before completing the Nature editor form.

Additional technical documentation:

- Architecture: https://opgee.readthedocs.io/en/latest/architecture.html
- Calculation of CI: https://opgee.readthedocs.io/en/latest/calculation.html
- Process implementations: `opgee/processes/` (Python source)

---

## Citation

If you use OPGEE in published research, please cite the accompanying Nature manuscript
and this software repository:

```
[Authors]. OPGEEv4: Oil Production Greenhouse gas Emissions Estimator, version 4.
https://github.com/msmasnadi/OPGEEv4
```

---

## Contact

- **Repository issues:** https://github.com/msmasnadi/OPGEEv4/issues
- **OPGEE project:** https://eao.stanford.edu/research-areas/opgee

---

## Release notes

### Version 4.1.0 (2024-03-11)

- Improved performance
- Merged `run`, `runsim`, and `runmany` into a unified `run` command
- Updated model XML format (`<FieldRef>` inside `<Analysis>`)

### Version 4.0.0-alpha.0 (2022-03-01)

- First public alpha release
