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
async def island_set_style(style: str = "island") -> str:
    """
    Change le style d'encoche affiché sur l'écran Windows.
    Valeurs acceptées :
    - 'island' : Dynamic Island (pilule flottante moderne)
    - 'iphonex' : Encoche iPhone X authentique (avec cornes concaves et grille haut-parleur)
    """
    res = await send_command_to_island({"action": "set_style", "style": style})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_point_at(x: int, y: int, label: str = "", duration: float = 3.5, color: str = None) -> str:
    """
    Pointe visuellement un élément sur l'écran de l'utilisateur avec un halo laser et une étiquette.
    Agit comme le troisième bras d'Antigravity (inspiré de HeyClicky).
    - x : Coordonnée horizontale en pixels
    - y : Coordonnée verticale en pixels
    - label : Message ou libellé explicatif affiché au-dessus du point (ex: 'Cliquez ici')
    - duration : Durée d'affichage en secondes avant disparition progressive
    - color : Couleur du pointeur (ex: '#38bdf8' pour cyan, '#22c55e' pour émeraude)
    """
    payload = {
        "action": "point_at",
        "x": x,
        "y": y,
        "label": label,
        "duration": duration
    }
    if color:
        payload["color"] = color
    res = await send_command_to_island(payload)
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_capture_screen(monitor_index: int = 1) -> str:
    """
    Capture instantanément l'écran Windows de l'utilisateur à très haute vitesse via MSS.
    Permet à Antigravity de 'voir' ce qui est affiché à l'écran.
    Retourne le chemin absolu du fichier PNG capturé ainsi que ses dimensions.
    """
    res = await send_command_to_island({
        "action": "capture_screen",
        "monitor": monitor_index
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_get_screen_info() -> str:
    """
    Récupère la résolution et la liste des écrans connectés sur la machine Windows de l'utilisateur.
    """
    res = await send_command_to_island({"action": "get_screens"})
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
