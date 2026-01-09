<script>
  import { marked } from "marked";
  import {
    createEventSource,
    fetchReport,
    fetchRun,
    startRun,
  } from "../api.js";

  let prompt = "";
  let runId = null;
  let status = "idle";
  let events = [];
  let outputMarkdown = "";
  let errors = [];
  let downloading = false;
  let streams = {};
  let streamPanelOpen = true;

  async function handleStartRun() {
    if (!prompt.trim()) {
      return;
    }
    status = "starting";
    events = [];
    outputMarkdown = "";
    errors = [];
    const payload = await startRun(prompt);
    runId = payload.run_id;
    status = "running";
    subscribeEvents();
  }

  function subscribeEvents() {
    const source = createEventSource(runId);
    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type && data.type.startsWith("llm_stream")) {
        handleStreamEvent(data);
        return;
      }
      events = [...events, data];
      if (data.type === "done") {
        status = data.status;
        source.close();
        loadRun();
      }
    };
  }

  function handleStreamEvent(event) {
    const payload = event.payload || {};
    const streamId = payload.stream_id;
    if (!streamId) return;
    if (payload.type === "llm_stream_start") {
      streams = {
        ...streams,
        [streamId]: {
          agent: event.agent,
          prompt: payload.prompt,
          response: "",
          completed: false,
        },
      };
    } else if (payload.type === "llm_stream") {
      const current = streams[streamId] || {
        agent: event.agent,
        prompt: "",
        response: "",
        completed: false,
      };
      streams = {
        ...streams,
        [streamId]: {
          ...current,
          response: current.response + (payload.delta || ""),
        },
      };
    } else if (payload.type === "llm_stream_end") {
      const current = streams[streamId] || {};
      streams = {
        ...streams,
        [streamId]: { ...current, completed: true },
      };
    }
  }

  async function loadRun() {
    const payload = await fetchRun(runId);
    outputMarkdown = payload.output_markdown || "";
    errors = payload.errors || [];
  }

  function formatPayload(payload) {
    if (!payload) return "";
    return JSON.stringify(payload, null, 2);
  }

  async function downloadReport() {
    if (!runId) return;
    downloading = true;
    const blob = await fetchReport(runId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "report.md";
    link.click();
    URL.revokeObjectURL(url);
    downloading = false;
  }
</script>

<main class="page">
  <header class="hero">
    <div class="hero-content">
      <p class="eyebrow">KAERI AR Report Agent</p>
      <h1>증거 기반 보고서 파이프라인</h1>
      <p class="lead">
        프롬프트 입력 → 에이전트 실행 → 실시간 상태 확인 → 결과 다운로드.
      </p>
    </div>
  </header>

  <section class="panel">
    <h2>프롬프트 입력</h2>
    <textarea
      bind:value={prompt}
      rows="10"
      placeholder="보고서 프롬프트를 입력하세요."
    ></textarea>
    <div class="actions">
      <button on:click={handleStartRun} disabled={status === "running"}>
        파이프라인 실행
      </button>
      <span class="status">상태: {status}</span>
    </div>
  </section>

  <section class="panel">
    <h2>실시간 에이전트 로그</h2>
    <div class="log">
      {#if events.length === 0}
        <p class="muted">진행중 로그가 여기에 표시됩니다.</p>
      {:else}
        {#each events as event}
          <div class="log-item">
            <span class="tag">{event.agent || "system"}</span>
            <span>
              <div class="log-title">{event.message || event.status}</div>
              {#if event.payload?.summary}
                <div class="log-summary">{event.payload.summary}</div>
              {/if}
            </span>
            <span class="time">{event.ts}</span>
          </div>
          {#if event.payload}
            <details class="log-details">
              <summary>세부 정보</summary>
              <pre>{formatPayload(event.payload)}</pre>
            </details>
          {/if}
        {/each}
      {/if}
    </div>
  </section>

  <section class="panel">
    <div class="panel-header">
      <h2>LLM 스트리밍</h2>
      <button class="ghost" on:click={() => (streamPanelOpen = !streamPanelOpen)}>
        {streamPanelOpen ? "접기" : "펼치기"}
      </button>
    </div>
    {#if streamPanelOpen}
      {#if Object.keys(streams).length === 0}
        <p class="muted">스트리밍 프롬프트/응답이 여기에 표시됩니다.</p>
      {:else}
        {#each Object.entries(streams) as [streamId, item]}
          <div class="stream-card">
            <div class="stream-header">
              <span class="tag">{item.agent}</span>
              <span class="stream-status">
                {item.completed ? "완료" : "생성 중"}
              </span>
            </div>
            <div class="stream-body">
              <div class="stream-col">
                <h4>프롬프트</h4>
                <pre>{item.prompt}</pre>
              </div>
              <div class="stream-col">
                <h4>응답(실시간)</h4>
                <pre>{item.response}</pre>
              </div>
            </div>
          </div>
        {/each}
      {/if}
    {/if}
  </section>

  <section class="panel">
    <h2>결과</h2>
    {#if runId}
      <div class="actions">
        <button on:click={downloadReport} disabled={downloading}>
          {downloading ? "다운로드 중..." : "보고서 다운로드"}
        </button>
      </div>
    {/if}
    {#if errors.length}
      <div class="errors">
        <h3>Issues</h3>
        <ul>
          {#each errors as issue}
            <li>{issue}</li>
          {/each}
        </ul>
      </div>
    {/if}
    <div class="markdown">{@html marked.parse(outputMarkdown || "")}</div>
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: "IBM Plex Sans", "Noto Sans KR", sans-serif;
    background: radial-gradient(circle at top, #f8f1e5, #f0e7dc 45%, #e6ded0);
    color: #1c1c1c;
  }

  .page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 32px 24px 80px;
  }

  .hero {
    padding: 48px 32px;
    background: linear-gradient(120deg, #212121, #2f2b27);
    color: #f3efe9;
    border-radius: 20px;
    margin-bottom: 32px;
  }

  .hero h1 {
    font-family: "IBM Plex Serif", "Nanum Myeongjo", serif;
    font-size: clamp(2rem, 2.6vw, 3rem);
    margin: 12px 0;
  }

  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-size: 0.8rem;
    opacity: 0.7;
    margin: 0;
  }

  .lead {
    margin: 0;
    max-width: 520px;
    line-height: 1.6;
  }

  .panel {
    background: #ffffffcc;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 18px 40px rgba(31, 24, 16, 0.12);
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
  }

  textarea {
    width: 100%;
    border: 1px solid #d9cdbf;
    border-radius: 12px;
    padding: 16px;
    font-size: 1rem;
    font-family: "IBM Plex Sans", "Noto Sans KR", sans-serif;
    background: #fdfaf6;
  }

  .actions {
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  button {
    border: none;
    border-radius: 999px;
    padding: 12px 24px;
    background: #ed6a3a;
    color: white;
    font-weight: 600;
    cursor: pointer;
  }

  button:disabled {
    background: #c7b9aa;
    cursor: not-allowed;
  }

  .status {
    font-size: 0.95rem;
    color: #49423c;
  }

  .log {
    max-height: 720px;
    min-height: 360px;
    overflow: auto;
    padding: 12px;
    border: 1px solid #e0d4c6;
    border-radius: 12px;
    background: #fbf7f2;
  }

  .log-details {
    margin: 6px 0 12px;
    padding: 10px 12px;
    background: #fff5ea;
    border-radius: 10px;
    border: 1px solid #eadfd3;
  }

  .log-details summary {
    cursor: pointer;
    font-weight: 600;
    color: #3b3027;
  }

  .log-details pre {
    margin: 8px 0 0;
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .log-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 12px;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px dashed #eadfd3;
    font-size: 0.9rem;
  }

  .log-title {
    font-weight: 600;
  }

  .log-summary {
    color: #8d837a;
    font-size: 0.85rem;
    margin-top: 4px;
  }

  .stream-card {
    background: #fff5ea;
    border-radius: 16px;
    padding: 16px;
    margin-top: 12px;
    border: 1px solid #eadfd3;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .ghost {
    border: 1px solid #d9cdbf;
    background: transparent;
    color: #3b3027;
  }

  .stream-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .stream-status {
    font-size: 0.8rem;
    color: #7a6f66;
  }

  .stream-body {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
  }

  .stream-col pre {
    background: #fff;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid #eadfd3;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.85rem;
  }

  .log-item:last-child {
    border-bottom: none;
  }

  .tag {
    font-weight: 700;
    color: #3b3027;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
  }

  .time {
    font-size: 0.7rem;
    color: #7a6f66;
  }

  .muted {
    color: #7a6f66;
  }

  .markdown {
    margin-top: 16px;
    line-height: 1.7;
  }

  .errors {
    background: #ffe8de;
    padding: 16px;
    border-radius: 12px;
    margin-top: 16px;
  }

  @media (max-width: 768px) {
    .actions {
      flex-direction: column;
      align-items: flex-start;
    }
    .log-item {
      grid-template-columns: 1fr;
      gap: 4px;
    }
  }
</style>
