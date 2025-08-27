# TNSEngineerEdition - Server
This repository contains source code, and tests for server component of engineering thesis:  \
**Concurrent interactive simulator of Krakow's tram network**

## Defining city configurations
City configurations are by default defined in the `cities` directory in the root of this repository. Inside of this directory there should be multiple directories, names of which specify the city ID. Inside these directories there should be city configurations in the form of JSON files with file names in the form of ISO 8601 format, for example `2025-07-07.json`. These files should contain a valid configuration for a given day, which should contain information specified inside the `CityConfiguration` class.

### Adding or updating configurations
In case you need to update the city configuration, you should create a new file with the name of the current date. This approach helps keeping backup copies of city configurations in case they need to be brought back. The configuration chosen by the server will always be the configuration with the maximal date.

### Example directory structure
```
cities/
├── krakow/
│   ├── 2025-01-18.json
│   ├── 2025-06-13.json
│   └── 2025-07-25.json
└── warsaw/
    ├── 2025-03-05.json
    ├── 2025-05-31.json
    └── 2025-07-01.json
```

## Development setup and notes
In order to efficiently and cleanly develop the application, we need to follow a few simple rules.

### Branch names
Branches created in this repository should be named in the following way:

`<author-names>/<short-description>`

The `<author-names>` field should correspond to your GitHub usernames. The names should be ordered alphabetically and be separated with `+` characters.

The `<short-description>` field should include a summary of the changes.

Examples of correct branch names:
```
RCRalph/added-pre-commit-check
Codefident+RCRalph/server-integration-tests
olobuszolo+Redor114/tram-network-graph-transformation
Codefident+olobuszolo+RCRalph+Redor144/test-cases-for-tram-stop-mapping
```

### Contributing code to main branch
In order to contribute code to the repository's main branch, create a pull request using your newly created branch and assign some reviewers to your code. When the pull request gets an approval from other members of this repository and all CI checks pass (if applicable), you will only then be able to merge it to main.

### Python and VirtualEnv
It is recommended to install Python using [pyenv](https://github.com/pyenv/pyenv). You can download the required Python version and create a virtual environment using the following commands:
```
pyenv install 3.12.8
pyenv virtualenv 3.12.8 tns-engineer-edition
```

Then navigate to repository's root directory and set the newly created virtual environment as local environment:
```
pyenv local tns-engineer-edition
```

Verify that everything is working as expected:
```
> pyenv local
tns-engineer-edition
> python3 -V
3.12.8
> pip freeze # Should be empty
```

If everything is working correctly, install development dependencies (such as pre-commit) by running:
```
pip install -e .[dev]
```

### Pre-commit
Before committing to this repository, the developers should make sure that their code passes all required quality checks. In order to run them automatically, run:
```sh
pre-commit install
```

This command assumes `pre-commit` is available through the currently active Python virtual environment.

### Running GitHub Actions pipelines locally
In order to run pipelines locally, install [act](https://github.com/nektos/act), preferably using GitHub CLI:
```
gh extension install https://github.com/nektos/gh-act
```

You can then run the pipelines using:
```
gh act -P self-hosted=catthehacker/ubuntu:act-22.04
```

You can find more details about running pipelines locally in [act user guide](https://nektosact.com/).
