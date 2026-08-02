# LEFX Schema V2

Status: implemented architecture baseline in the isolated V2 experiment

## 1. Goal

LEFX V2 defines States, Overlays and Events as separate, strictly validated
domain types. The controller knows their lifecycle contracts, but it does not
know the application-specific meaning of individual definitions.

The V2 design intentionally breaks with LEFX V1 where a generic effect could
change its meaning through a preset, target layer, duration or command.

## 2. Vocabulary

### LEFX artifact

An immutable distribution package containing exactly one complete visual
definition, its rendering code, metadata, schemas, assets and optional presets.

### Definition

The immutable description of exactly one State, Overlay or Event. A definition
contains schemas and defaults, but no active runtime state.

### Preset

A named configuration of the definition contained in the same LEFX artifact.
A preset cannot change the definition type, overlay mode or layer group.

### Request

A validated request to set, update, clear or emit a definition.

### Instance

A running definition with resolved configuration, runtime inputs and lifecycle
state.

### Runtime input

Mutable data supplied while an instance is active, such as progress, azimuth
or speech activity. Runtime inputs are separate from configuration parameters.

## 3. Definition types

### State

- Represents a visual base mode.
- Runs indefinitely until replaced or cleared.
- Can be placed only in the background or application State slot.
- Must not declare a finite duration.
- Does not receive mutable external runtime inputs.

### Overlay

- Represents current functional information over a State.
- Has exactly one lifecycle mode:
  - `controlled`: set, updated through a channel and explicitly cleared.
  - `timed`: set once and automatically cleared after a finite duration.
- Can be placed only in the matching internal Overlay slot.
- Controlled Overlays require a channel.
- Timed Overlays require a finite duration.

### Event

- Represents a single occurrence.
- Is always finite.
- Is emitted once and cannot be updated after activation.
- Uses the Event queue and the highest layer group.
- Requires a finite duration.

## 4. Removed V1 concepts

- No generic definition that can become multiple types.
- No public `MAIN_LAYER`.
- No preset category named `effect`.
- No target layer in a preset.
- No embedded application command registry.
- No controller branch based on concrete definition IDs.
- No effect-specific defaults or color choices in input normalization.

## 5. Package ownership

Each LEFX artifact owns:

- its complete visual and animation logic
- parameter and runtime-input semantics
- defaults and embedded presets
- assets and metadata

The controller owns:

- validated request dispatch
- type lifecycle
- internal layer placement
- composition and hardware output

Integrations own:

- hardware and external data acquisition
- application-specific mappings and aliases

LEFX code may depend only on the versioned LEFX SDK and explicitly allowed
standard-library modules. It must not import controller services, registries,
other LEFX artifacts or application-specific helpers.

## 6. Identifiers

- Definition and preset local IDs share one globally unique public namespace.
- Canonical user-facing identifiers are the short local IDs.
- Qualified `<source_id>::<local_id>` identifiers remain accepted for explicit
  source references and diagnostics.
- Definition package IDs are accepted as exact aliases.
- Overlay channels form a separate runtime namespace.
- Fuzzy matches are suggestions only and are never executed automatically.

## 7. Parameters and runtime inputs

Every value is declared by a strict schema. Unknown fields are rejected.

Configuration resolution order:

1. definition defaults
2. selected embedded preset
3. explicit request configuration

The resolved configuration is validated before an instance is changed.

Runtime inputs:

- use a separate schema and payload
- cannot overwrite configuration values
- are allowed only for controlled Overlays
- are immutable for Events and timed Overlays after activation

Declared aliases are accepted only at the validation boundary. Internal
configuration and runtime inputs always use canonical field names. Supplying a
canonical field together with one of its aliases is an error.

### Standard visual fields

- Every colored definition declares `brightness` as a float from `0.0` to
  `1.0`.
- Every animated definition declares `speed` as a multiplier. `1.0` is the
  definition's authored baseline.
- Every directional definition declares boolean `reverse`.
- Angles use `direction_deg`; progress values use `progress` from `0.0` to
  `100.0`.

The declared color model is exactly one of:

- `none`
- `mono` with `color`
- `dual` with `color` and `secondary_color`
- `palette` with `colors`
- `gradient` with ordered `{at, color}` stops including `0.0` and `1.0`
- `random_range` with a bounded HSV `color_range` and `random_seed`

The composition mode is declared independently as `opaque` or `transparent`.

### Controlled Overlay sampling and health

Controlled Overlays declare an input mode:

- `push`: an external integration updates a channel.
- `pull`: the package instance implements `sample_inputs`; `interval_ms: 0`
  samples once per rendered frame.

The default heartbeat window is `1000 ms` with three allowed missed windows.
Each successful pull result and each push update, including an empty update,
refreshes the engine-owned receipt timestamp. The last valid values remain
effective during the grace period. At `3000 ms` without a heartbeat the input
health becomes `failed` and the renderer receives `None` for each declared
runtime input. The definition owns the visual response to that condition.

## 8. Value normalization

System boundaries accept documented, unambiguous convenience forms. Internal
runtime values are canonical and typed.

Examples:

- colors: `#00FF00`, `0x00FF00`, `green`, `gruen`, `grün`,
  and other explicit aliases
