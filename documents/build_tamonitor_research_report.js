#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  Header,
  HeadingLevel,
  ImageRun,
  Math: DocxMath,
  MathFraction,
  MathRun,
  MathSubScript,
  MathSubSuperScript,
  MathSuperScript,
  PageBreak,
  PageNumber,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableLayoutType,
  TableOfContents,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} = require(process.platform === "win32"
  ? "C:/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx"
  : "/mnt/c/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx");

const repoRoot = path.resolve(__dirname, "..");
const sourcePath = path.join(__dirname, "基于运行时验证的安全性质违反精确判定方法研究报告.md");
const outputPath = path.join(__dirname, "基于运行时验证的安全性质违反精确判定方法研究报告.docx");
const markdown = fs.readFileSync(sourcePath, "utf8").replace(/\r\n/g, "\n");

const fonts = {
  body: "宋体",
  heading: "黑体",
  latin: "Times New Roman",
  code: "Consolas",
};

function stripMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^>\s?/, "")
    .trim();
}

function readBraceGroup(source, start) {
  if (source[start] !== "{") throw new Error(`Expected '{' in math expression: ${source}`);
  let depth = 0;
  for (let index = start; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return { text: source.slice(start + 1, index), end: index + 1 };
  }
  throw new Error(`Unclosed math group: ${source}`);
}

function normalizeMathSource(source) {
  return source
    .replace(/\\operatorname\{([^{}]+)\}/g, "$1")
    .replace(/\\mathbf\{([^{}]+)\}/g, "$1")
    .replace(/\\varphi/g, "φ")
    .replace(/\\rho/g, "ρ")
    .replace(/\\sigma/g, "σ")
    .replace(/\\pi/g, "π")
    .replace(/\\beta/g, "β")
    .replace(/\\neg/g, "¬")
    .replace(/\\subseteq/g, "⊆")
    .replace(/\\in/g, "∈")
    .replace(/\\le/g, "≤")
    .replace(/\\ge/g, "≥")
    .replace(/\\ne/g, "≠")
    .replace(/\\varnothing/g, "∅")
    .replace(/\\cap/g, "∩")
    .replace(/\\cup/g, "∪")
    .replace(/\\rightarrow/g, "→")
    .replace(/\\Longleftrightarrow/g, "⇔")
    .replace(/\\times/g, "×")
    .replace(/\\cdot/g, "·")
    .replace(/\\cdots|\\ldots/g, "…")
    .replace(/\\qquad/g, "   ")
    .replace(/\\quad/g, "  ")
    .replace(/\\bigl|\\bigr|\\left|\\right/g, "")
    .replace(/\\!/g, "")
    .replace(/\\%/g, "%")
    .replace(/\\\{/g, "{")
    .replace(/\\\}/g, "}")
    .trim();
}

function scriptedMath(base, subScript, superScript) {
  const children = [new MathRun(base)];
  if (subScript !== undefined && superScript !== undefined) {
    return new MathSubSuperScript({
      children,
      subScript: mathComponents(subScript),
      superScript: mathComponents(superScript),
    });
  }
  if (subScript !== undefined) {
    return new MathSubScript({ children, subScript: mathComponents(subScript) });
  }
  if (superScript !== undefined) {
    return new MathSuperScript({ children, superScript: mathComponents(superScript) });
  }
  return new MathRun(base);
}

function mathComponents(rawSource) {
  const source = normalizeMathSource(rawSource);
  const components = [];
  let plain = "";
  let index = 0;

  const flushPlain = () => {
    if (plain) components.push(new MathRun(plain));
    plain = "";
  };

  while (index < source.length) {
    if (source.startsWith("\\frac", index)) {
      flushPlain();
      const numerator = readBraceGroup(source, index + 5);
      const denominator = readBraceGroup(source, numerator.end);
      components.push(new MathFraction({
        numerator: mathComponents(numerator.text),
        denominator: mathComponents(denominator.text),
      }));
      index = denominator.end;
      continue;
    }

    const atom = source.slice(index).match(/^([A-Za-z0-9\u0370-\u03FF]+)(?:_(?:\{([^{}]*)\}|([^\s]))){0,1}(?:\^(?:\{([^{}]*)\}|([^\s]))){0,1}/);
    if (atom && atom[0]) {
      flushPlain();
      components.push(scriptedMath(atom[1], atom[2] ?? atom[3], atom[4] ?? atom[5]));
      index += atom[0].length;
      continue;
    }

    plain += source[index];
    index += 1;
  }
  flushPlain();
  return components.length ? components : [new MathRun("")];
}

