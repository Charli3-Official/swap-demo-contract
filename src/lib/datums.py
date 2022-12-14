"""Datums implementation"""
from dataclasses import dataclass
from typing import Union, Optional
from pycardano import PlutusData
from pycardano.serialization import IndefiniteList


@dataclass
class PriceData(PlutusData):
    """represents cip oracle datum PriceMap(Tag +2)"""

    CONSTR_ID = 2
    price_map: dict

    def get_price(self) -> int:
        """get price from price map"""
        return self.price_map[0]

    def get_timestamp(self) -> int:
        """get timestamp of the feed"""
        return self.price_map[1]

    def get_expiry(self) -> int:
        """get expiry of the feed"""
        return self.price_map[2]

    @classmethod
    def set_price_map(cls, price: int, timestamp: int, expiry: int):
        """set price_map"""
        price_map = {0: price, 1: timestamp, 2: expiry}
        return cls(price_map)


@dataclass
class GenericData(PlutusData):
    CONSTR_ID = 0
    price_data: PriceData


@dataclass
class Nothing(PlutusData):
    CONSTR_ID = 1


# 121([123([{0: 2400000, 1: 1669903618, 2: 1701439564}])])