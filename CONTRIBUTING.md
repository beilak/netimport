# Contributing to NetImport

First off, thank you for considering contributing to NetImport! It's people like you that make open source such a great community.

We welcome any type of contribution, not only code. You can help with:
*   **Reporting a bug**
*   **Discussing the current state of the code**
*   **Submitting a fix**
*   **Proposing new features**
*   **Becoming a maintainer**

## We Use Github Flow

We use Github Flow, so all code changes happen through Pull Requests.
Pull Requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes.
5.  Make sure your code lints.
6.  Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](https://github.com/beilak/netimport/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

*   A quick summary and/or background
*   Steps to reproduce
    *   Be specific!
    *   Give sample code if you can.
*   What you expected would happen
*   What actually happens
*   Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

We use `ruff` to format our code. Please run `poetry run ruff format .` before committing your changes.
We also use `mypy` for static type checking. Please run `poetry run mypy .` to check for type errors.

## Setting up your development environment

1.  Fork the repository and clone it to your local machine.
2.  Install `poetry` if you don't have it already.
3.  Run `poetry install` to create a virtual environment and install the project dependencies.

## Running Tests

To run the test suite, run the following command:
```bash
poetry run pytest
```

## Submitting a Pull Request

When you're ready to submit a pull request, please make sure you have done the following:

1.  Run the test suite and ensure all tests pass.
2.  Run the linter and type checker and ensure there are no errors.
3.  Update the documentation if you have changed any APIs.
4.  Write a clear and descriptive pull request message.

Thank you for your contribution!
