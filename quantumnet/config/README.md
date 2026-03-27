Configuration assets for QuantumNet.

- `config.py`: dataclasses and `SimulationConfig`.
- `default_config.yaml`: default GUI/CLI configuration file.
- `default_topology.json`: default GUI topology editor file.
- JSON topology files can also be stored here and referenced from:
  - `topology.name: Json`
  - `topology.args: ["my_topology.json"]`

When loading from this default YAML, relative JSON topology paths are resolved
from this same folder.