- durations: `1500ms`, `1.5s`
- ratios: `0.5`, `50%`
- angles: `90`, `90deg`
- CLI booleans: `true/false`, `on/off`, `an/aus`, `ja/nein`

Case, surrounding whitespace and explicitly registered aliases may be
normalized. Ambiguous or unknown input is rejected with structured
suggestions.

## 9. Controller actions

The canonical CLI grammar is:

```text
ledctl <verb> <object> [target] [options]
```

The mutation vocabulary is deliberately small:

```text
ledctl set state <id-or-preset>
ledctl clear state

ledctl set overlay <id-or-preset> --channel <name>
ledctl update overlay <channel>
ledctl clear overlay <channel>

ledctl emit event <id-or-preset>
```

`apply`, `open`, `close` and `play` are not separate V2 verbs.

Safe shorthand may omit an object only when the verb and exact target resolve
to one valid type:

```text
ledctl set <state-id-or-preset>
ledctl set <overlay-id-or-preset> --channel <name>
ledctl update <overlay-channel>
ledctl clear <overlay-channel>
ledctl emit <event-id-or-preset>
```

The CLI reports the canonical spelling after accepting a shorthand.

## 10. Activation mode

For State and controlled Overlay actions:

- no mode or `--on`: ensure the requested target is active
- `--off`: ensure the requested target is inactive
- `--toggle`: explicitly toggle the target

The HTTP API exposes equivalent explicit `on`, `off` and `toggle` operations.
A bare `set` operation means `on`, never an implicit toggle. This keeps `set`
idempotent and safe for retries.

Events do not support `on`, `off` or `toggle`.

## 11. Read operations

Collection endpoints return identifier lists by default, not complete schemas.

Default example:

```json
["fill_ring", "rotating_segment", "yin_yang_spin"]
```

Read vocabulary:

```text
ledctl list states
ledctl list overlays
ledctl list events
ledctl list presets
ledctl show <id-or-preset>
```

CLI output:

- default list: one identifier per line
- `--json`: compact machine-readable JSON
- `--details`: complete metadata for every listed item
- `show`: complete detail JSON for one item

API output:

- collection endpoint: identifier list
- `?details=true`: complete items
- item endpoint: complete metadata
- item `/schema`: parameter and runtime-input schemas
- item `/presets`: embedded presets

## 12. Validation invariants

1. One artifact contains exactly one definition of exactly one type.
2. State definitions are indefinite.
3. Overlay definitions declare exactly one overlay mode.
4. Timed Overlays and Events have a valid finite duration.
5. Presets cannot change type, mode or internal layer placement.
6. Every parameter and runtime input is declared and type-valid.
7. Unknown fields are rejected.
8. Definition and preset identifiers cannot collide anywhere in the registry.
9. The controller never selects behavior by concrete definition ID.
10. Invalid requests change no runtime state.
11. LEFX Sets aggregate LEFX artifacts and add no domain behavior.
12. Build sources never live below a disposable build-output directory.
13. A source contains exactly one local `BaseEffect` implementation.
14. A source cannot contain a generic `common.py` or import controller,
    service, registry or another definition.
15. Source folder, definition ID and State/Overlay/Event type agree.

## 13. Implemented HTTP operations

```text
GET  /api/v2/states
GET  /api/v2/overlays
GET  /api/v2/events
GET  /api/v2/presets
GET  /api/v2/show/{target}

POST /api/v2/set/state
POST /api/v2/clear/state
POST /api/v2/set/overlay
POST /api/v2/update/overlay
POST /api/v2/clear/overlay
POST /api/v2/emit/event
```

Mutation payloads separate `config` and `inputs`. State and controlled Overlay
set requests use explicit `action: on|off|toggle`; the default is `on`.

## 14. Implementation status

Completed in the experiment:

1. Strict type, lifecycle, parameter and runtime-input validation.
2. `lefx/2` and `lefxset/2` build, load, inspect and verify paths.
3. All first-party definitions classified as State, controlled/timed Overlay,
   or Event.
4. Typed runtime set/update/clear/emit operations.
5. Compact V2 catalog API and verb-first CLI, including safe shorthand.
6. English/German color aliases and boundary value normalization.
7. Removal of embedded commands, public `MAIN_LAYER`, V1 preset lifecycle
   fields and `src/engine/normalization.py`.
8. Application-specific mappings isolated in
   `src/integrations/application_commands.py`.
9. Standard `.lefx`/`.lefxset` build and smoke rendering for all definitions.
10. Thirty-seven autonomous first-party sources under typed
    `sources/states`, `sources/overlays` and `sources/events` directories.
11. Strict color, brightness, speed, direction, alias, gradient and random
    color-range validation.
12. Push/Pull input sampling with engine-owned heartbeat diagnostics and
    three-window failure handling.
13. Removal of the old shared `effect_definitions` and duplicated
    `sorted_by_type` trees after migration of the unique
    `doa_activity_indicator`.

Still intentionally outside this implementation:

- The ReSpeaker hardware already runs the new firmware that decouples DOA
  values from its internal LED effect. Integrating and validating the live USB
  update stream end to end remains separate from the LEFX V2 implementation.
- Migration strategy for existing third-party `lefx/1` artifacts. V2 rejects
  them rather than guessing a conversion.
- Decision whether the remaining application-specific V1 service callbacks
  should be removed or kept as an integration compatibility surface.
