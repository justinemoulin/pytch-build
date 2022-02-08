#!/bin/bash

cd_or_fail() { cd "$1" || exit 1; }

. "$PYTCH_REPO_BASE"/pytch-build/venv/bin/activate
cd "$PYTCH_REPO_BASE"/pytch-tutorials

pytchbuild-gather-tutorials --index-source=RECIPES_TIP -o /tmp/pytch-tutorials.zip
mkdir -p site-layer
cd site-layer
unzip -qo /tmp/pytch-tutorials.zip

echo Serving tutorial layer from $(pwd)

python $PYTCH_LOCAL_SERVER_DIR/cors_server.py 8125

