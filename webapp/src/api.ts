import type {
  ApiClient,
  ApiErrorEnvelope,
  HealthResponse,
  ListParams,
  QueryBody,
  ResourceName,
} from "./types";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;

  constructor(envelope: ApiErrorEnvelope) {
    super(envelope.error.message);
    this.code = envelope.error.code;
    this.details = envelope.error.details;
  }
}

function buildQuery(params?: ListParams): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined) {
      continue;
    }
    searchParams.set(key, String(value));
  }

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function createApiClient(baseUrl = "/api"): ApiClient {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });

    if (!response.ok) {
      const payload = (await response.json()) as ApiErrorEnvelope;
      throw new ApiError(payload);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  function listResource<T>(resource: ResourceName, params?: ListParams): Promise<T> {
    return request<T>(`/${resource}${buildQuery(params)}`);
  }

  function queryResource<T>(resource: ResourceName, body: QueryBody): Promise<T> {
    return request<T>(`/${resource}/query`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  function getResource<T>(resource: ResourceName, id: string): Promise<T> {
    return request<T>(`/${resource}/${encodeURIComponent(id)}`);
  }

  function createResource<T>(resource: ResourceName, body: unknown): Promise<T> {
    return request<T>(`/${resource}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  function patchResource<T>(resource: ResourceName, id: string, patch: unknown): Promise<T> {
    return request<T>(`/${resource}/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  }

  function replaceResource<T>(resource: ResourceName, id: string, body: unknown): Promise<T> {
    return request<T>(`/${resource}/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  async function deleteResource(resource: ResourceName, id: string): Promise<void> {
    await request<void>(`/${resource}/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  }

  function getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  }

  function getConversationItems<T>(conversationId: string, params?: ListParams): Promise<T> {
    return request<T>(
      `/conversations/${encodeURIComponent(conversationId)}/items${buildQuery(params)}`,
    );
  }

  function createConversationItem<T>(conversationId: string, body: unknown): Promise<T> {
    return request<T>(`/conversations/${encodeURIComponent(conversationId)}/items`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  function getConversationResponses<T>(conversationId: string): Promise<T> {
    return request<T>(`/conversations/${encodeURIComponent(conversationId)}/responses`);
  }

  function getSessionConversations<T>(sessionId: string): Promise<T> {
    return request<T>(`/sessions/${encodeURIComponent(sessionId)}/conversations`);
  }

  return {
    getHealth,
    listResource,
    queryResource,
    getResource,
    createResource,
    patchResource,
    replaceResource,
    deleteResource,
    getConversationItems,
    createConversationItem,
    getConversationResponses,
    getSessionConversations,
  };
}