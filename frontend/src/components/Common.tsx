import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Linking, Modal, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { categoryCode } from '../data/products';
import { bestPrice, money } from '../utils/pricing';
import { Category, Product } from '../types';
import { SHOPPING_AREAS, ShoppingArea } from '../constants/shoppingAreas';

export function ScreenHeader({
  title,
  shoppingArea,
  onChangeArea,
}: {
  title: string;
  shoppingArea: string;
  onChangeArea: () => void;
}) {
  return (
    <View style={styles.header}>
      <View style={styles.brandRow}>
        <View style={styles.brandMark}>
          <Ionicons name="pricetag" size={21} color="#FFFFFF" />
        </View>
        <Text style={styles.brandName}>Price Check KE</Text>
        <View style={styles.headerSpacer} />
        <Pressable
          style={styles.areaPill}
          onPress={onChangeArea}
          accessibilityRole="button"
          accessibilityLabel={`Change shopping area, currently ${shoppingArea}`}
        >
          <Text style={styles.areaPillText}>{shoppingArea}</Text>
          <Ionicons name="chevron-down" size={15} color={COLORS.muted} />
        </Pressable>
      </View>
      <Text style={styles.pageTitle}>{title}</Text>
      <Text style={styles.headerSubtitle}>Make every shilling count today.</Text>
    </View>
  );
}

export function ShoppingAreaModal({
  visible,
  selectedArea,
  onSelect,
  onClose,
}: {
  visible: boolean;
  selectedArea: string;
  onSelect: (area: ShoppingArea) => void;
  onClose: () => void;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <Pressable
          style={styles.modalDismissArea}
          onPress={onClose}
          accessibilityLabel="Close shopping area selection"
        />
        <View style={styles.areaPickerSheet}>
          <View style={styles.modalHandle} />
          <Text style={styles.modalProductTitle}>Choose shopping area</Text>
          <Text style={styles.productDescription}>
            Select an area for your nearby price preferences.
          </Text>
          {SHOPPING_AREAS.map((area) => (
            <Pressable
              key={area}
              style={[styles.areaPickerOption, area === selectedArea && styles.areaPickerOptionSelected]}
              onPress={() => onSelect(area)}
              accessibilityRole="button"
              accessibilityState={{ selected: area === selectedArea }}
            >
              <Text
                style={[
                  styles.areaPickerOptionText,
                  area === selectedArea && styles.areaPickerOptionTextSelected,
                ]}
              >
                {area}
              </Text>
              {area === selectedArea && (
                <Ionicons name="checkmark-circle" size={19} color={COLORS.green} />
              )}
            </Pressable>
          ))}
        </View>
      </View>
    </Modal>
  );
}

export function SearchBar({
  value,
  placeholder,
  onChangeText,
  onPress,
  editable = true,
}: {
  value: string;
  placeholder: string;
  onChangeText: (value: string) => void;
  onPress?: () => void;
  editable?: boolean;
}) {
  return (
    <Pressable
      style={styles.searchBar}
      onPress={onPress}
      accessibilityRole={editable ? undefined : 'button'}
    >
      <Ionicons name="search-outline" size={21} color={COLORS.green} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#89918A"
        style={styles.searchInput}
        editable={editable}
        returnKeyType="search"
        accessibilityLabel="Search products"
      />
      {value.length > 0 && (
        <Pressable onPress={() => onChangeText('')} accessibilityLabel="Clear search">
          <Ionicons name="close-circle" size={20} color={COLORS.muted} />
        </Pressable>
      )}
    </Pressable>
  );
}

export function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <View style={styles.sectionHeading}>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
    </View>
  );
}

