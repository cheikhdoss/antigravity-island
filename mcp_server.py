import asyncio
import json
import websockets
from mcp.server.fastmcp import FastMCP

# Initialisation du serveur MCP officiel Antigravity Island
mcp = FastMCP("antigravity-island")

WS_URL = "ws://127.0.0.1:8765"

async def send_command_to_island(payload: dict) -> dict:
    """Envoie un ordre en JSON au serveur WebSocket local de l'encoche."""
    try:
        async with websockets.connect(WS_URL, open_timeout=2) as ws:
            await ws.send(json.dumps(payload))
            response = await asyncio.wait_for(ws.recv(), timeout=2)
            return json.loads(response)
    except Exception as e:
        return {"status": "error", "message": f"L'application Antigravity Island n'est pas joignable sur {WS_URL} ({e}). Lancez d'abord AntigravityIsland.exe."}

@mcp.tool()
async def island_set_state(state: str) -> str:
    """
    Change l'état visuel de l'encoche flottante sur l'écran Windows.
    Valeurs acceptées pour 'state' : 'idle', 'listening', 'thinking', 'speaking', 'action'.
    """
    res = await send_command_to_island({"action": "set_state", "state": state})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_speak(text: str) -> str:
    """
    Affiche un message textuel et anime l'encoche en mode parole (Speaking).
    Idéal pour donner un compte-rendu ou interpeller l'utilisateur directement à l'écran.
    """
    res = await send_command_to_island({"action": "speak", "text": text})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_action(title: str, detail: str = "", progress: float = 0.0) -> str:
    """
    Affiche une mission d'agent en cours sur l'encoche avec barre de progression.
    - title : Titre de l'action (ex: 'Génération du composant')
    - detail : Détail explicatif court (ex: 'Vérification des tests...')
    - progress : Valeur entre 0.0 et 1.0 (ex: 0.75 pour 75%)
    """
    res = await send_command_to_island({
        "action": "action",
        "title": title,
        "detail": detail,
        "progress": progress
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_idle() -> str:
    """
    Remet l'encoche en mode compact au repos (Idle).
    """
    res = await send_command_to_island({"action": "idle"})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_audio_pulse(power: float = 0.5) -> str:
    """
    Anime le visualiseur d'ondes audio sur l'encoche (valeur entre 0.0 et 1.0).
    """
    res = await send_command_to_island({"action": "audio_power", "power": power})
    return json.dumps(res, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()
