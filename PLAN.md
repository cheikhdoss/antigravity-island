# Plan de Développement — Antigravity Island (Windows)

## 🎯 Objectif
Créer une île dynamique ("Dynamic Island" / encoche Apple) native sous Windows, toujours au premier plan, contrôlable directement par Antigravity via WebSocket et protocole d'actions (MCP), permettant à l'IA d'interagir visuellement et vocalement avec l'utilisateur même quand la fenêtre Antigravity est réduite.

---

## 🗺️ Phases du Projet

### Phase 1 : Le Visuel de l'Encoche (UI/UX Haute Fidélité PyQt6)
- [x] Initialisation du dépôt Git et structure modulaire.
- [ ] Fenêtre transparente, sans bordure, `always-on-top`, ancrée au sommet de l'écran principal.
- [ ] Moteur de géométrie fluide (transitions par interpolation `QEasingCurve.Type.OutBack` / `InOutCubic`).
- [ ] Les 5 états visuels :
  1. `IDLE` : Pilule compacte discrète (140x34px) avec lueur d'activité.
  2. `LISTENING` : Onde sonore réactive (Waveform animée 320x46px).
  3. `THINKING` : Orbite lumineuse pulsante (260x42px).
  4. `SPEAKING` : Cartouche élargi avec texte de réponse & equalizer vocal (460x84px).
  5. `ACTION` : Affichage des tâches en cours de l'agent (480x120px).
- [ ] Bouton de test interactif / raccourcis pour valider visuellement tous les états.

### Phase 2 : Le Canal de Contrôle Bidirectionnel (WebSocket Server)
- [ ] Serveur WebSocket asynchrone intégré (`ws://127.0.0.1:8765`).
- [ ] Protocole de commandes JSON :
  - `set_state(state)`
  - `speak(text, audio_level)`
  - `show_notification(title, message, duration)`
  - `point_to(x, y, label)`
- [ ] Script client de démonstration `test_client.py` permettant à Antigravity de piloter l'île.

### Phase 3 : Le Moteur Cœur (Voice & Vision)
- [ ] Raccourci clavier global Push-to-Talk (`Ctrl + Espace` ou `Ctrl + Alt`).
- [ ] Capture d'écran instantanée multi-moniteurs haute résolution via `mss` / Windows Desktop Duplication.
- [ ] Overlay de pointage d'écran (curseur bleu volant le long d'arcs de Bézier vers les coordonnées ciblées).
- [ ] Synthèse vocale & streaming audio vers l'île.

### Phase 4 : Intégration Native Antigravity (MCP Server)
- [ ] Création du serveur MCP `antigravity-island-mcp` enregistrant les outils officiels pour Antigravity :
  - `island_speak`
  - `island_display`
  - `island_point`
  - `island_capture`
- [ ] Autonomie complète : Antigravity agit spontanément sur l'île pour notifier et guider.
