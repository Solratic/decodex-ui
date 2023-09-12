from langchain import PromptTemplate, LLMChain
from langchain.chat_models import AzureChatOpenAI
import chainlit as cl
from chainlit.server import app
from decodex.translate import Translator
from decodex.type import TaggedTx
from decodex.utils import (
    fmt_addr,
    fmt_blktime,
    fmt_gas,
    fmt_status,
    fmt_value,
)
from jinja2 import Template
from tabulate import tabulate
import os
import re
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import status
from typing import Optional, Union, Literal
from jsonrpc import PriceOracle
from datetime import datetime
from decodex.type import TaggedTx, TaggedAddr, ERC20Compatible
from typing import TypedDict, List
from logging import Logger, INFO
from decodex.constant import NULL_ADDRESS_0x0, NULL_ADDRESS_0xF

# 擴展 AssetBalanceChanged
ExtendedAssetBalanceChanged = TypedDict(
    "ExtendedAssetBalanceChanged",
    {
        "asset": ERC20Compatible,  # address of the asset
        "balance_change": float,  # balance change of the asset
        "balance_change_usd": float,  # balance change in USD (Optional)
    },
    total=False,
)

# 使用擴展的 AssetBalanceChanged 來擴展 AccountBalanceChanged
ExtendedAccountBalanceChanged = TypedDict(
    "ExtendedAccountBalanceChanged",
    {"address": TaggedAddr, "assets": List[ExtendedAssetBalanceChanged]},
)

# 使用擴展的 AccountBalanceChanged 來擴展 TaggedTx
ExtendedTaggedTx = TypedDict(
    "ExtendedTaggedTx",
    {
        "txhash": str,
        "from": TaggedAddr,
        "to": TaggedAddr,
        "block_number": int,
        "block_time": datetime,
        "value": int,
        "gas_used": int,
        "gas_price": int,
        "input": str,
        "status": int,
        "reason": Optional[str],
        "method": Optional[str],
        "actions": List[str],
        "balance_change": List[ExtendedAccountBalanceChanged],
    },
    total=False,
)

LOGGER = Logger("decodex-ui", level=INFO)
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI")
ORACLE_PROVIDER_URI = os.getenv("ORACLE_PROVIDER_URI")
ORACLE = None
if ORACLE_PROVIDER_URI:
    ORACLE = PriceOracle(ORACLE_PROVIDER_URI)


WETH = {
    "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
}
TEMPLATE = """\
As a proficient blockchain data analyst, your role entails delivering concise insights into the intentions driving the given transactions. Please present a brief overview for each transaction, comprising three sentences. Include details such as the transaction time, involved parties, and their actions.

Transaction: {{txhash}}
Blocktime: {{blocktime}}
From: {{from_addr}}
To: {{to_addr}}  {% if contract_created %} (Contract Created: {{contract_created}}){% endif %}
Value: {{value}}
GasUsed: {{gas_used}}
Gas Price: {{gas_price}}
Status: {{status}}{% if reason %} ({{reason}}){% endif %}
{% if method -%}
Method: {{method}}
{% endif -%}
{% if actions -%}

Actions
------
{{actions}}
{% endif -%}
{% if balance_change -%}

Balance Changes
--------------
{{balance_change}}
{% endif -%}
"""

translator = Translator(
    provider_uri=WEB3_PROVIDER_URI,
    chain="ethereum",
    verbose=True,
)


def is_txhash(in_str: str):
    pattern = r"^0x([A-Fa-f0-9]{64})$"
    if re.match(pattern, in_str):
        return True
    else:
        return False


def fill_usd_price(chain: str, tx: TaggedTx):
    balances = tx["balance_change"]
    involved_tokens = set()
    for balance in balances:
        for asset in balance["assets"]:
            address = asset["asset"]["address"]
            if address in {NULL_ADDRESS_0x0, NULL_ADDRESS_0xF}:
                weth = WETH[chain]
                involved_tokens.add(weth)
            else:
                involved_tokens.add(address)

    block_timestamp = tx["block_time"]
    timestamp = int(block_timestamp.timestamp())

    prices = ORACLE.get_token_price(
        chain="ethereum",
        tokens=list(map(lambda x: x.lower(), involved_tokens)),
        timestamp=timestamp,
        tolerance=3600,
        as_dict=True,
    )

    for balance in balances:
        for asset in balance["assets"]:
            address = asset["asset"]["address"]
            if address in {NULL_ADDRESS_0x0, NULL_ADDRESS_0xF}:
                address = WETH[chain]
            price_info = prices.get(address.lower(), None)
            if price_info:
                price_usd = float(price_info["price"])
                balance_change_usd = asset["balance_change"] * price_usd
                asset["balance_change_usd"] = balance_change_usd


