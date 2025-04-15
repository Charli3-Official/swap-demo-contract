from dataclasses import dataclass

from pycardano import PlutusData


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


@dataclass
class OdvRequest(PlutusData):
    """Top up contract redeemer"""

    CONSTR_ID = 8


@dataclass
class OracleRedeemer(PlutusData):
    """Types of actions for Oracle smart contract"""

    CONSTR_ID = 0  # Base constructor ID


class OdvAggregate(OracleRedeemer):
    """User sends on demand validation request with oracle nodes message"""

    CONSTR_ID = 0
