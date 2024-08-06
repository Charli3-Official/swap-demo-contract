from pycardano import PlutusData
from dataclasses import dataclass


@dataclass
class SwapA(PlutusData):
    CONSTR_ID = 0
    amount: int


@dataclass
class SwapB(PlutusData):
    CONSTR_ID = 1
    amount: int


@dataclass
class AddLiquidity(PlutusData):
    CONSTR_ID = 2
