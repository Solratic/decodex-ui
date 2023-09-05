from langchain import PromptTemplate, LLMChain
from langchain.chat_models import AzureChatOpenAI
import chainlit as cl
from decodex.translate import Translator
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

WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URL")

TEMPLATE = """
Please explain the main objectives of the following transaction:

Transaction: {txhash}
Blocktime: {blocktime}
From: {from_addr}
To: {to_addr}
Value: {value}
GasUsed: {gas_used}
Gas Price: {gas_price}
Status: {status}
{action_field}{actions}
"""


TEMPLATE = """\
As a proficient blockchain data analyst, your role entails delivering concise insights into the intentions driving the given transactions. Please present a brief overview for each transaction, comprising three sentences. Include details such as the transaction time, involved parties, and their actions.
Transaction: {{txhash}}
Blocktime: {{blocktime}}
From: {{from_addr}}
To: {{to_addr}}
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


def is_txhash(in_str: str):
    pattern = r"^0x([A-Fa-f0-9]{64})$"
    if re.match(pattern, in_str):
        return True
    else:
        return False


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

    translator = Translator(
        provider_uri=WEB3_PROVIDER_URI,
        chain="ethereum",
        verbose=True,
    )
    tagged_tx = translator.translate(txhash)

    txhash = tagged_tx["txhash"]
    blocktime = fmt_blktime(tagged_tx["block_time"])
    from_addr = fmt_addr(tagged_tx["from"])
    to_addr = fmt_addr(tagged_tx["to"])
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
