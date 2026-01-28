import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const projectRoot = process.cwd();
const targetDirs = ["app", "components"];
const allowedProps = new Set([
  "className",
  "id",
  "role",
  "type",
  "href",
  "rel",
  "target",
  "lang",
  "variant", 
  "size",
  "open",
  "asChild"
]);

const allowedDataPrefixes = ["data-"];

const violations = [];

function isAllowedAttribute(name) {
  if (allowedProps.has(name)) {
    return true;
  }

  // SVG attributes
  const svgAttrs = new Set([
    'width', 'height', 'viewBox', 'd', 'fill', 'stroke', 'strokeWidth',
    'strokeLinecap', 'strokeLinejoin', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 
    'cx', 'cy', 'r', 'points', 'transform', 'offset', 'stopColor', 
    'stopOpacity', 'strokeDasharray', 'dataKey', 'fontSize', 'tickLine', 'axisLine', 'minTickGap', 'vertical', 'dy'
  ]);
  
  if (svgAttrs.has(name)) return true;

  return allowedDataPrefixes.some((prefix) => name.startsWith(prefix));
}

function collectFiles(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next") {
        continue;
      }
      files.push(...collectFiles(fullPath));
    } else if (entry.isFile()) {
      if (fullPath.endsWith(".tsx")) {
        files.push(fullPath);
      }
    }
  }

  return files;
}

function reportViolation(sourceFile, node, message) {
  const position = sourceFile.getLineAndCharacterOfPosition(node.getStart());
  const relativePath = path.relative(projectRoot, sourceFile.fileName);
  violations.push(`${relativePath}:${position.line + 1}:${position.character + 1} ${message}`);
}

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    content,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );

  function visit(node) {
    if (ts.isJsxText(node)) {
      const text = node.getText().replace(/\s+/g, " ").trim();
      if (text.length > 0) {
        reportViolation(sourceFile, node, "JSX text must come from translations");
      }
    }

    if (ts.isJsxExpression(node) && node.expression) {
      if (
        ts.isStringLiteral(node.expression) ||
        ts.isNoSubstitutionTemplateLiteral(node.expression)
      ) {
        reportViolation(sourceFile, node, "String literals must come from translations");
      }
    }

    if (ts.isJsxAttribute(node)) {
      const name = node.name.getText();
      const initializer = node.initializer;

      if (initializer && !isAllowedAttribute(name)) {
        if (ts.isStringLiteral(initializer)) {
          reportViolation(sourceFile, node, `Attribute "${name}" must come from translations`);
        }

        if (
          ts.isJsxExpression(initializer) &&
          initializer.expression &&
          (ts.isStringLiteral(initializer.expression) ||
            ts.isNoSubstitutionTemplateLiteral(initializer.expression))
        ) {
          reportViolation(sourceFile, node, `Attribute "${name}" must come from translations`);
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
}

for (const dir of targetDirs) {
  const absoluteDir = path.join(projectRoot, dir);
  if (fs.existsSync(absoluteDir)) {
    const files = collectFiles(absoluteDir);
    for (const file of files) {
      checkFile(file);
    }
  }
}

if (violations.length > 0) {
  console.error("Hardcoded UI string check failed:");
  for (const violation of violations) {
    console.error(`- ${violation}`);
  }
  process.exit(1);
}

console.log("Hardcoded UI string check passed.");
