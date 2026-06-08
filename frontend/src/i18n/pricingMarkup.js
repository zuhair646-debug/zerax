/**
 * Dynamic Pricing Markup by Language.
 *
 * Logic: Visitors using a non-Arabic language consume Claude translation
 * cycles on every page load, so we transparently absorb that cost into
 * the package price. Arabic visitors pay the original price unchanged.
 *
 * Markup: $3 USD (≈ 11 SAR) per package for every non-Arabic language.
 * This is intentionally flat so users can't game it by switching languages.
 *
 * USAGE:
 *   import { applyMarkup } from '@/i18n/pricingMarkup';
 *   const { sar, usd } = applyMarkup(pkg.price_sar, pkg.price_usd, i18n.language);
 */
const MARKUP_USD = 3;
const MARKUP_SAR = 11;

export function getMarkup(langCode) {
  if (!langCode || langCode === 'ar') return { sar: 0, usd: 0, applies: false };
  return { sar: MARKUP_SAR, usd: MARKUP_USD, applies: true };
}

/** Return the displayed price after applying the language-based markup. */
export function applyMarkup(priceSar, priceUsd, langCode) {
  const m = getMarkup(langCode);
  const sar = Number(priceSar || 0) + m.sar;
  const usd = Number(priceUsd || 0) + m.usd;
  return { sar, usd, applies: m.applies, markup: m };
}

/** Human-readable hint shown next to the price for non-AR users. */
export function markupHint(langCode) {
  if (langCode === 'ar' || !langCode) return null;
  return `Includes +$${MARKUP_USD} international support`;
}
