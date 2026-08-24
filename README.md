# ARC-AGI Tasks Viewer

[arc-agi-task-viewer](https://ironbar.github.io/arc-agi-task-viewer/)

A tiny static website for browsing complete ARC-AGI-1 and ARC-AGI-2 public tasks with locally generated thumbnails.

## Local thumbnail prototype

`scripts/generate_thumbnails.py` creates PNG thumbnails directly from the public ARC task JSON files. It uses only the Python standard library and the original ARC palette. Every example appears in one horizontal sequence with its input above its output. Training examples come first on white, followed by test examples on gray, and one-pixel lines make every grid cell distinct.

All 1,920 public-task thumbnails are checked into `thumbnails/`. The default gallery loads them in small batches, while the original ARC Prize-thumbnail table remains available at `legacy.html`.

To reproduce them, clone the official datasets outside this repository and run:

```sh
python3 scripts/generate_thumbnails.py \
  --source /path/to/ARC-AGI/data/training \
  --output thumbnails/arc1-training \
  --task 007bbfb7
```

Repeat `--task` to select several tasks, or omit it to generate the entire source directory. The public data comes from the official [ARC-AGI-1](https://github.com/fchollet/ARC-AGI) and [ARC-AGI-2](https://github.com/arcprize/ARC-AGI-2) repositories.

## Local Preview

Open `index.html` directly in a browser, or serve the folder with any static file server.

## GitHub Pages

Publish the repository from the `main` branch root in GitHub Pages settings. No build command is needed.
