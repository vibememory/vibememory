export type SearchMode = "exact" | "semantic" | "hybrid";
export type Memory = {
  id: string;
  kind: "memory";
  content: string;
  keywords: string[];
  version: number;
  created_at: string;
  correction_status?: string;
};
export type SearchHit = {
  id: string;
  score: number;
  matched_keywords: Array<{
    query_keyword: string;
    stored_keyword: string;
    similarity: number;
  }>;
};
export type Page<T> = {items: T[]; limit: number; offset: number};
export type BatchItem<T = unknown> = {
  index: number;
  client_request_id: string;
  status: "created" | "updated" | "existing" | "conflict" | "failed";
  id?: string;
  version?: number;
  resource?: T;
  error?: {code: string; message: string; retryable: boolean};
};
export type BatchResult<T = unknown> = {
  items: Array<BatchItem<T>>;
  counts: Record<string, number>;
  total: number;
  atomic: false;
};
export type RequestOptions = {signal?: AbortSignal; timeoutMs?: number};

type ErrorContract = {
  reason_code?: string;
  retryable?: boolean;
  request_id?: string;
};

export class VibeMemoryError extends Error {
  readonly code?: string;
  readonly retryable: boolean;
  readonly requestId?: string;

  constructor(
    readonly status: number,
    readonly body: string,
    contract: ErrorContract = {},
  ) {
    super(`Vibe Memory ${status}: ${contract.reason_code ?? body}`);
    this.name = "VibeMemoryError";
    this.code = contract.reason_code;
    this.retryable = Boolean(contract.retryable);
    this.requestId = contract.request_id;
  }
}

export class VibeMemoryClient {
  constructor(
    private baseUrl: string,
    private token: string,
    private namespace = "default",
    private contractVersion = "1.1",
  ) {}

  private async request<T>(
    path: string,
    init: RequestInit = {},
    retry = false,
    options: RequestOptions = {},
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort("timeout"), options.timeoutMs ?? 20_000);
    const cancel = () => controller.abort(options.signal?.reason);
    if (options.signal?.aborted) cancel();
    else options.signal?.addEventListener("abort", cancel, {once: true});
    try {
      const response = await fetch(new URL(path, this.baseUrl), {
        ...init,
        signal: controller.signal,
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${this.token}`,
          "x-vibe-memory-namespace": this.namespace,
          "vibe-memory-contract-version": this.contractVersion,
          ...init.headers,
        },
      });
      if (response.status === 429 && retry) {
        const delay = Math.min(Number(response.headers.get("retry-after") || 1), 30);
        await new Promise<void>((resolve, reject) => {
          const retryTimer = setTimeout(resolve, Math.max(delay, 0) * 1000);
          controller.signal.addEventListener(
            "abort",
            () => {
              clearTimeout(retryTimer);
              reject(controller.signal.reason);
            },
            {once: true},
          );
        });
        return this.request<T>(path, init, false, options);
      }
      if (!response.ok) {
        const body = await response.text();
        let contract: ErrorContract = {};
        try {
          contract = (JSON.parse(body) as {error?: ErrorContract}).error ?? {};
        } catch {
          // Non-JSON gateways remain visible through the raw body.
        }
        throw new VibeMemoryError(response.status, body, contract);
      }
      return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener("abort", cancel);
    }
  }

  get(id: string, options: RequestOptions = {}) {
    return this.request<Memory>(`/v1/records/${encodeURIComponent(id)}`, {}, false, options);
  }

  search(keywords: string[], match_mode: SearchMode = "hybrid", options: RequestOptions = {}) {
    return this.request<{hits: SearchHit[]}>(
      "/v1/search",
      {method: "POST", body: JSON.stringify({keywords, match_mode})},
      true,
      options,
    );
  }

  create(
    content: string,
    keywords: string[],
    client_request_id?: string,
    options: RequestOptions = {},
  ) {
    return this.request<Memory>(
      "/v1/memories",
      {method: "POST", body: JSON.stringify({content, keywords, kind: "fact", client_request_id})},
      Boolean(client_request_id),
      options,
    );
  }

  correct(
    previous_id: string,
    expected_previous_version: number,
    replacement: {content: string; keywords: string[]},
    reason: string,
    client_request_id: string,
    options: RequestOptions = {},
  ) {
    return this.request(
      "/v1/corrections/memories",
      {
        method: "POST",
        body: JSON.stringify({
          previous_id,
          expected_previous_version,
          replacement: {...replacement, kind: "fact"},
          relation: "CORRECTS",
          correction_scope: "full",
          reason,
          client_request_id,
        }),
      },
      true,
      options,
    );
  }

  list(limit = 50, offset = 0, options: RequestOptions = {}) {
    return this.request<Page<Memory>>(`/v1/records?limit=${limit}&offset=${offset}`, {}, false, options);
  }

  async *records(limit = 50, offset = 0, options: RequestOptions = {}) {
    while (true) {
      const page = await this.list(limit, offset, options);
      yield page;
      if (page.items.length < limit) return;
      offset += page.items.length;
    }
  }

  createEntities(items: Array<Record<string, unknown>>, options: RequestOptions = {}) {
    return this.request<BatchResult>(
      "/v1/entities/batch",
      {method: "POST", body: JSON.stringify({items, return: "minimal", atomic: false})},
      false,
      options,
    );
  }

  contextBundle(request: Record<string, unknown>, options: RequestOptions = {}) {
    return this.request(
      "/v1/context-bundle",
      {method: "POST", body: JSON.stringify(request)},
      true,
      options,
    );
  }
}
