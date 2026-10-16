import os
from functools import lru_cache
from typing import cast

import hou
import hutil

MENU_CUSTOM_VALUE = 'custom'
MENU_CUSTOM_LABEL = 'Custom'
CUSTOM_PRESETS_PATH = os.path.join(
    hou.homeHoudiniDirectory(), 'meadow_mask_builder_presets.json'
)


@lru_cache(1)
def get_custom_presets() -> dict[str, list[dict]]:
    """Return a dictionary with custom presets."""

    presets = {}
    if os.path.exists(CUSTOM_PRESETS_PATH):
        try:
            presets = hutil.json.loads(hou.readFile(CUSTOM_PRESETS_PATH))
        except hutil.json.JSONDecodeError:
            pass
    return presets


@lru_cache(1)
def get_embedded_presets() -> dict[str, list[dict]]:
    """Return a dictionary with embedded presets."""

    content = hou.readFile("opdef:.?presets.json")
    try:
        presets = hutil.json.loads(content)
    except hutil.json.JSONDecodeError:
        presets = {}
    return presets


def get_presets() -> dict[str, list[dict]]:
    """Return a dictionary with all presets."""

    presets = {}
    presets.update(get_custom_presets())
    presets.update(get_embedded_presets())
    return presets


def get_menu() -> list:
    """Return the menu populated from the presets file."""

    presets = get_presets()

    menu = [MENU_CUSTOM_VALUE, MENU_CUSTOM_LABEL]
    keys = sorted(presets.keys(), key=str.lower)
    for i, preset in enumerate(keys):
        menu.extend((preset, preset.title()))
    return menu


def reload_presets() -> None:
    """Reload preset caches."""

    get_custom_presets.cache_clear()
    get_embedded_presets.cache_clear()


def load_preset(name: str) -> None:
    """Load the preset from a name."""

    presets = get_presets()
    preset = presets.get(name)
    if not preset:
        return

    noises = preset
    count = len(noises)

    node = cast(hou.SopNode, hou.pwd())
    node.parm('noises').set(0)
    node.parm('noises').set(count)

    for j, noise in enumerate(noises):
        i = j + 1

        noise_type = noise.get('noise_type')
        if noise_type is not None:
            node.parm(f'noise_type{i}').set(noise_type)

        op = noise.get('op')
        if op is not None:
            node.parm(f'op{i}').set(op)

        roughness = noise.get('roughness')
        if roughness is not None:
            node.parm(f'roughness{i}').set(roughness)

        scale = noise.get('scale')
        if scale is not None:
            node.parmTuple(f'scale{i}').set(scale)

        keys = noise.get('keys', ())
        values = noise.get('values', ())
        bases = [hou.rampBasis.Linear] * len(keys)
        ramp = hou.Ramp(bases, keys, values)
        hou.parm(f'remap{i}').set(ramp)


def extract_preset() -> list[dict]:
    """Return a preset from current parameter values."""

    node = cast(hou.SopNode, hou.pwd())
    count = node.parm('noises').eval()
    noises = []
    for i in range(1, count + 1):
        ramp = node.parm(f'remap{i}').eval()
        noise_data = {
            'noise_type': node.parm(f'noise_type{i}').eval(),
            'op': node.parm(f'op{i}').eval(),
            'roughness': node.parm(f'roughness{i}').eval(),
            'scale': list(node.parmTuple(f'scale{i}').eval()),
            'keys': list(ramp.keys()),
            'values': list(ramp.values()),
        }
        noises.append(noise_data)
    return noises


def save_preset() -> None:
    """Save the current noises as a preset."""

    status, name = hou.ui.readInput(
        'Preset Name:',
        buttons=('Save', 'Cancel'),
        title='Save Preset',
    )

    if status != 0 or not name.strip():
        return

    embedded_presets = get_embedded_presets()
    if name in embedded_presets:
        hou.ui.displayMessage(
            'Cannot override embedded presets. Please chose another name.',
            severity=hou.severityType.Error,
        )
        return

    custom_presets = get_custom_presets()
    preset = extract_preset()
    custom_presets[name] = preset

    with open(CUSTOM_PRESETS_PATH, 'w') as f:
        f.write(hutil.json.dumps(custom_presets, indent=2))

    node = cast(hou.SopNode, hou.pwd())
    node.parm('presets').set(name)


def delete_preset() -> None:
    """Delete the currently selected preset."""

    node = cast(hou.SopNode, hou.pwd())
    name = node.parm('presets').eval()

    custom_presets = get_custom_presets()
    if name in custom_presets:
        del custom_presets[name]

        with open(CUSTOM_PRESETS_PATH, 'w') as f:
            f.write(hutil.json.dumps(custom_presets, indent=2))

        node.parm('presets').set(MENU_CUSTOM_VALUE)


def attribute_changed() -> None:
    """Handle attribute changes in the noise parameters."""

    node = cast(hou.SopNode, hou.pwd())
    name = node.parm('presets').eval()
    if name != MENU_CUSTOM_VALUE:
        node.parm('presets').set(MENU_CUSTOM_VALUE)
        node.parm('savepreset').disable(False)
        node.parm('deletepreset').disable(True)


def preset_changed() -> None:
    """Handle changing the preset dropdown."""

    node = cast(hou.SopNode, hou.pwd())
    name = node.parm('presets').eval()

    embedded_presets = get_embedded_presets()
    custom_presets = get_custom_presets()
    node.parm('savepreset').disable(name in embedded_presets)
    node.parm('deletepreset').disable(name not in custom_presets)

    load_preset(name)