export function CategoryTile({ category, onPress }: { category: Exclude<Category, 'All'>; onPress: () => void }) {
  const icons: Record<Exclude<Category, 'All'>, keyof typeof Ionicons.glyphMap> = {
    Dairy: 'water-outline',
    Bakery: 'cafe-outline',
    Pantry: 'basket-outline',
    Produce: 'leaf-outline',
    Household: 'home-outline',
    'Non-food': 'cube-outline',
  };
  return (
    <Pressable style={styles.categoryTile} onPress={onPress} accessibilityRole="button">
      <View style={styles.categoryIcon}>
        <Ionicons name={icons[category]} size={20} color={COLORS.green} />
      </View>
      <Text style={styles.categoryText}>{category}</Text>
      <Ionicons name="chevron-forward" size={15} color={COLORS.muted} />
    </Pressable>
  );
}

export function ListingLabel({ dataLabel }: { dataLabel: string }) {
  return (
    <View style={styles.demoLabel}>
      <Ionicons name="information-circle-outline" size={14} color={COLORS.muted} />
      <Text style={styles.demoLabelText}>{dataLabel}</Text>
    </View>
  );
}

function openListing(url: string) {
  void Linking.openURL(url).catch((error: unknown) => {
    console.error('Could not open retailer product listing.', error);
  });
}

export function ProductCard({
  product,
  onOpen,
  onAdd,
  compact = false,
}: {
  product: Product;
  onOpen: () => void;
  onAdd: () => void;
  compact?: boolean;
}) {
  const best = bestPrice(product);
  return (
    <View style={[styles.productCard, compact && styles.productCardCompact]}>
      <Pressable style={styles.productInfo} onPress={onOpen} accessibilityRole="button">
        <View style={styles.productBadge}>
          <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
        </View>
        <View style={styles.productDetails}>
          <Text style={styles.productName}>
            {product.name} <Text style={styles.productSize}>{product.size}</Text>
          </Text>
          <Text style={styles.productDescription}>{product.description}</Text>
          <View style={styles.storeLine}>
            <Ionicons name="storefront-outline" size={14} color={COLORS.muted} />
            <Text style={styles.storeName}>
              {best.store} · {best.location_name}
            </Text>
          </View>
        </View>
      </Pressable>
      <View style={styles.productPriceBlock}>
        <Text style={styles.bestPriceCaption}>Lowest observed</Text>
        <Text style={styles.productPrice}>{money(best.price)}</Text>
        <Pressable style={styles.addButton} onPress={onAdd} accessibilityRole="button">
          <Ionicons name="add" size={17} color="#FFFFFF" />
          <Text style={styles.addButtonText}>Add</Text>
        </Pressable>
      </View>
    </View>
  );
}

