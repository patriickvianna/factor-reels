#!/usr/bin/env bash
# Abre a gravação de referência da voz do PTK: o arquivo fica cifrado no repositório (público)
# e a chave só é entregue pelo Supabase ao robô deste repositório (token OIDC do GitHub).
set -euo pipefail
[ -f voz/ptk.flac.enc ] || { echo "sem gravação do PTK"; exit 0; }
KEY=$(.github/scripts/api.sh '{"action":"chave","name":"voz_ptk"}' | jq -r '.value // empty')
[ -n "$KEY" ] || { echo "chave da voz indisponível"; exit 0; }
echo "::add-mask::$KEY"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in voz/ptk.flac.enc -out /tmp/ptk.flac -pass "pass:$KEY"
ffmpeg -v error -y -i /tmp/ptk.flac -ac 1 -ar 24000 voz/ptk.wav && rm -f /tmp/ptk.flac
echo "voz do PTK pronta ($(ffprobe -v error -show_entries format=duration -of csv=p=0 voz/ptk.wav)s)"
