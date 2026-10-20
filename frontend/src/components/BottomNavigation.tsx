import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { Tab } from '../types';

export function BottomNavigation({
  activeTab,
  basketCount,
  bottomInset,
  onChange,
}: {
  activeTab: Tab;
  basketCount: number;
  bottomInset: number;
  onChange: (tab: Tab) => void;
}) {
  const tabs: { name: Tab; icon: keyof typeof Ionicons.glyphMap; activeIcon: keyof typeof Ionicons.glyphMap }[] = [
    { name: 'Home', icon: 'home-outline', activeIcon: 'home' },
    { name: 'Search', icon: 'search-outline', activeIcon: 'search' },
    { name: 'Basket', icon: 'basket-outline', activeIcon: 'basket' },
    { name: 'Trends', icon: 'trending-up-outline', activeIcon: 'trending-up' },
    { name: 'Profile', icon: 'person-outline', activeIcon: 'person' },
  ];
  return (
    <View style={[styles.bottomNav, { paddingBottom: Math.max(bottomInset, 8) }]}>
      {tabs.map((item) => {
        const selected = activeTab === item.name;
        return (
          <Pressable
            key={item.name}
            style={[styles.navItem, selected && styles.navItemActive]}
            onPress={() => onChange(item.name)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
          >
            <View style={styles.navIconWrap}>
              <Ionicons
                name={selected ? item.activeIcon : item.icon}
                size={21}
                color={selected ? COLORS.green : COLORS.muted}
              />
              {item.name === 'Basket' && basketCount > 0 && (
                <View style={styles.navBadge}>
                  <Text style={styles.navBadgeText}>{basketCount > 9 ? '9+' : basketCount}</Text>
                </View>
              )}
            </View>
            <Text style={[styles.navLabel, selected && styles.navLabelActive]}>{item.name}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