export function ProductModal({
  product,
  watched,
  onClose,
  onToggleWatch,
  onAdd,
}: {
  product: Product | null;
  watched: boolean;
  onClose: () => void;
  onToggleWatch: () => void;
  onAdd: () => void;
}) {
  if (!product) return null;
  const lowest = bestPrice(product);
  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <Pressable style={styles.modalDismissArea} onPress={onClose} accessibilityLabel="Close product details" />
        <ScrollView
          style={styles.modalSheet}
          contentContainerStyle={styles.modalSheetContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.modalHandle} />
          <View style={styles.modalTopRow}>
            <View style={styles.productBadge}>
              <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
            </View>
            <View style={styles.headerSpacer} />
            <Pressable onPress={onClose} style={styles.closeButton} accessibilityLabel="Close">
              <Ionicons name="close" size={21} color={COLORS.text} />
            </Pressable>
          </View>
          <Text style={styles.eyebrow}>{product.category}</Text>
          <Text style={styles.modalProductTitle}>{product.name}</Text>
          <Text style={styles.productDescription}>
            {product.description} · {product.size}
          </Text>
          <View style={styles.currentPriceCard}>
            <Text style={styles.bestPriceCaption}>Lowest observed price</Text>
            <Text style={styles.modalLowestPrice}>{money(lowest.price)}</Text>
            <Text style={styles.productDescription}>
              at {lowest.store} · {lowest.location_name}
            </Text>
            <Text style={styles.compareStock}>
              Observed {new Date(lowest.observed_at).toLocaleString('en-KE')}
            </Text>
          </View>
          {product.comparison_note && (
            <Text style={styles.productDescription}>{product.comparison_note}</Text>
          )}
          <Text style={styles.compareTitle}>Observed retailer listings</Text>
          {product.prices.map((item) => (
            <View style={styles.compareRow} key={`${item.location_id}-${item.item_name}`}>
              <View style={styles.storeAvatar}>
                <Text style={styles.storeInitial}>{item.store.charAt(0)}</Text>
              </View>
              <View style={styles.compareStore}>
                <Text style={styles.compareStoreName}>
                  {item.store} · {item.location_name}
                </Text>
                <Text style={styles.compareStock}>{item.item_name}</Text>
                <Text style={styles.compareStock}>{item.location_context}</Text>
                <Text style={styles.compareStock}>
                  Observed {new Date(item.observed_at).toLocaleString('en-KE')}
                </Text>
                <Pressable
                  onPress={() => openListing(item.product_url)}
                  accessibilityRole="link"
                  accessibilityLabel={`View ${item.store} product listing`}
                >
                  <Text style={styles.linkText}>View retailer listing</Text>
                </Pressable>
                {item.regular_price !== null && item.regular_price > item.price && (
                  <Text style={styles.compareStock}>Regular price {money(item.regular_price)}</Text>
                )}
              </View>
              {item.location_id === lowest.location_id && <Text style={styles.lowestTag}>Lowest</Text>}
              <Text style={styles.comparePrice}>{money(item.price)}</Text>
            </View>
          ))}
          {product.missing_at_stores.length > 0 && (
            <Text style={styles.modalDisclaimer}>
              No verified listing in this snapshot: {product.missing_at_stores.join(', ')}.
            </Text>
          )}
          <Text style={styles.modalDisclaimer}>
            Observed listing prices; stock and checkout prices are not verified.
          </Text>
          <View style={styles.modalActions}>
            <Pressable style={styles.watchButton} onPress={onToggleWatch} accessibilityRole="button">
              <Ionicons name={watched ? 'notifications' : 'notifications-outline'} size={18} color={COLORS.green} />
              <Text style={styles.watchButtonText}>{watched ? 'Watching price' : 'Watch price'}</Text>
            </Pressable>
            <Pressable style={styles.primaryButton} onPress={onAdd} accessibilityRole="button">
              <Ionicons name="basket-outline" size={18} color="#FFFFFF" />
              <Text style={styles.primaryButtonText}>Add to basket</Text>
            </Pressable>
          </View>
        </ScrollView>
      </View>
    </Modal>
  );
}

export function StrategyButton({
  active,
  title,
  subtitle,
  icon,
  disabled = false,
  onPress,
}: {
  active: boolean;
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
  disabled?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[
        styles.strategyButton,
        active && styles.strategyButtonActive,
        disabled && styles.strategyButtonDisabled,
      ]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ selected: active, disabled }}
    >
      <Ionicons name={icon} size={20} color={active ? COLORS.green : COLORS.muted} />
      <View style={styles.strategyText}>
        <Text style={styles.strategyTitle}>{title}</Text>
        <Text style={styles.strategySubtitle}>{subtitle}</Text>
      </View>
    </Pressable>
  );
}

export function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryRow}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
    </View>
  );
}

export function MetricCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <View style={styles.metricCard}>
      <Ionicons name={icon} size={18} color={COLORS.green} />
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricHint}>{hint}</Text>
    </View>
  );
}

export function SettingRow({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.settingRow}>
      <View style={styles.settingIcon}>
        <Ionicons name={icon} size={19} color={COLORS.green} />
      </View>
      <View style={styles.settingCopy}>
        <Text style={styles.settingTitle}>{title}</Text>
        <Text style={styles.settingSubtitle}>{subtitle}</Text>
      </View>
      {children}
    </View>
  );
}
