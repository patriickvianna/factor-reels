#!/usr/bin/env bash
# Junta as partes do Reels explicativo 3D (renderizadas em máquinas separadas) e coloca a voz.
#   join-explica.sh pasta_das_partes voz.wav saida.mp4
# As partes são do mesmo codec e tamanho: a junção copia o vídeo sem recodificar (sem perder qualidade).
set -euo pipefail
dir="$1"; voz="$2"; out="$3"
for f in $(ls "$dir"/p*.mp4 | sort -V); do echo "file '$(realpath "$f")'"; done > "$dir/lista.txt"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$dir/lista.txt" -i "$voz" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$out"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out"
