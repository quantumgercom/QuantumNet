## GUI Architecture

This package is organized by responsibility so new features can be added without creating large page files.

- `core/`: shared infrastructure used across pages.
  - `config.py`: config path resolution and YAML load/save.
  - `layout.py`: global page setup and common UI controls.
- `pages/`: page routing and top-level page composition.
  - `navigation.py`: central page registration for Streamlit navigation.
- `parameters/`: domain logic for the Parameters feature.
  - `field_metadata.py`: labels/options/help metadata.
  - `validation.py`: domain-specific validation and sanitizers.
  - `sections.py`: Streamlit sections used by the parameters form.

## Adding a new feature

1. Create a feature package under `gui/` (for example, `gui/topology/`).
2. Keep feature-specific validation, metadata, and section renderers in that package.
3. Add a page renderer under `gui/pages/`.
4. Register the page in `gui/pages/navigation.py`.

## Backward compatibility

Legacy modules (`config_io.py`, `ui.py`, `constants.py`, `validation.py`) are compatibility wrappers that re-export the new modules.
