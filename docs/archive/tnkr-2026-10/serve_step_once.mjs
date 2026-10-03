// 一次性静态文件服务器：供 Tnkr 页面(HTTPS) fetch 本地装配体 STEP，绕过原生文件选择器。
// 用法: node tools/serve_step_once.mjs <文件路径>   (默认端口 8765, 仅绑定 127.0.0.1)
// 特性: CORS * + Private Network Access 头（Chrome 允许 https 页面访问 localhost 信源）
import http from "node:http";
import { readFile } from "node:fs/promises";

const FILE = process.argv[2];
const PORT = Number(process.argv[3] || 8765);
if (!FILE) {
  console.error("usage: node serve_step_once.mjs <file> [port]");
  process.exit(1);
}
const data = await readFile(FILE);
const server = http.createServer((req, res) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Private-Network": "true",
    "Content-Type": "application/octet-stream",
    "Content-Length": data.length,
  };
  if (req.method === "OPTIONS") {
    res.writeHead(204, headers);
    res.end();
    return;
  }
  res.writeHead(200, headers);
  res.end(req.method === "HEAD" ? undefined : data);
});
server.listen(PORT, "127.0.0.1", () => {
  console.log(`SERVE_READY port=${PORT} bytes=${data.length}`);
});
