import { Fragment, type ReactNode } from "react";

type CoachMarkdownProps = {
  content: string;
};

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "unordered" | "ordered"; items: string[] };

const HEADING_PATTERN = /^(#{1,3})\s+(.+)$/;
const UNORDERED_PATTERN = /^[-*]\s+(.+)$/;
const ORDERED_PATTERN = /^\d+[.)]\s+(.+)$/;

function inlineMarkdown(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <Fragment key={index}>{part}</Fragment>,
  );
}

function parseBlocks(lines: string[]): Block[] {
  const blocks: Block[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }
    const heading = line.match(HEADING_PATTERN);
    if (heading) {
      blocks.push({ kind: "heading", level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }
    const unordered = line.match(UNORDERED_PATTERN);
    const ordered = line.match(ORDERED_PATTERN);
    if (unordered || ordered) {
      const kind = unordered ? "unordered" : "ordered";
      const pattern = unordered ? UNORDERED_PATTERN : ORDERED_PATTERN;
      const items: string[] = [];
      while (index < lines.length) {
        const match = lines[index].trim().match(pattern);
        if (!match) break;
        items.push(match[1]);
        index += 1;
      }
      blocks.push({ kind, items });
      continue;
    }
    const paragraph: string[] = [];
    while (index < lines.length) {
      const candidate = lines[index].trim();
      if (!candidate || HEADING_PATTERN.test(candidate) || UNORDERED_PATTERN.test(candidate) || ORDERED_PATTERN.test(candidate)) break;
      paragraph.push(candidate);
      index += 1;
    }
    blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
  }
  return blocks;
}

function renderBlocks(blocks: Block[], keyPrefix: string): ReactNode[] {
  return blocks.map((block, index) => {
    const key = keyPrefix + "-" + index;
    if (block.kind === "heading") {
      if (block.level === 1) return <h2 key={key}>{inlineMarkdown(block.text)}</h2>;
      return <h3 key={key}>{inlineMarkdown(block.text)}</h3>;
    }
    if (block.kind === "paragraph") return <p key={key}>{inlineMarkdown(block.text)}</p>;
    const items = block.items.map((item, itemIndex) => <li key={itemIndex}>{inlineMarkdown(item)}</li>);
    return block.kind === "ordered" ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>;
  });
}

function cardTone(title: string): "risk" | "action" | null {
  if (/风险提醒|安全提醒|注意事项|身体不适/.test(title)) return "risk";
  if (/今日行动|行动建议|今天怎么做|今天的行动/.test(title)) return "action";
  return null;
}

export function CoachMarkdown({ content }: CoachMarkdownProps) {
  const blocks = parseBlocks(content.replace(/\r\n?/g, "\n").split("\n"));
  const rendered: ReactNode[] = [];
  let index = 0;
  while (index < blocks.length) {
    const block = blocks[index];
    if (block.kind === "heading") {
      const tone = cardTone(block.text);
      if (tone) {
        const children: Block[] = [];
        index += 1;
        while (index < blocks.length && blocks[index].kind !== "heading") {
          children.push(blocks[index]);
          index += 1;
        }
        rendered.push(
          <section className={"coach-markdown-card coach-markdown-card--" + tone} key={"card-" + index}>
            <h3>{tone === "risk" ? "⚠ " : "✓ "}{inlineMarkdown(block.text)}</h3>
            {renderBlocks(children, "card-" + index)}
          </section>,
        );
        continue;
      }
    }
    rendered.push(...renderBlocks([block], "block-" + index));
    index += 1;
  }
  return <div className="coach-markdown">{rendered}</div>;
}
