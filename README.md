# TNSEngineerEdition
This repository contains prototypes, source code, and tests for engineering thesis:  \
**Concurrent interactive simulator of Krakow's tram network**

## Development setup and notes
In order to efficiently and cleanly develop the application, we need to follow a few simple rules.

### Branch names
Branches created in this repository should be named in the following way:

`<author-names>/issue-<issue-numbers>`

The `<author-names>` field should correspond to your GitHub usernames. The names should be ordered alphabetically and be separated with `+` characters.

The `<issue-numbers>` field should correspond to the issues existing in the repository. The numbers should be order in ascending order and be separated with `-` characters.

Examples of correct branch names:
```
RCRalph/issue-41
Codefident+RCRalph/issue-341
olobuszolo+Redor114/issue-412-432
Codefident+olobuszolo+RCRalph+Redor144/issue-653-5422-543346
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
pip install -r dev-requirements.txt
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