function mathObject(source) {
  return new DocxMath({ children: mathComponents(source) });
}

function inlineRuns(text, options = {}) {
  const runs = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\$[^$]+\$)/g;
  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      runs.push(new TextRun({
        text: text.slice(last, match.index),
        font: options.font || fonts.body,
        size: options.size || 21,
      }));
    }
    const token = match[0];
    if (token.startsWith("$")) {
      runs.push(mathObject(token.slice(1, -1)));
    } else if (token.startsWith("**")) {
      runs.push(new TextRun({
        text: token.slice(2, -2),
        bold: true,
        font: options.font || fonts.body,
        size: options.size || 21,
      }));
    } else {
      runs.push(new TextRun({
        text: token.slice(1, -1),
        font: fonts.code,
        size: options.codeSize || 19,
        color: "1F4E79",
      }));
    }
    last = regex.lastIndex;
  }
  if (last < text.length) {
    runs.push(new TextRun({
      text: text.slice(last),
      font: options.font || fonts.body,
      size: options.size || 21,
    }));
  }
  return runs.length ? runs : [new TextRun({ text: "", font: fonts.body, size: 21 })];
}

function bodyParagraph(text, opts = {}) {
  return new Paragraph({
    children: inlineRuns(text, opts),
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    indent: opts.indent || { firstLine: 420 },
    spacing: { line: 360, after: 120, before: opts.before || 0 },
    keepNext: false,
  });
}

function headingParagraph(text, level) {
  const sizes = {
    [HeadingLevel.HEADING_1]: 32,
    [HeadingLevel.HEADING_2]: 28,
    [HeadingLevel.HEADING_3]: 24,
    [HeadingLevel.HEADING_4]: 22,
  };
  return new Paragraph({
    heading: level,
    children: [new TextRun({
      text,
      font: fonts.heading,
      bold: true,
      size: sizes[level] || 24,
    })],
    spacing: { before: level === HeadingLevel.HEADING_1 ? 360 : 240, after: 160 },
    keepNext: true,
    pageBreakBefore: text === "参考文献" || text.startsWith("2.4 实验设计与结果分析"),
  });
}

function listParagraph(text, ordered) {
  return new Paragraph({
    children: inlineRuns(text),
    bullet: ordered ? undefined : { level: 0 },
    indent: ordered ? { left: 420, hanging: 360 } : undefined,
    spacing: { line: 330, after: 80 },
  });
}

function codeParagraph(lines) {
  const children = [];
  lines.forEach((line, index) => {
    children.push(new TextRun({ text: line, font: fonts.code, size: 18 }));
    if (index !== lines.length - 1) children.push(new TextRun({ break: 1 }));
  });
  return new Paragraph({
    children,
    shading: { type: ShadingType.CLEAR, fill: "F3F6F9" },
    border: {
      left: { style: BorderStyle.SINGLE, size: 10, color: "5B9BD5" },
    },
    indent: { left: 360, right: 240 },
    spacing: { before: 120, after: 160, line: 280 },
  });
}

function displayMathParagraph(source) {
  return new Paragraph({
    children: [mathObject(source.replace(/\s+/g, " ").trim())],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 180, line: 320 },
    keepLines: true,
  });
}

function pngDimensions(filePath) {
  const buffer = fs.readFileSync(filePath);
  const signature = buffer.subarray(1, 4).toString("ascii");
  if (signature !== "PNG") throw new Error(`Only PNG figures are supported: ${filePath}`);
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20), buffer };
}

