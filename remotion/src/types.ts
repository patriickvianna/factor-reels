// Formato que o robô (Python) entrega para o Remotion. Tempos em segundos, contados do início do vídeo.

export type Word = { text: string; start: number; end: number };

// words: instante de cada palavra, ouvido pelo Whisper. voz: "outra" quando o 2º personagem fala.
export type Line = { text: string; start: number; end: number; words?: Word[]; voz?: string };
export type Fala = { quem?: string; emocao?: string; reacao?: string };
export type CaptionPage = { start: number; end: number; words: Word[] };

export type SceneBase = { start: number; end: number; lines: Line[] };

export type Scene = SceneBase &
  (
    | { type: "gancho"; kicker?: string; titulo: string; destaque?: string }
    | { type: "numero"; numero: string; rotulo: string; kicker?: string }
    | { type: "lista"; titulo: string; itens: string[]; kicker?: string }
    | { type: "mito_verdade"; mito: string; verdade: string }
    | { type: "passos"; titulo: string; passos: string[] }
    | { type: "comparacao"; titulo?: string; esquerda: { titulo: string; itens: string[] }; direita: { titulo: string; itens: string[] } }
    | { type: "pergunta"; pergunta: string; opcoes: string[] }
    | { type: "destaque"; antes?: string; destaque: string; depois?: string; kicker?: string }
    | { type: "produto"; kicker?: string; nome: string; imagem: string; desconto?: number }
    | { type: "preco"; nome: string; imagem: string; de?: string | null; por: string; desconto?: number }
    | { type: "prova"; imagem: string; selos: string[] }
    | { type: "produtos"; titulo: string; sub?: string; imagens: string[]; kicker?: string }
    | { type: "item"; indice: number; total: number; nome: string; imagem: string; por: string; desconto?: number }
    | { type: "historia"; personagens: string[]; lugar?: string; falas?: Fala[]; inicio?: Record<string, string>; nomes?: Record<string, string> }
    | { type: "chat"; personagens: string[]; contato?: string; falas?: Fala[] }
    | { type: "tela"; titulo: string; itens: { rotulo: string; valor: string; riscado?: boolean; alerta?: boolean }[]; total?: string; carimbo?: string }
    | { type: "cta"; handle: string; oferta?: number | null; ofertas?: number[] | null; salvar?: boolean }
  );

export type ReelProps = {
  scenes: Scene[];
  pages: CaptionPage[];
  audio: string; // arquivo dentro de public/
  duration: number;
  handle: string;
  modelo?: "v1" | "v2";
};
