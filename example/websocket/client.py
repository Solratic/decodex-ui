import asyncio
import websockets
import os


async def test_websocket():
    # Replace with the actual URI of your WebSocket server
    uri = f"ws://localhost:{os.getenv('DECODEX_SERVER_PORT', 8000)}/ws"
    try:
        async with websockets.connect(uri) as websocket:
            path = os.path.join(os.path.dirname(__file__), "description.txt")
            with open(path, "r") as F:
                await websocket.send(F.read())

            # Iterating over the received messages
            while True:
                response = await websocket.recv()
                print(response, end="")
    except websockets.exceptions.ConnectionClosedOK as e:
        pass
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_websocket())