function imageBlocks(relativePath, caption) {
  const filePath = path.resolve(__dirname, relativePath);
  if (!filePath.startsWith(path.resolve(__dirname) + path.sep)) {
    throw new Error(`Figure path escapes the report directory: ${relativePath}`);
  }
  if (!fs.existsSync(filePath)) throw new Error(`Figure not found: ${filePath}`);
  const { width, height, buffer } = pngDimensions(filePath);
  const maxWidth = 600;
  const maxHeight = 610;
  const scale = Math.min(maxWidth / width, maxHeight / height, 1);
  const renderWidth = Math.round(width * scale);
  const renderHeight = Math.round(height * scale);
  return [
    new Paragraph({
      children: [new ImageRun({
        type: "png",
        data: buffer,
        transformation: { width: renderWidth, height: renderHeight },
      })],
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 70 },
      keepNext: true,
    }),
    new Paragraph({
      children: [new TextRun({ text: caption, font: fonts.body, size: 19 })],
      alignment: AlignmentType.CENTER,
      spacing: { after: 180 },
      keepLines: true,
    }),
  ];
}

function parseTable(lines) {
  const rows = lines
    .filter((_, index) => index !== 1)
    .map((line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()));
  const columnCount = Math.max(...rows.map((row) => row.length));
  const width = Math.floor(9000 / columnCount);
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    rows: rows.map((row, rowIndex) => new TableRow({
      tableHeader: rowIndex === 0,
      children: Array.from({ length: columnCount }, (_, cellIndex) => new TableCell({
        width: { size: width, type: WidthType.DXA },
        verticalAlign: VerticalAlign.CENTER,
        shading: rowIndex === 0 ? { type: ShadingType.CLEAR, fill: "D9EAF7" } : undefined,
        margins: { top: 80, bottom: 80, left: 100, right: 100 },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" },
          left: { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" },
          right: { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" },
        },
        children: [new Paragraph({
          children: inlineRuns(row[cellIndex] || "", { size: 19, codeSize: 17 }),
          alignment: cellIndex === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          spacing: { line: 270, after: 0 },
        })],
      })),
    })),
  });
}

function classifyHeading(raw, marks) {
  const text = stripMarkdown(raw.slice(marks.length));
  if (marks === "#") return [text, HeadingLevel.HEADING_1];
  if (marks === "##") return [text, HeadingLevel.HEADING_2];
  if (marks === "###") return [text, HeadingLevel.HEADING_3];
  return [text, HeadingLevel.HEADING_4];
}

function parseBody(lines) {
  const children = [];
  let paragraph = [];
  let inCode = false;
  let code = [];
  let tocInserted = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const text = paragraph.join(" ").trim();
    if (text) children.push(bodyParagraph(text));
    paragraph = [];
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];

    if (line.trim() === "$$") {
      flushParagraph();
      const mathLines = [];
      i += 1;
      while (i < lines.length && lines[i].trim() !== "$$") {
        mathLines.push(lines[i].trim());
        i += 1;
      }
      if (i >= lines.length) throw new Error("Unclosed display math block");
      children.push(displayMathParagraph(mathLines.join(" ")));
      continue;
    }

    if (line.startsWith("```")) {
      flushParagraph();
      if (!inCode) {
        inCode = true;
        code = [];
      } else {
        inCode = false;
        children.push(codeParagraph(code));
      }
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }

    const image = line.match(/^!\[([^\]]+)\]\(([^)]+)\)\s*$/);
    if (image) {
      flushParagraph();
      children.push(...imageBlocks(image[2], image[1]));
      continue;
    }

    if (/^\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\|?\s*:?-+/.test(lines[i + 1])) {
      flushParagraph();
      const tableLines = [line, lines[i + 1]];
      i += 2;
      while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) {
        tableLines.push(lines[i]);
        i += 1;
      }
      i -= 1;
      children.push(parseTable(tableLines));
      children.push(new Paragraph({ spacing: { after: 120 } }));
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      const [text, level] = classifyHeading(line, heading[1]);
      if (text === "1 基于时间自动机引导的模糊测试框架" && !tocInserted) {
        children.push(new Paragraph({ children: [new PageBreak()] }));
        children.push(headingParagraph("目录", HeadingLevel.HEADING_1));
        children.push(new TableOfContents("", { hyperlink: true, headingStyleRange: "1-4" }));
        children.push(new Paragraph({ children: [new PageBreak()] }));
        tocInserted = true;
      }
      children.push(headingParagraph(text, level));
      continue;
    }

    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      flushParagraph();
      children.push(listParagraph(unordered[1], false));
      continue;
    }
    const ordered = line.match(/^(\d+)[.]\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      children.push(listParagraph(`${ordered[1]}. ${ordered[2]}`, true));
      continue;
    }
    if (line.startsWith(">")) {
      flushParagraph();
      children.push(new Paragraph({
        children: inlineRuns(stripMarkdown(line)),
        shading: { type: ShadingType.CLEAR, fill: "FFF2CC" },
        border: { left: { style: BorderStyle.SINGLE, size: 10, color: "C9A227" } },
        indent: { left: 360, right: 240 },
        spacing: { line: 330, before: 120, after: 120 },
      }));
      continue;
    }
    if (/^\[\d+\]\s+/.test(line)) {
      flushParagraph();
      children.push(new Paragraph({
        children: inlineRuns(line, { size: 19, codeSize: 18 }),
        indent: { left: 420, hanging: 420 },
        spacing: { line: 300, after: 100 },
      }));
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      continue;
    }
    paragraph.push(line.trim().replace(/\s{2}$/g, ""));
  }
  flushParagraph();
  return children;
}

