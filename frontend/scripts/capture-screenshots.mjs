import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const OUT = path.resolve("..", "docs", "screenshots");
const BASE = process.env.UI_URL ?? "http://localhost:5173";

const tree = [
  {
    name: "app",
    path: "app",
    kind: "dir",
    language: null,
    children: [
      { name: "auth.py", path: "app/auth.py", kind: "file", language: "python", children: [] },
      { name: "deps.py", path: "app/deps.py", kind: "file", language: "python", children: [] },
      { name: "main.py", path: "app/main.py", kind: "file", language: "python", children: [] },
      { name: "models.py", path: "app/models.py", kind: "file", language: "python", children: [] },
      { name: "store.py", path: "app/store.py", kind: "file", language: "python", children: [] },
      {
        name: "routes",
        path: "app/routes",
        kind: "dir",
        language: null,
        children: [
          { name: "todos.py", path: "app/routes/todos.py", kind: "file", language: "python", children: [] },
          { name: "users.py", path: "app/routes/users.py", kind: "file", language: "python", children: [] },
        ],
      },
      {
        name: "services",
        path: "app/services",
        kind: "dir",
        language: null,
        children: [
          {
            name: "todo_service.py",
            path: "app/services/todo_service.py",
            kind: "file",
            language: "python",
            children: [],
          },
        ],
      },
    ],
  },
  { name: "pyproject.toml", path: "pyproject.toml", kind: "file", language: "toml", children: [] },
  { name: "README.md", path: "README.md", kind: "file", language: "markdown", children: [] },
];

const authPy = `from fastapi import Header, HTTPException

API_KEY_HEADER = "X-API-Key"


def authenticate(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    return x_api_key
`;

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.route("**/api/ready", (route) =>
  route.fulfill({ json: { ingested: false, llm_configured: true, name: "" } }),
);
await page.route("**/api/sources", (route) =>
  route.fulfill({ json: { ingested: false, name: "", file_count: 0, chunk_count: 0, tree: [] } }),
);
await page.goto(BASE, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: /Ask a repository/ }).waitFor();
await page.screenshot({ path: path.join(OUT, "onboarding.png"), fullPage: true });

await page.unroute("**/api/ready");
await page.unroute("**/api/sources");
await page.route("**/api/ready", (route) =>
  route.fulfill({ json: { ingested: true, llm_configured: true, name: "nexus-tasks" } }),
);
await page.route("**/api/sources", (route) =>
  route.fulfill({
    json: {
      ingested: true,
      name: "nexus-tasks",
      source: "sample",
      file_count: 10,
      chunk_count: 24,
      tree,
    },
  }),
);
await page.route("**/api/sources/content**", (route) =>
  route.fulfill({ json: { path: "app/auth.py", content: authPy } }),
);
await page.reload({ waitUntil: "networkidle" });
await page.getByText("auth.py", { exact: true }).click();
await page.getByText('API_KEY_HEADER = "X-API-Key"').waitFor();
await page.getByText("deps.py", { exact: true }).click();
await page.getByRole("tab", { name: "auth.py" }).click();

const splitter = page.getByRole("separator", { name: "Resize code panel" });
const splitterBefore = await splitter.boundingBox();
if (!splitterBefore) {
  throw new Error("Code panel splitter is not visible");
}
await page.mouse.move(splitterBefore.x + 2, splitterBefore.y + splitterBefore.height / 2);
await page.mouse.down();
await page.mouse.move(splitterBefore.x - 80, splitterBefore.y + splitterBefore.height / 2);
await page.mouse.up();
const splitterAfter = await splitter.boundingBox();
if (!splitterAfter || splitterAfter.x >= splitterBefore.x) {
  throw new Error("Dragging the splitter did not expand the code panel");
}

await page.screenshot({ path: path.join(OUT, "workspace.png") });

await browser.close();
