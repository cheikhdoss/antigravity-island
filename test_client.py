import asyncio
import json
import sys
import websockets

sys.stdout.reconfigure(encoding='utf-8')

async def run_demo():
    uri = "ws://127.0.0.1:8765"
    print(f"Connexion au serveur de l'île sur {uri}...")
    
    try:
        async with websockets.connect(uri) as ws:
            print("Connecté avec succès !\n")

            # 1. Mode Écoute
            print("1. Envoi : Mode Listening (l'utilisateur parle)")
            await ws.send(json.dumps({
                "action": "set_state",
                "state": "listening"
            }))
            resp = await ws.recv()
            print(f"   Réponse : {resp}")
            
            # Simuler de la voix (audio power)
            for power in [0.2, 0.6, 0.9, 0.4, 0.8, 0.3]:
                await ws.send(json.dumps({
                    "action": "audio_power",
                    "power": power
                }))
                await asyncio.sleep(0.3)

            # 2. Mode Réflexion
            print("\n2. Envoi : Mode Thinking (analyse multimodale de l'écran)")
            await ws.send(json.dumps({
                "action": "set_state",
                "state": "thinking"
            }))
            await ws.recv()
            await asyncio.sleep(2.0)

            # 3. Mode Parole
            print("\n3. Envoi : Mode Speaking (Antigravity s'exprime)")
            await ws.send(json.dumps({
                "action": "speak",
                "text": "Bonjour ! J'ai bien analysé ton écran. Ton projet est prêt pour le commit Git."
            }))
            await ws.recv()
            await asyncio.sleep(3.5)

            # 4. Mode Action
            print("\n4. Envoi : Mode Action (Agent en tâche de fond)")
            await ws.send(json.dumps({
                "action": "action",
                "title": "Compilation & Tests E2E",
                "detail": "Vérification des 12 modules en arrière-plan...",
                "progress": 0.75
            }))
            await ws.recv()
            await asyncio.sleep(3.0)

            # 5. Retour Idle
            print("\n5. Envoi : Retour au repos (Idle)")
            await ws.send(json.dumps({
                "action": "idle"
            }))
            await ws.recv()
            print("\n✅ Démonstration terminée avec succès !")

    except Exception as e:
        print(f"❌ Impossible de se connecter à l'île : {e}")
        print("Assurez-vous que 'python main.py' est bien lancé.")

if __name__ == "__main__":
    asyncio.run(run_demo())
