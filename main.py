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


def is_txhash(in_str: str):
    pattern = r"^0x([A-Fa-f0-9]{64})$"
    if re.match(pattern, in_str):
        return True
    else:
        return False


@cl.on_chat_start
async def main():
    # Instantiate the chain for that user session
    prompt = PromptTemplate(
        template=TEMPLATE,
        input_variables=[
            "txhash",
            "blocktime",
            "from_addr",
            "to_addr",
            "value",
            "gas_used",
            "gas_price",
            "status",
            "action_field",
            "actions",
        ],
    )

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
        prompt=prompt,
        llm=chatllm,
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

    action_existed = len(tagged_tx["actions"]) != 0
    action_str = ""
    if action_existed:
        action_str += "\n".join(f"- {a}" for a in tagged_tx["actions"])

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
            "action_field": "Actions:\n" if action_existed else "",
            "actions": action_str,
        },
        callbacks=[cl.LangchainCallbackHandler()],
    )
    await cl.Message(content=res).send()
