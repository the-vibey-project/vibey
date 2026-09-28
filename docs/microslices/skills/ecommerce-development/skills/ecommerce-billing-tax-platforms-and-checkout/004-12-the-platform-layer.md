---
id: skill-12-the-platform-layer-ad4c530a06
purpose: 12 the platform layer
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: ["skill-11-tax-and-cross-border-c9972da7e1"]
links: ["skill-13-catalog-cart-and-checkout-a8752b82f8"]
---

## §12. The Platform Layer

### 12.1 Build vs. buy

**[DURABLE] The honest default for most businesses is a SaaS platform**, and teams
routinely underestimate what they're rebuilding: catalog, variants, pricing rules,
promotions, cart, checkout, payments, tax, shipping rate calculation, order management,
returns, admin tooling, and the reporting the business will ask for in month three.

| Option | Fits |
|---|---|
| **Shopify (+ Plus)** | Most DTC and mid-market. Enormous app ecosystem; **Shopify Payments' rates and the fee for using an external gateway are a real cost input** |
| **BigCommerce, Wix, Squarespace** | SMB to mid-market, varying by catalog complexity |
| **Adobe Commerce / Magento** | Large, complex catalogs and B2B; heavy to run |
| **Salesforce Commerce Cloud, SAP, Oracle** | Enterprise, deep ERP integration |
| **WooCommerce** | WordPress-native, cheap to start, yours to operate |
| **Commercetools, Elastic Path, Medusa, Saleor** | **Headless/composable** — API-first, you build the front end |
| **Custom** | Genuinely unusual models. **Rarely justified by "our business is special"** |

### 12.2 Headless and composable

**[CONTESTED]** *For*: front-end freedom, multi-channel (web, app, kiosk, agent), best-of-
breed components, better performance ceiling. *Against*: **you now own the integration
layer**, which is a permanent team cost; more services to operate; and you lose the
monolith's out-of-the-box admin. **The honest test: are you actually constrained by the
templating layer, or do you just want a nicer stack?** Composable makes sense at scale and
with a platform team; it is frequently a costly aesthetic choice below that.

**[DURABLE] Whatever you choose, the storefront's job is speed.** Core Web Vitals affect
both ranking and conversion, and the highest-leverage work is usually image optimization,
reducing third-party scripts (which is also §8.3 → `ecommerce-payment-methods-sca-fraud-and-pci`'s security advice), and caching strategy.

---
