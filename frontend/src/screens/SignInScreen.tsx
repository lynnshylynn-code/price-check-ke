import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';

export function SignInScreen({ onContinue }: { onContinue: (name: string) => void }) {
  const [name, setName] = useState('');
  const [showNameError, setShowNameError] = useState(false);
  const trimmedName = name.trim();

  const continueToApp = () => {
    if (!trimmedName) {
      setShowNameError(true);
      return;
    }
    onContinue(trimmedName);
  };

  return (
    <ScrollView
      contentContainerStyle={styles.signInScreen}
      keyboardShouldPersistTaps="handled"
      automaticallyAdjustKeyboardInsets
    >
      <View style={styles.signInBrand}>
        <View style={styles.signInBrandMark}>
          <Ionicons name="pricetag" size={24} color="#FFFFFF" />
        </View>
        <Text style={styles.signInBrandName}>Price Check KE</Text>
      </View>

      <View style={styles.signInCard}>
        <Text style={styles.signInEyebrow}>PERSONALISE YOUR EXPERIENCE</Text>
        <Text style={styles.signInTitle}>Welcome to Price Check KE</Text>
        <Text style={styles.signInDescription}>
          What should we call you? We’ll use your name to greet you when you open the app.
        </Text>

        <View style={styles.signInField}>
          <Text style={styles.signInLabel}>Your name</Text>
          <TextInput
            value={name}
            onChangeText={(value) => {
              setName(value);
              setShowNameError(false);
            }}
            placeholder="e.g. Amina"
            placeholderTextColor={COLORS.muted}
            style={styles.signInInput}
            autoCapitalize="words"
            autoCorrect={false}
            maxLength={60}
            returnKeyType="done"
            onSubmitEditing={continueToApp}
            accessibilityLabel="Your name"
          />
          {showNameError && <Text style={styles.signInError}>Enter your name to continue.</Text>}
        </View>

        <Pressable
          style={styles.signInButton}
          onPress={continueToApp}
          accessibilityRole="button"
        >
          <Text style={styles.signInButtonText}>Continue</Text>
          <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
        </Pressable>
        <View style={styles.signInPrivacy}>
          <Ionicons name="phone-portrait-outline" size={16} color={COLORS.green} />
          <Text style={styles.signInPrivacyText}>
            This profile is saved on this device. Account sign-in and sync are not set up yet.
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}