const lines = markdown.split("\n");
const bodyStartIndex = lines.findIndex((line) => line.trim() === "# 摘要");
if (bodyStartIndex < 0) throw new Error("Markdown source does not contain the abstract section");

const title = stripMarkdown(lines[0].replace(/^#\s+/, ""));
const stage = stripMarkdown(lines.find((line) => line.includes("阶段版本")) || "阶段版本：运行时验证部分");
const subject = stripMarkdown(lines.find((line) => line.includes("研究对象")) || "研究对象：TAMonitor");
const date = stripMarkdown(lines.find((line) => line.includes("编制日期")) || "编制日期：2026 年 7 月 27 日");

const cover = [
  new Paragraph({ spacing: { before: 1800, after: 600 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: title, font: fonts.heading, bold: true, size: 48 })],
    spacing: { line: 520, after: 900 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: stage, font: fonts.heading, size: 28 })],
    spacing: { after: 240 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: subject, font: fonts.body, size: 26 })],
    spacing: { after: 240 },
  }),
  new Paragraph({ spacing: { before: 1700 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: date, font: fonts.body, size: 24 })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

const body = parseBody(lines.slice(bodyStartIndex));

const document = new Document({
  creator: "TAFuzz / TAMonitor",
  title,
  subject: "运行时验证方法研究报告",
  description: "基于当前仓库 TAMonitor 实现与 Zotero 相关文献形成的阶段研究报告",
  settings: { updateFields: true },
  styles: {
    default: {
      document: {
        run: { font: fonts.body, size: 21, color: "000000" },
        paragraph: { spacing: { line: 360, after: 120 } },
      },
    },
    paragraphStyles: [
      {
        id: "Title",
        name: "Title",
        basedOn: "Normal",
        next: "Normal",
        run: { font: fonts.heading, size: 48, bold: true },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { after: 600 } },
      },
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: fonts.heading, size: 32, bold: true },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: fonts.heading, size: 28, bold: true },
        paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 },
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: fonts.heading, size: 24, bold: true },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 },
      },
      {
        id: "Heading4",
        name: "Heading 4",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: fonts.heading, size: 22, bold: true },
        paragraph: { spacing: { before: 150, after: 90 }, outlineLevel: 3 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        size: { orientation: "portrait" },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "基于运行时验证的安全性质违反精确判定方法研究报告", font: fonts.body, size: 18, color: "666666" })],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" } },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "— ", font: fonts.body, size: 18 }),
            new TextRun({ children: [PageNumber.CURRENT], font: fonts.body, size: 18 }),
            new TextRun({ text: " —", font: fonts.body, size: 18 }),
          ],
        })],
      }),
    },
    children: [...cover, ...body],
  }],
});

Packer.toBuffer(document).then((buffer) => {
  fs.writeFileSync(outputPath, buffer);
  process.stdout.write(JSON.stringify({
    source: sourcePath,
    output: outputPath,
    bytes: buffer.length,
    repo_root: repoRoot,
  }, null, 2) + "\n");
});
