import { API_BASE_URL } from './marketApi';

export type MarketQuestionAnswer = {
  answer: string;
  source_name: string;
  source_url: string | null;
  coverage_start: string | null;
  coverage_end: string | null;
  intent: string;
  intent_confidence: number;
  entities: Record<string, unknown>;
  model_version: string;
  sources: { name: string; url: string; note: string }[];
};

function isMarketQuestionAnswer(value: unknown): value is MarketQuestionAnswer {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<MarketQuestionAnswer>;
  return (
    typeof payload.answer === 'string' &&
    typeof payload.source_name === 'string' &&
    (typeof payload.source_url === 'string' || payload.source_url === null) &&
    (typeof payload.coverage_start === 'string' || payload.coverage_start === null) &&
    (typeof payload.coverage_end === 'string' || payload.coverage_end === null) &&
    typeof payload.intent === 'string' &&
    typeof payload.intent_confidence === 'number' &&
    typeof payload.model_version === 'string'
  );
}

async function requestMarketQuestion(
  endpoint: string,
  question: string,
  signal?: AbortSignal,
): Promise<MarketQuestionAnswer> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(
      `Could not reach the Price Check KE API at ${API_BASE_URL}. Check that the backend is running and that EXPO_PUBLIC_API_BASE_URL points to it.`,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('AI service returned an invalid response.');
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `AI request failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }
  if (!isMarketQuestionAnswer(payload)) {
    throw new Error('AI service returned an unexpected response.');
  }
  return payload;
}

export function askMarketQuestion(
  question: string,
  signal?: AbortSignal,
): Promise<MarketQuestionAnswer> {
  return requestMarketQuestion('assistant/ask', question, signal);
}

export function simulateMarketQuestion(
  question: string,
  signal?: AbortSignal,
): Promise<MarketQuestionAnswer> {
  return requestMarketQuestion('ai/market-question/simulate', question, signal);
}
