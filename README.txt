# Snake Game - Pygbag Version

This is your Pygame Snake game modified so it can be packaged for the web with Pygbag.

## Run normally on your computer

Install Pygame:

```bash
python -m pip install pygame
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