@cl.on_chat_start
async def main():
    chatllm = AzureChatOpenAI(
        openai_api_key=os.getenv("OPENAI_CHAT_API_KEY"),
        openai_api_base=os.getenv("OPENAI_CHAT_API_BASE"),
        openai_api_version=os.getenv("OPENAI_CHAT_API_VERSION"),
        openai_api_type=os.getenv("OPENAI_CHAT_API_TYPE"),
        deployment_name=os.getenv("OPENAI_CHAT_API_MODEL"),
        streaming=True,
        temperature=0,
    )

    llm_chain = LLMChain(
        llm=chatllm,
        prompt=PromptTemplate.from_template(
            template=TEMPLATE,
            template_format="jinja2",
        ),
        verbose=True,
    )

    # Store the chain in the user session
    cl.user_session.set("llm_chain", llm_chain)
    await cl.Message(
        content="This is the transaction Explainer AI. Please input transaction hash on ethereum to start!"
    ).send()


@cl.on_message
async def main(txhash: str):
    if not is_txhash(txhash):
        await cl.Message(
            content="This is not a valid transaction hash. Please try again."
        ).send()
        return

    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")  # type: LLMChain

    # Get the transaction
    await cl.Message(content="Searching transaction").send()

    tagged_tx = translator.translate(txhash)

    txhash = tagged_tx["txhash"]
    blocktime = fmt_blktime(tagged_tx["block_time"])
    from_addr = fmt_addr(tagged_tx["from"])
    to_addr = fmt_addr(tagged_tx["to"]) if tagged_tx["to"] else None
    contract_created = (
        fmt_addr(tagged_tx["contract_created"])
        if tagged_tx["contract_created"]
        else None
    )
    value = fmt_value(tagged_tx["value"])
    gas_used = f'{tagged_tx["gas_used"]}'
    gas_price = fmt_gas(tagged_tx["gas_price"])
    status = fmt_status(tagged_tx["status"])
    method = tagged_tx["method"]
    reason = tagged_tx["reason"]

    actions = "\n".join(f"- {a}" for a in tagged_tx["actions"])

    render = ""
    for acc in tagged_tx["balance_change"]:
        render += "\n"
        render += "Account: " + fmt_addr(acc["address"], truncate=False)
        render += "\n"
        table_data = []
        for asset in acc["assets"]:
            table_data.append(
                [
                    fmt_addr(asset["asset"], truncate=False),
                    asset["balance_change"],
                ]
            )

        render += tabulate(
            table_data, headers=["Asset", "Balance Change"], tablefmt="grid"
        )
        render += "\n"

    res = llm_chain.run(
        {
            "txhash": txhash,
            "blocktime": blocktime,
            "from_addr": from_addr,
            "to_addr": to_addr,
            "contract_created": contract_created,
            "value": value,
            "gas_used": gas_used,
            "gas_price": gas_price,
            "status": status,
            "method": method,
            "actions": actions,
            "reason": reason,
            "balance_change": render,
        },
        callbacks=[cl.LangchainCallbackHandler()],
    )
    await cl.Message(content=res).send()


@app.get("/tx/{txhash}", tags=["api"])
async def search(txhash: str) -> ExtendedTaggedTx:
    if not is_txhash(txhash):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "This is not a valid transaction hash. Please try again."
            },
        )
    try:
        tagged = translator.translate(txhash=txhash)
        if ORACLE is not None:
            fill_usd_price(chain="ethereum", tx=tagged)
        LOGGER.info(tagged)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(tagged),
        )
    except Exception as e:
        LOGGER.exception(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)},
        )


@app.get("/simulate", tags=["api"])
async def simulate(
    from_address: str,
    to_address: str,
    value: float = 0.0,
    data: str = "0x",
    block: Union[int, Literal["latest"]] = "latest",
    gas: Union[int, Literal["auto"]] = "auto",
    gas_price: Union[float, Literal["auto"]] = "auto",
) -> ExtendedTaggedTx:
    try:
        if gas_price is None:
            gas_price = "auto"
        elif isinstance(gas_price, float):
            gas_price = int(gas_price * 1e9)
        if gas is None:
            gas = "auto"

        res = translator.simulate(
            from_address=from_address,
            to_address=to_address,
            value=int(value * 1e18),
            data=data,
            block=block,
            gas=gas,
            gas_price=gas_price,
        )
        if ORACLE is not None:
            fill_usd_price(chain="ethereum", tx=res)
        print(res)
        LOGGER.info(res)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(res),
        )
    except Exception as e:
        LOGGER.exception(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)},
        )
