#
# OPGEE Attribute and related classes
#
# Authors: Richard Plevin and Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior
# University. See LICENSE.txt for license details.
#
import pandas as pd

from .core import STP, TemperaturePressure
from .log import getLogger
from .stream import Stream
from .thermodynamics import Gas, Oil, Water
from .units import ureg

_logger = getLogger(__name__)

# TODO: improve this to use temp and press
def combine_streams(streams):
    """
    Thermodynamically combine multiple streams' components into a new
    anonymous Stream. This is used on input streams since it makes no
    sense for output streams.

    :param streams: (list of Streams) the Streams to combine
    :return: (Stream) if len(streams) > 1, returns a new Stream. If
       len(streams) == 1, the input stream (streams[0]) is returned.
    """
    if len(streams) == 1:  # corner case
        return streams[0]

    non_empty_streams = [stream for stream in streams if not stream.is_uninitialized()]
    non_empty_streams_pressure = [stream.tp.P for stream in non_empty_streams]

    non_empty_API_streams = \
        [stream for stream in non_empty_streams if stream.API is not None and stream.liquid_flow_rate("oil").m > 0]

    def calculated_combined_API_using_weighted_average(streams):
        """
            Calculate the combined API of crude oil streams using the weighted average method.

            Args:
                streams (List): A list of crude oil stream objects.

            Returns:
                float: The combined API of the crude oil streams.
        """
        if len(streams) == 1:
            return streams[0].API

        total_mass_rate = sum(stream.liquid_flow_rate("oil") for stream in streams)
        sum_of_mass_multiply_specific_gravity = sum(
            stream.liquid_flow_rate("oil") * Oil.specific_gravity(stream.API) for stream in streams)

        combined_sg = sum_of_mass_multiply_specific_gravity / total_mass_rate
        return Oil.API_from_SG(combined_sg)

    if not non_empty_streams:
        return Stream("empty_stream", TemperaturePressure(None, None))

    comp_matrix = sum([stream.components for stream in streams])

    stream_temperature = pd.Series([stream.tp.T.to("kelvin").m for stream in non_empty_streams],
                                   dtype="pint[kelvin]")

    stream_specific_heat = pd.Series([mixture_specific_heat_capacity(stream).m for
                                      stream in non_empty_streams],
                                     dtype="pint[btu/degF/day]")

    stream_sp_heat_sum = stream_specific_heat.sum()
    if stream_sp_heat_sum.m != 0.0:
        temperature = (stream_temperature * stream_specific_heat).sum() / stream_sp_heat_sum
        temperature = temperature.to("degF")
        min_pressure = min(non_empty_streams_pressure)
        stream = Stream('combined',
                        TemperaturePressure(temperature, max(STP.P, min_pressure)),
                        comp_matrix=comp_matrix)
    else:
        stream = Stream('empty_stream', tp=STP)

    if len(non_empty_API_streams) > 0:
        stream.API = calculated_combined_API_using_weighted_average(non_empty_API_streams)
    else:
        stream.API = None
    return stream


def mixture_specific_heat_capacity(stream):
    """
    cp_mix = (mass_1/mass_mix)cp_1 + (mass_2/mass_mix)cp_2 + ...

    :param API:
    :param stream:
    :return: (float) heat capacity of mixture (unit = btu/degF/day)
    """
    temperature = stream.tp.T
    oil_mass_rate = stream.liquid_flow_rate("oil")
    if oil_mass_rate.m == 0 or stream.API is None:
        oil_heat_capacity = ureg.Quantity(0, "btu/delta_degF/day")
    else:
        oil_heat_capacity = oil_mass_rate * Oil.specific_heat(stream.API, temperature)
    water_heat_capacity = Water.heat_capacity(stream)
    gas_heat_capacity = Gas.heat_capacity(stream)

    heat_capacity = oil_heat_capacity + water_heat_capacity + gas_heat_capacity
    return heat_capacity.to("btu/delta_degF/day")
