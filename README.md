# DREEM
Prof. Silvi Rouskin's [DREEM algorithm](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7310298/).

## Installation

### Conda Install

Trying to get a conda-able install script

With an `env.yml` like this

```
channels:
 - conda-forge
 - bioconda
 - defaults
dependencies:
# - bowtie2=2.5.0
# - fastqc=0.11.9
 - python=3.11
# - trim-galore=0.6.7
 - pip
 - pip:
#   - dreem @ git+https://github.com/yvesmartindestaillades/dreem.git
   - dreem @ git+https://github.com/cjgunnar/dreem_yves_martin
```

Create environment

```
conda env create -n dreem_yves --file env.yml && \
conda activate dreem_yves
```

### Pip Virtual Env Install

```
cd path/to/where/you/want/dreem
git clone https://github.com/yvesmartindestaillades/dreem
cd dreem
python3 -m venv venv
source bin/activate
pip install -r requirements.txt
pip install .
```


## Contributors
- Yves Martin
- Scott Grote 
- Matthew "Matty" Allan
- Albéric de Lajarte
