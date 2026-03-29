# Good Big Example Service

This directory mirrors `big_example`, but restructures imports around a small
set of package-level entry points so the dependency graph demonstrates lower
coupling.

## Structure

- `domine`: Contains the domain models for the service.
- `entities.py`: Re-exports domain entities through one public package boundary.
- `repo`: Contains the repository classes for accessing the domain models.
- `service`: Contains the service classes that implement the business logic.
- `application.py`: Wires creation use cases behind a single entry point.
- `reporting.py`: Wires reporting use cases behind a single entry point.
- `data`: Contains sample data files.
- `docs`: Contains documentation.
- `complex_logic`: Contains heavier modules that now depend on package-level APIs
  instead of many concrete modules.
- `main.py`: The entry point for the application.
- `config.py`: Configuration settings.
- `utils.py`: Utility functions.
