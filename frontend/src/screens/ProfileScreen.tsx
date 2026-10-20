import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { ScreenHeader, SectionHeading, SettingRow } from '../components/Common';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { money } from '../utils/pricing';

export function ProfileScreen({
  shoppingArea,
  onChangeArea,
  weeklyBudget,
  onChangeBudget,
  onSaveBudget,
  budgetError,
  storageError,
  savedNotice,
  savedBudget,
  displayName,
  onSignOut,
}: {
  shoppingArea: string;
  onChangeArea: () => void;
  weeklyBudget: string;
  onChangeBudget: (value: string) => void;
  onSaveBudget: () => void;
  budgetError: string;
  storageError: string | null;
  savedNotice: boolean;
  savedBudget: number;
  displayName: string;
  onSignOut: () => void;
}) {
  return (
    <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
      <ScreenHeader
        title="Your Pricewise profile"
        shoppingArea={shoppingArea}
        onChangeArea={onChangeArea}
      />
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{displayName.charAt(0).toUpperCase()}</Text>
        </View>
        <View style={styles.profileIdentity}>
          <Text style={styles.profileName}>{displayName}</Text>
          <Text style={styles.profileSubtext}>Your profile is saved on this device</Text>
        </View>
        <Pressable
          style={styles.profileSignOutButton}
          onPress={onSignOut}
          accessibilityRole="button"
        >
          <Ionicons name="log-out-outline" size={16} color={COLORS.green} />
          <Text style={styles.profileSignOutText}>Sign out</Text>
        </Pressable>
      </View>
      <SectionHeading eyebrow="Preferences" title="Shopping settings" />
      <View style={styles.settingsCard}>
        <SettingRow
          icon="wallet-outline"
          title="Weekly budget"
          subtitle="Used for basket warnings and suggestions"
        >
          <View style={styles.budgetControl}>
            <Text style={styles.currencyPrefix}>KSh</Text>
            <TextInput
              value={weeklyBudget}
              onChangeText={onChangeBudget}
              keyboardType="number-pad"
              style={styles.budgetInput}
              accessibilityLabel="Weekly budget"
            />
            <Pressable style={styles.saveButton} onPress={onSaveBudget} accessibilityRole="button">
              <Text style={styles.saveButtonText}>Save</Text>
            </Pressable>
          </View>
        </SettingRow>
        {savedNotice && (
          <Text style={styles.savedNotice}>Weekly budget saved: {money(savedBudget)}</Text>
        )}
        {budgetError.length > 0 && <Text style={styles.budgetError}>{budgetError}</Text>}
        <SettingRow
          icon="location-outline"
          title="Shopping area"
          subtitle="Used for nearby price discovery"
        >
          <Pressable style={styles.areaSelect} onPress={onChangeArea} accessibilityRole="button">
            <Text style={styles.areaSelectText}>{shoppingArea}</Text>
            <Ionicons name="chevron-down" size={16} color={COLORS.green} />
          </Pressable>
        </SettingRow>
      </View>
      <View style={styles.privacyNote}>
        <Ionicons name="phone-portrait-outline" size={20} color={COLORS.green} />
        <View style={styles.privacyText}>
          <Text style={styles.privacyTitle}>
            {storageError ? 'Local saving needs attention' : 'Settings saved on this device'}
          </Text>
          <Text style={storageError ? styles.budgetError : styles.privacyBody}>
            {storageError ??
              'Your basket, budget, area, and watchlist are stored locally. Account sync is not set up.'}
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}
