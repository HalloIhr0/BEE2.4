from __future__ import annotations

from uuid import UUID

import attrs
from srctools import Property, bool_as_int
from srctools.dmx import Attribute as DMAttribute, Element, ValueType

from consts import UUID_PORTAL2, PALETTE_FORCE_SHOWN as FORCE_SHOWN
from BEE2_config import GEN_OPTS as LEGACY_CONF
import config


@config.APP.register
@attrs.frozen(slots=False)
class PaletteState(config.Data, conf_name='Palette', palette_stores=False):
    """Data related to palettes which is restored next run.

    Since we don't store in the palette, we don't need to register the UI callback.
    """
    selected: UUID = UUID_PORTAL2
    save_settings: bool = False
    hidden_defaults: frozenset[UUID] = attrs.Factory(frozenset)

    @classmethod
    def parse_legacy(cls, conf: Property) -> dict[str, PaletteState]:
        """Convert the legacy config options to the new format."""
        # These are all in the GEN_OPTS config.
        try:
            selected_uuid = UUID(hex=LEGACY_CONF.get_val('Last_Selected', 'palette_uuid', ''))
        except ValueError:
            selected_uuid = UUID_PORTAL2

        return {'': cls(
            selected_uuid,
            LEGACY_CONF.get_bool('General', 'palette_save_settings'),
            frozenset(),
        )}

    @classmethod
    def parse_kv1(cls, data: Property, version: int) -> PaletteState:
        """Parse Keyvalues data."""
        assert version == 1
        hidden = {
            UUID(hex=prop.value)
            for prop in data.find_all('hidden')
        }
        try:
            uuid = UUID(hex=data['selected'])
        except (LookupError, ValueError):
            uuid = UUID_PORTAL2
        hidden.discard(uuid)
        hidden -= FORCE_SHOWN
        return PaletteState(uuid, data.bool('save_settings', False), frozenset(hidden))

    def export_kv1(self) -> Property:
        """Export to a property block."""
        prop = Property('', [
            Property('selected', self.selected.hex),
            Property('save_settings', bool_as_int(self.save_settings)),
        ])
        for hidden in self.hidden_defaults:
            prop.append(Property('hidden', hidden.hex))
        return prop

    @classmethod
    def parse_dmx(cls, data: Element, version: int) -> PaletteState:
        """Parse DMX data."""
        try:
            uuid = UUID(bytes=data['selected'].val_bytes)
        except (LookupError, ValueError):
            uuid = UUID_PORTAL2
        hidden: set[UUID]
        try:
            hidden_arr = data['hidden'].iter_bytes()
        except KeyError:
            hidden = set()
        else:
            hidden = {UUID(bytes=byt) for byt in hidden_arr}
            hidden.discard(uuid)
            hidden -= FORCE_SHOWN

        return PaletteState(
            uuid,
            data['save_settings'].val_bool,
            frozenset(hidden),
        )

    def export_dmx(self) -> Element:
        """Export to a DMX."""
        elem = Element('Palette', 'DMElement')
        elem['selected'] = self.selected.bytes
        elem['save_settings'] = self.save_settings
        elem['hidden'] = hidden = DMAttribute.array('hidden', ValueType.BINARY)
        for uuid in self.hidden_defaults:
            hidden.append(uuid.bytes)
        return elem
