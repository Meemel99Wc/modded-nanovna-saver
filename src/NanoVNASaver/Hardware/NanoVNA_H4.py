#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging

from .NanoVNA_H import NanoVNA_H
from .Serial import Interface

logger = logging.getLogger(__name__)


LITEVNA64_MAX_FREQ_HZ = 6300e6


class NanoVNA_H4(NanoVNA_H):
    name = "NanoVNA-H4"
    screenwidth = 480
    screenheight = 320
    valid_datapoints: tuple[int, ...] = (
        101,
        11,
        51,
        201,
        401,
    )

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_hz = 1500e6
        if self._is_litevna64_firmware():
            # Missing Link firmware (litevna-openvna) answers as
            # "NanoVNA-H 4 compatible, LiteVNA64 hardware"; the hardware
            # sweeps up to 6.3 GHz. Real NanoVNA-H 4 stays at 1.5 GHz.
            self.sweep_max_freq_hz = LITEVNA64_MAX_FREQ_HZ
        self.sweep_method = "scan"
        if "Scan mask command" in self.features:
            self.sweep_method = "scan_mask"

    def _is_litevna64_firmware(self) -> bool:
        try:
            info = " ".join(self.exec_command("info"))
        except Exception:  # serial trouble: keep the safe 1.5 GHz limit
            logger.warning("Could not read info for LiteVNA64 detection")
            return False
        return "LiteVNA64" in info
