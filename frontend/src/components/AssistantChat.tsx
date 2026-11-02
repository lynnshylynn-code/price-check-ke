import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { askMarketQuestion, MarketQuestionAnswer } from '../services/aiApi';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  intent?: string;
  answer?: MarketQuestionAnswer;
};
type SavedChat = { messages: Message[]; context: Record<string, unknown> | null };
const STORAGE_KEY = 'price-check-ke.assistant-chat.v1';

export function AssistantChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [context, setContext] = useState<Record<string, unknown> | null>(null);
  const [question, setQuestion] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const skipPersist = useRef(false);

  useEffect(() => {
    void AsyncStorage.getItem(STORAGE_KEY).then((saved) => {
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as SavedChat;
          setMessages(parsed.messages.slice(-50));
          setContext(parsed.context ?? null);
        } catch {
          void AsyncStorage.removeItem(STORAGE_KEY);
        }
      }
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    if (hydrated) {
      if (skipPersist.current) {
        skipPersist.current = false;
        void AsyncStorage.removeItem(STORAGE_KEY);
        return;
      }
      void AsyncStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ messages: messages.slice(-50), context } satisfies SavedChat),
      );
    }
  }, [context, hydrated, messages]);

  async function send(text = question) {
    const message = text.trim();
    if (!message || loading) return;
    const userMessage: Message = { id: `${Date.now()}-user`, role: 'user', text: message };
    setMessages((current) => [...current, userMessage].slice(-50));
    setQuestion('');
    setLoading(true);
    setError(null);
    try {
      const result = await askMarketQuestion(message, context);
      setContext(result.context);
      setSuggestions(result.suggestions ?? []);
      const assistantMessage: Message = {
        id: `${Date.now()}-assistant`, role: 'assistant', text: result.answer,
        intent: result.intent, answer: result,
      };
      setMessages((current) => [...current, assistantMessage].slice(-50));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The assistant could not answer.');
    } finally {
      setLoading(false);
    }
  }

  async function clear() {
    skipPersist.current = true;
    setMessages([]);
    setContext(null);
    setSuggestions([]);
    setQuestion('');
    setError(null);
    await AsyncStorage.removeItem(STORAGE_KEY);
  }

  return (
    <View style={styles.aiCard}>
      <Text style={styles.aiLabel}>Assistant chat</Text>
      <Text style={styles.aiFootnote}>
        This assistant answers questions about the price data. It is not open chat.
        Conversation is saved on this device only.
      </Text>
      <View style={styles.simulationPromptRow}>
        <Pressable style={styles.filterChip} onPress={() => void clear()} accessibilityRole="button">
          <Text style={styles.filterChipText}>New chat</Text>
        </Pressable>
        <Pressable style={styles.filterChip} onPress={() => void clear()} accessibilityRole="button">
          <Text style={styles.filterChipText}>Clear conversation</Text>
        </Pressable>
      </View>
      <ScrollView style={{ maxHeight: 330 }} contentContainerStyle={{ gap: 10 }}>
        {messages.map((message) => (
          <View key={message.id} style={{
            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '90%', padding: 12, borderRadius: 14,
            backgroundColor: message.role === 'user' ? COLORS.green : '#F1F4EF',
          }}>
            <Text style={{ color: message.role === 'user' ? '#FFFFFF' : COLORS.text }}>
              {message.text}
            </Text>
            {message.answer && (
              <>
                <Text style={styles.aiSourceText}>Understood as: {message.intent}</Text>
                <Text style={styles.aiSourceText}>
                  {message.answer.source_name}
                  {message.answer.coverage_start ? ` · ${message.answer.coverage_start}–${message.answer.coverage_end}` : ''}
                </Text>
                {message.answer.sources.map((source) => (
                  <Text key={`${source.name}-${source.url}`} style={styles.aiSourceText}>
                    {source.name}: {source.note} {source.url}
                  </Text>
                ))}
              </>
            )}
          </View>
        ))}
        {loading && <ActivityIndicator color={COLORS.green} accessibilityLabel="Assistant is typing" />}
      </ScrollView>
      {suggestions.length > 0 && (
        <View style={styles.simulationPromptRow}>
          {suggestions.slice(0, 3).map((suggestion) => (
            <Pressable key={suggestion} style={styles.filterChip} onPress={() => setQuestion(suggestion)}>
              <Text style={styles.filterChipText}>{suggestion}</Text>
            </Pressable>
          ))}
        </View>
      )}
      <TextInput
        style={styles.aiQuestionInput}
        value={question}
        onChangeText={setQuestion}
        onSubmitEditing={() => void send()}
        placeholder="Ask about prices, offers, or market data"
        accessibilityLabel="Message the assistant"
        returnKeyType="send"
      />
      <Pressable style={styles.primaryButton} disabled={loading || !question.trim()} onPress={() => void send()}>
        <Text style={styles.primaryButtonText}>{loading ? 'Thinking…' : 'Send'}</Text>
      </Pressable>
      {error && <Text style={styles.aiError} accessibilityRole="alert">{error}</Text>}
    </View>
  );
}
