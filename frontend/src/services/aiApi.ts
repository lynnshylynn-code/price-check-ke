import { API_BASE_URL } from './marketApi';

export type MarketQuestionAnswer = {
  answer: string;
  source_name: string;
  source_url: string;
  coverage_start: string;
  coverage_end: string;
};

function isMarketQuestionAnswer(value: unknown): value is MarketQuestionAnswer {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<MarketQuestionAnswer>;
  return (
    typeof payload.answer === 'string' &&
    typeof payload.source_name === 'string' &&
    typeof payload.source_url === 'string' &&
    typeof payload.coverage_start === 'string' &&
    typeof payload.coverage_end === 'string'
  );
}

async function requestMarketQuestion(
  endpoint: 'market-question' | 'market-question/simulate',
  question: string,
  signal?: AbortSignal,
): Promise<MarketQuestionAnswer> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/ai/${endpoint}`, {
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
  return requestMarketQuestion('market-question', question, signal);
}

export function simulateMarketQuestion(
  question: string,
  signal?: AbortSignal,
): Promise<MarketQuestionAnswer> {
  return requestMarketQuestion('market-question/simulate', question, signal);
}
