# Factor Reels

Robô que monta os Reels da **Factor Ofertas**: roteiro, voz, legenda, música e conferência de som, tudo com ferramentas gratuitas.

- **Fila:** o painel (factor-ofertas.vercel.app › Instagram › Reels) e o plano diário colocam pedidos no Supabase.
- **Robô:** este repositório olha a fila a cada 15 minutos (GitHub Actions) e só monta o ambiente quando há trabalho.
- **Login:** o robô entra no Supabase com o token OIDC do próprio GitHub. Não há senha ou chave guardada aqui.
- **Entrega:** cada vídeo vira um Release (`reel-…`) com 3 arquivos: com música, só com voz e a capa. Apagados após 14 dias.

| Parte | Ferramenta | Licença |
|---|---|---|
| Voz | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) via kokoro-onnx (vozes pf_dora, pm_alex, pm_santa) | Apache 2.0 |
| Pronúncia | eSpeak NG | GPL (ferramenta, não vai no vídeo) |
| Imagem | Chromium (Playwright) quadro a quadro + FFmpeg | — |
| Música | [FreePD.com](https://freepd.com) | CC0 1.0 |
| Fonte | Space Grotesk | OFL |

Padrão de som: −14 LUFS integrado, pico verdadeiro ≤ −1 dBTP, 48 kHz AAC 192k. Fora disso, o vídeo é barrado.

Teste local: `TTS_ENGINE=espeak python render/main.py --local alerta` (gera em `out/`).
