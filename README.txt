# Snake Game - Pygbag Version

This is your Pygame Snake game modified so it can be packaged for the web with Pygbag.

## Controls

- Desktop: Arrow keys / WASD to move, Esc or P to pause.
- Mobile (web): Swipe, or use the on-screen D-pad / joystick. Tap the small
  "JOYSTICK" / "D-PAD" button next to Pause to switch between the two —
  your choice is remembered for next time.

## Leaderboard

- On the web build, scores are saved in the browser's localStorage, so
  they persist across page reloads and repeat visits on the same browser.
- When running natively on desktop (`python main.py`), scores are saved
  to `highscore.json` in the project folder instead.

## Run normally on your computer

Install dependencies from requirements.txt:

```bash
python -m pip install -r requirements.txt
```

Then:

```bash
python main.py
```

## Build a browser version

Install Pygbag:

```bash
python -m pip install pygbag --user --upgrade
```

From the folder containing `SnakeGame`, run:

```bash
python -m pygbag SnakeGame
```

Then open:

http://localhost:8000

The generated browser files will be in:

```text
SnakeGame/build/web/
```

You can publish the contents of `build/web` with GitHub Pages to get a free public URL.
