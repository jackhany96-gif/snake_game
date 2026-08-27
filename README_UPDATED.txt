# Snake Game - Discord Login + Level 6

## What was added

- Discord login gate: the game menu requires a Discord-authenticated player before Free Mode or Levels can start.
- The Discord username becomes the in-game username.
- Level 6 was added:
  - 12 FPS.
  - 16 obstacles.
  - Controls are inverted: Up=Down, Down=Up, Left=Right, Right=Left.
  - The worm apple replaces the golden apple role.
  - The Level 6 worm apple is golden and gives the golden-apple reward (+30).
  - It despawns after a timer and respawns at a safe location.
  - Achievement: LEVEL 6 WORM HUNTER.
- Food/obstacle spawning now avoids the snake, normal apple, special apple, and other obstacles so walls/obstacles do not spawn on food.
- Free Mode leaderboard is no longer limited to five entries. Each player entry can contain score and achievements.
- Free Mode is kept separate from level scores. Only Free Mode contributes to the Free Mode leaderboard.
- Player achievements and personal progress are stored locally in the browser while the game is running as a Pygbag web game.

## Important: Discord login needs a server

A Pygame/Pygbag game should not put the Discord client secret inside `main.py`. Discord OAuth uses a redirect and server-side code exchange. Discord's standard OAuth flow redirects the player back to a URL with a code that is exchanged for tokens; the server then reads the user's Discord identity. See Discord's current OAuth documentation for the standard flow.

This project includes `auth_server.py` as the server-side starting point.

## Discord Developer Portal setup

1. Create an application in the Discord Developer Portal.
2. Open OAuth2.
3. Add this redirect URL for local testing:
   `http://localhost:5000/callback`
4. Copy the Client ID.
5. Copy/reset the Client Secret.
6. Keep the Client Secret on the server only. Never put it in `main.py`, GitHub Pages, or the Pygbag build.

The server requests `identify email`. The email is optional game profile information; the actual game username comes from the Discord username.

## Local setup

Use Python 3.12.x for the project.

Install dependencies:

`python -m pip install -r requirements.txt`

Set environment variables on Windows CMD:

`set DISCORD_CLIENT_ID=YOUR_CLIENT_ID`

`set DISCORD_CLIENT_SECRET=YOUR_CLIENT_SECRET`

`set FLASK_SECRET_KEY=replace-with-a-long-random-secret`

`set GAME_URL=http://localhost:5000/game`

Then run:

`python auth_server.py`

Build the game separately with Pygbag and place its generated web files under `build/web/`, or set `GAME_URL` to the URL where the game is hosted.

## Pygbag

The existing game already uses an async loop and `await asyncio.sleep(0)`, which is required by Pygbag's browser runtime.

Build:

`python -m pygbag SnakeGame`

Then use the generated `build/web/` output for hosting.

## Remaining integration work

The current game-side login reads the username returned by the OAuth server and enforces the login gate. The included Flask server already has endpoints for `/api/me`, `/api/leaderboard`, and `/api/score`.

For a true multi-user online leaderboard, the final step is to connect those API endpoints to the Pygbag client using a browser-compatible async fetch bridge. Do not replace this with a client-side-only username or score system if the leaderboard is meant to be authoritative.

Also, score validation is still client-side. A competitive public leaderboard should eventually validate game results server-side or use a trusted game service.
