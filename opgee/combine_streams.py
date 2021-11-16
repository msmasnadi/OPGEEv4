# from . import ureg
import pandas as pd

from opgee.stream import PHASE_LIQUID, Stream
from .error import OpgeeException
from .log import getLogger
from .thermodynamics import Oil, Gas, Water

_logger = getLogger(__name__)

#TODO: improve the combine stream to use temp and press
def combine_streams(streams, API, pressure=None, temperature=None):
    """
    Thermodynamically combine multiple streams' components into a new
    anonymous Stream. This is used on input streams since it makes no
    sense for output streams.

    :param temperature:
    :param pressure:
    :param API:
    :param streams: (list of Streams) the Streams to combine
    :return: (Stream) if len(streams) > 1, returns a new Stream. If
       len(streams) == 1, the original stream is returned.
    """
    if len(streams) == 1:  # corner case
        return streams[0]

    matrices = [stream.components for stream in streams]

    comp_matrix = sum(matrices)

    non_empty_streams = [stream for stream in streams if not stream.is_empty()]

    if not non_empty_streams:
        raise OpgeeException(f"combine_streams: streams are all empty")

    # TODO: This block might not be necessary
    for stream in non_empty_streams:
        if stream.pressure.m == 0:
            raise OpgeeException(f"combine_streams: steam pressure of '{stream.name}' is Zero")

    first_non_empty_stream = non_empty_streams[0]
    stream_temperature = pd.Series([stream.temperature.to("kelvin").m for stream in non_empty_streams],
                                   dtype="pint[kelvin]")
    stream_mass_rate = pd.Series([stream.total_flow_rate().m for stream in non_empty_streams],
                                 dtype="pint[tonne/day]")
    stream_Cp = pd.Series([mixture_heat_capacity(API, stream).m for stream in non_empty_streams],
                          dtype="pint[btu/degF/day]")
    stream_specific_heat = stream_mass_rate * stream_Cp
    temperature = (stream_temperature * stream_specific_heat).sum() / stream_specific_heat.sum()
    temperature = temperature.to("degF")
    stream = Stream('combined', temperature=temperature, pressure=first_non_empty_stream.pressure, comp_matrix=comp_matrix)
    return stream


def mixture_heat_capacity(API, stream):
    """
    cp_mix = (mass_1/mass_mix)cp_1 + (mass_2/mass_mix)cp_2 + ...

    :param API:
    :param stream:
    :return: (float) heat capacity of mixture (unit = btu/degF/day)
    """
    temperature = stream.temperature
    total_mass_rate = stream.total_flow_rate()
    oil_heat_capacity = stream.hydrocarbon_rate(PHASE_LIQUID) * Oil.specific_heat(API, temperature)
    water_heat_capacity = Water.heat_capacity(stream)
    gas_heat_capacity = Gas.heat_capacity(stream)

    heat_capacity = (oil_heat_capacity + water_heat_capacity + gas_heat_capacity) / total_mass_rate
    return heat_capacity
