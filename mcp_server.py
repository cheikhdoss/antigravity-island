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
async def island_get_last_query() -> str:
    """
    Récupère la dernière requête vocale enregistrée et transcrite depuis le microphone par le raccourci Win + Alt.
    """
    res = await send_command_to_island({"action": "get_last_query"})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_audio_pulse(power: float = 0.5) -> str:
    """
    Anime le visualiseur d'ondes audio sur l'encoche (valeur entre 0.0 et 1.0).
    """
    res = await send_command_to_island({"action": "audio_power", "power": power})
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_find_elements(query: str = "", image_path: str = "") -> str:
    """
    Détecte les éléments de texte et boutons affichés à l'écran via l'OCR haute performance natif Windows.
    Retourne la liste des éléments correspondants avec leurs coordonnées exactes (center_x, center_y, width, height).
    - query : Texte ou mot-clé à rechercher à l'écran (ex: 'Enregistrer', 'Paramètres', 'Fermer', 'GitHub'). Si vide, retourne tous les textes détectés.
    - image_path : Chemin optionnel d'une capture d'écran PNG. Si non spécifié, prend une capture instantanée automatique.
    """
    payload = {"action": "find_elements", "query": query}
    if image_path:
        payload["image_path"] = image_path
    res = await send_command_to_island(payload)
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_click(x: int, y: int, button: str = "left", double: bool = False, smooth: bool = True) -> str:
    """
    Déplace la souris et clique sur une position spécifique de l'écran Windows.
    - x : Coordonnée X en pixels
    - y : Coordonnée Y en pixels
    - button : 'left' (gauche), 'right' (droit) ou 'middle' (molette)
    - double : True pour effectuer un double-clic
    - smooth : True pour utiliser un vol de curseur fluide le long d'une courbe de Bézier naturelle (recommandé)
    """
    res = await send_command_to_island({
        "action": "click",
        "x": x,
        "y": y,
        "button": button,
        "double": double,
        "smooth": smooth
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_click_element(query: str, button: str = "left", double: bool = False) -> str:
    """
    Localise automatiquement un texte ou bouton à l'écran par OCR et clique dessus directement.
    - query : Texte du bouton ou label à cliquer (ex: 'Annuler', 'Se connecter', 'Envoyer')
    - button : 'left' (gauche) ou 'right' (droit)
    - double : True pour double-cliquer
    """
    ocr_res = await send_command_to_island({"action": "find_elements", "query": query})
    if ocr_res.get("status") != "success" or not ocr_res.get("elements"):
        return json.dumps({
            "status": "error",
            "message": f"Élément introuvable à l'écran pour la recherche '{query}'."
        }, ensure_ascii=False)
    
    first = ocr_res["elements"][0]
    cx = first.get("center_x")
    cy = first.get("center_y")

    # Mettre l'encoche en mode action et pointer brièvement
    await send_command_to_island({
        "action": "point_at",
        "x": cx,
        "y": cy,
        "label": f"Clic sur {first.get('text', query)[:25]}",
        "duration": 1.2
    })

    # Clic fluide
    res = await send_command_to_island({
        "action": "click",
        "x": cx,
        "y": cy,
        "button": button,
        "double": double,
        "smooth": True
    })
    res["clicked_element"] = first
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_move_cursor(x: int, y: int, duration: float = 0.35) -> str:
    """
    Déplace fluidement le curseur de souris Windows vers une cible le long d'une courbe de Bézier avec amorti.
    - x : Coordonnée X en pixels
    - y : Coordonnée Y en pixels
    - duration : Durée du déplacement en secondes (défaut: 0.35s)
    """
    res = await send_command_to_island({
        "action": "move_cursor",
        "x": x,
        "y": y,
        "duration": duration
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_type(text: str, delay: float = 0.015) -> str:
    """
    Saisit du texte au clavier Windows avec support natif Unicode complet (accents français, ponctuation, symboles).
    - text : Texte à taper
    - delay : Délai en secondes entre chaque caractère frappé (défaut: 0.015s)
    """
    res = await send_command_to_island({
        "action": "type",
        "text": text,
        "delay": delay
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_press_key(key: str) -> str:
    """
    Simule une touche ou combinaison de touches Windows.
    Exemples : 'enter', 'tab', 'escape', 'ctrl+s', 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d', 'backspace'.
    """
    res = await send_command_to_island({
        "action": "press_key",
        "key": key
    })
    return json.dumps(res, ensure_ascii=False)

@mcp.tool()
async def island_scroll(amount: int = -3) -> str:
    """
    Fait défiler la molette de souris.
    - amount : Nombre de crans de molette (valeur positive pour monter, négative pour descendre, ex: -3).
    """
    res = await send_command_to_island({
        "action": "scroll",
        "amount": amount
    })
    return json.dumps(res, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()
