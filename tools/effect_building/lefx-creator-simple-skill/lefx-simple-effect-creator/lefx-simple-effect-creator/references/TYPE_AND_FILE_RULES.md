# Typ-, Lebenszyklus- und Dateiregeln

## Typentscheidung

### State

Verwenden, wenn der Effekt unbestimmt als Grundzustand läuft.

Vertrag:

- `definition_type=DefinitionType.STATE`
- kein `overlay_mode`
- keine endliche Dauer
- keine veränderlichen Runtime-Eingaben
- Layer: `BACKGROUND_STATE_LAYER` und/oder `STATE_LAYER`
- Playback: `LOOP` und gegebenenfalls `PERSISTENT`
- Lebensdauer: `requires_indefinite_duration=True`

Typischer Aufbau:

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
    restorable=True,
),
layer_rules={
    LayerId.BACKGROUND_STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
        requires_indefinite_duration=True,
        persistent_storage=True,
    ),
    LayerId.STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
        requires_indefinite_duration=True,
    ),
},
```

`persistent_storage=True` gehört nur zur Background-State-Regel.

### Timed Overlay

Verwenden, wenn die Einblendung nach einer beim Aktivieren bekannten Dauer
automatisch endet.

Vertrag:

- `definition_type=DefinitionType.OVERLAY`
- `overlay_mode=OverlayMode.TIMED`
- `duration_ms` oder `total_ms` im `parameter_schema`
- keine veränderlichen Runtime-Eingaben
- Layer: `TEMP_OVERLAY_LAYER`
- Playback: `SINGLE_RUN`
- Lebensdauer: `requires_finite_duration=True`
- häufig `composition=CompositionMode.TRANSPARENT`

Typischer Aufbau:

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.SINGLE_RUN,),
    supports_transparency=True,
    supports_duration_override=True,
),
layer_rules={
    LayerId.TEMP_OVERLAY_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
        requires_finite_duration=True,
        allows_transparency=True,
    ),
},
```

### Event

Verwenden, wenn ein kurzes, priorisiertes Einmalsignal abgespielt wird.

Vertrag:

- `definition_type=DefinitionType.EVENT`
- kein `overlay_mode`
- `duration_ms` oder `total_ms` im `parameter_schema`
- keine veränderlichen Runtime-Eingaben
- Layer: `EVENT_LAYER`
- Playback: `SINGLE_RUN`
- Queue: `QueueMode.PRIORITY_FIFO`
- Lebensdauer: `requires_finite_duration=True`

Typischer Aufbau:

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.SINGLE_RUN,),
    supports_duration_override=True,
    supports_queueing=True,
),
layer_rules={
    LayerId.EVENT_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
        requires_finite_duration=True,
        queue_mode=QueueMode.PRIORITY_FIFO,
    ),
},
```

## Quelldateien

### `effect.yaml`

Beispiel:

```yaml
package_id: my-effects.rotating_segment
source_id: my-effects
entry_file: effect.py
entry_class: RotatingSegmentState
min_service_version: 1.0.0
```

Titel, Beschreibung, Parameter und Typ werden nicht im Manifest dupliziert.
Sie stehen in `EffectDefinition`.

### `effect.py`

Muss genau eine lokal definierte `BaseEffect`-Unterklasse enthalten.
Paketlokale Hilfsmodule sind erlaubt; eine generische `common.py` ist nicht
erlaubt.

### `presets.yaml`

Beispiel:

```yaml
presets:
  rotating_segment_calm:
    title: Rotating Segment Calm
    description: Langsame und gedämpfte Variante.
    params:
      color: "#4A7BFF"
      background_color: "#020814"
      brightness: 0.45
      speed: 0.7
      segment_length: 4
      reverse: false
    tags:
      - calm
```

Presets enthalten ausschließlich Werte aus `parameter_schema`.

## IDs

- Definition-ID: kurze globale ID, `snake_case`.
- Source-ID: Quellenraum, zum Beispiel `default-effects`.
- Package-ID: gewöhnlich `<source_id>.<effect_id>`.
- Preset-ID: global eindeutig und aussagekräftig.

Vor dem Erstellen nach Definition- und Preset-ID suchen.
