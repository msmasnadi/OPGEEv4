from opgee.stream import PHASE_LIQUID, Stream, PHASE_GAS, PHASE_SOLID
import pandas as pd
from statistics import mean
from .thermodynamics import Oil, Gas, Water
from .log import getLogger
from . import ureg

_logger = getLogger(__name__)


class Combine(Stream):

    @classmethod
    def combine_streams(cls, API, streams, temperature=None, pressure=None):
        """
        Thermodynamically combine multiple streams' components into a new
        anonymous Stream. This is used on input streams since it makes no
        sense for output streams.

        :param API:
        :param streams: (list of Streams) the Streams to combine
        :return: (Stream) if len(streams) > 1, returns a new Stream. If
           len(streams) == 1, the original stream is returned.
        """
        if len(streams) == 1:  # corner case
            return streams[0]

        matrices = [stream.components for stream in streams]

        comp_matrix = sum(matrices)
        numerator = 0
        denumerator = 0
        for stream in streams:
            total_mass_rate = stream.components.sum().sum()
            if total_mass_rate.m == 0:
                continue
            mixture_Cp = cls.mixture_heat_capacity(API, stream)
            numerator += stream.temperature.to("kelvin") * total_mass_rate * mixture_Cp
            denumerator += total_mass_rate * mixture_Cp
        temperature = (numerator / denumerator).to("degF")
        pressure = pressure if pressure is not None else mean([stream.pressure for stream in streams])
        stream = Stream('combined', temperature=temperature, pressure=pressure, comp_matrix=comp_matrix)
        return stream

    @staticmethod
    def mixture_heat_capacity(API, stream):
        """
        cp_mix = (mass_1/mass_mix)cp_1 + (mass_2/mass_mix)cp_2 + ...

        :param API:
        :param stream:
        :return: (float) heat capacity of mixture (unit = btu/degF/day)
        """
        temperature = stream.temperature
        total_mass_rate = stream.components.sum().sum()
        oil_heat_capacity = stream.hydrocarbon_rate(PHASE_LIQUID) * Oil.specific_heat(API, temperature)
        water_heat_capacity = Water.heat_capacity(stream)
        gas_heat_capacity = Gas.heat_capacity(stream)

        heat_capacity = (oil_heat_capacity + water_heat_capacity + gas_heat_capacity) / total_mass_rate
        return heat_capacity
