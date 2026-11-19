import { readFileSync, statSync } from "node:fs";

function parseRelease(file) {
  if (statSync(file).size > 128 * 1024) throw new Error("File release vượt quá 128 KiB.");
  const source = readFileSync(file, "utf8").replace(/^\uFEFF/, "").replace(/\r\n/g, "\n");
  const parts = /^---\n([\s\S]+?)\n---\n([\s\S]*)$/.exec(source);
  if (!parts) throw new Error("File release cần YAML frontmatter và changelog VI/EN.");
  function scalar(key) {
    const lines = parts[1].split("\n").filter(line => line.startsWith(`${key}:`));
    if (lines.length !== 1) throw new Error(`Frontmatter cần đúng một trường ${key}.`);
    return lines[0].slice(key.length + 1).trim().replace(/^(['"])(.*)\1$/, "$2");
  }
  const appId = scalar("app_id");
  const version = scalar("version");
  const tag = `v${version}`;
  if (!/^[a-z][a-z0-9_]{0,31}$/.test(appId) || !/^(?:0|[1-9][0-9]{0,8})(?:\.(?:0|[1-9][0-9]{0,8})){2}$/.test(version)) {
    throw new Error("Cần app_id hợp lệ và version stable X.Y.Z.");
  }
  const changelog = { vi: [], en: [] };
  const sections = parts[2].split(/^##\s+([^\n]+)\n/gm);
  const seen = new Set();
  for (let index = 1; index < sections.length; index += 2) {
    const language = sections[index].trim();
    if (language !== "vi" && language !== "en") continue;
    if (seen.has(language)) throw new Error(`Changelog trùng mục ${language}.`);
    seen.add(language);
    for (const line of sections[index + 1].trim().split("\n")) {
      if (!line.trim()) continue;
      const note = /^-\s+(.+)$/.exec(line.trim())?.[1].trim();
      if (!note || note.length > 240 || Array.from(note).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) {
        throw new Error(`Changelog ${language} yêu cầu bullet text tối đa 240 ký tự.`);
      }
      changelog[language].push(note);
    }
    if (changelog[language].length > 12) throw new Error(`Changelog ${language} vượt quá 12 dòng.`);
  }
  if (!changelog.vi.length || !changelog.en.length) throw new Error("Cần changelog ở cả hai mục ## vi và ## en.");
  return { appId, version, tag, changelog };
}

async function main() {
  const [file, tagOrCheck, unexpected] = process.argv.slice(2);
  if (!file || unexpected) throw new Error("Dùng node scripts/sync_web_release.mjs FILE [TAG | --check].");
  const { appId, version, tag, changelog } = parseRelease(file);
  const expectedApp = process.env.SHOWCASE_RELEASE_APP_ID;
  if (expectedApp && appId !== expectedApp) throw new Error("app_id trong file khác app đang phát hành.");
  if (tagOrCheck === "--check") {
    console.log(`Đã kiểm hồ sơ ${appId} ${tag}.`);
    return;
  }
  if (tagOrCheck && tagOrCheck !== tag) throw new Error("Version trong file khác tag phát hành.");
  const token = process.env.SHOWCASE_RELEASE_SYNC_TOKEN ?? (appId === "vxmedia" ? process.env.VXMEDIA_RELEASE_SYNC_TOKEN : undefined);
  if (!token || !/^[a-f0-9]{64}$/.test(token)) throw new Error("Thiếu SHOWCASE_RELEASE_SYNC_TOKEN hợp lệ.");
  const target = new URL(process.env.RELEASE_SYNC_ORIGIN ?? "https://tools.linhbv.com");
  if (target.origin !== "https://tools.linhbv.com" && !(target.protocol === "http:" && target.hostname === "tools.localhost")) {
    throw new Error("Origin release sync phải là Tools production hoặc Tools preview local.");
  }
  const url = new URL(`/api/releases/v1/apps/${appId}/current`, target.origin);
  async function send(method, body) {
    const gitHubToken = process.env.SHOWCASE_RELEASE_GITHUB_TOKEN ?? (appId === "vxmedia" ? process.env.VXMEDIA_RELEASE_GITHUB_TOKEN : undefined);
    const response = await fetch(url, {
      method, headers: {
        authorization: `Bearer ${token}`, "content-type": "application/json",
        ...(method === "PUT" && gitHubToken ? { "x-release-github-token": gitHubToken } : {}),
      },
      body: body && JSON.stringify(body), redirect: "error", signal: AbortSignal.timeout(15_000),
    });
    const requestId = response.headers.get("x-request-id");
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(`${method} ${response.status} ${data?.error ?? ""} request_id=${requestId ?? "n/a"}`);
    return { data, requestId };
  }
  const { data: current } = await send("GET");
  if (!Number.isSafeInteger(current?.revision) || current.revision < 0) throw new Error("API trả revision không hợp lệ.");
  const { data, requestId } = await send("PUT", { version, tag, changelog, expected_revision: current.revision });
  if (data?.version !== version || data.tag !== tag || !["updated", "unchanged"].includes(data.status)) {
    throw new Error(`API trả kết quả không hợp lệ, request_id=${requestId ?? "n/a"}.`);
  }
  console.log(`${appId} ${tag} ${data.status} revision=${data.revision} request_id=${requestId}`);
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
