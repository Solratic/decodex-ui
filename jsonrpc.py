from web3 import Web3
from web3.providers.rpc import HTTPProvider
from typing import Optional, TypedDict, List, Union, Dict
from concurrent.futures import ThreadPoolExecutor
import os


class TokenPrice(TypedDict):
    chain: str
    name: str
    price: str
    symbol: str
    timestamp: int
    token_address: str


class PriceOracle:
    def __init__(self, provider_uri):
        self.w3 = Web3(HTTPProvider(provider_uri))

    def get_token_price(
        self,
        chain: str,
        tokens: List[str],
        timestamp: int,
        tolerance: Optional[int] = None,
        as_dict: bool = False,
        *,
        max_workers: int = 10,
    ) -> Union[List[Optional[TokenPrice]], Dict[str, Optional[TokenPrice]]]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            prices = executor.map(
                lambda token: self._get_token_price(chain, token, timestamp, tolerance),
                tokens,
            )
        if as_dict:
            return {token["token_address"]: token for token in prices if token}
        else:
            return [token for token in prices if token]

    def _get_token_price(
        self,
        chain: str,
        token: str,
        timestamp: int,
        tolerance: Optional[int] = None,
    ) -> Optional[TokenPrice]:
        """
        Get token price from chain and token address, at a given timestamp (the closest one before the timestamp)

        Parameters
        ----------
        chain : str
            chain name, e.g. ethereum
        token : str
            token address, e.g. 0x069f967be0ca21c7d793d8c343f71e597d9a49b3
        timestamp : int
            timestamp in seconds
        tolerance : int | None
            tolerance for the senconds for price, None to accept any time for the price

        Returns
        -------
        If successful, returns a TokenPrice object, otherwise returns None

        - success
            ```json
            {
            "id": "1",
            "jsonrpc": "2.0",
            "result": {
                "chain": "ethereum",
                "name": "hzm",
                "price": "0.00039805",
                "symbol": "HZM Coin",
                "timestamp": 1692948326,
                "token_address": "0x069f967be0ca21c7d793d8c343f71e597d9a49b3"
            }
            }
            ```

        - failure
            ```json
            {
                "id": "1",
                "jsonrpc": "2.0",
                "result": null
            }
            ```
        """
        response = self.w3.provider.make_request(
            "hdt_getTokenPrice",
            [chain, token, timestamp],
        )
        if response.get("result", None) is None:
            return None

        price = TokenPrice(**response["result"])
        if tolerance is not None and abs(price["timestamp"] - timestamp) > tolerance:
            return None
        return price


if __name__ == "__main__":
    WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL")
    oracle = PriceOracle(WEB3_PROVIDER_URL)
    prices = oracle.get_token_price(
        chain="ethereum",
        tokens=["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"],
        timestamp=1693497600,
        tolerance=36000,
        as_dict=True,
    )
    print(prices)
