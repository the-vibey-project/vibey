---
id: skill-13-catalog-cart-and-checkout-a8752b82f8
purpose: 13 catalog cart and checkout
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: ["skill-12-the-platform-layer-ad4c530a06"]
links: ["skill-14-agentic-commerce-893ac8a9b0"]
---

## §13. Catalog, Cart, and Checkout

### 13.1 The data model

**Products vs. variants** is the modelling decision everything else hangs off. A "product"
with options (size, colour) has **variants** as the actual sellable units with their own
SKU, price, and inventory. **⚠️ Getting this wrong forces a painful migration**, because
carts, orders, and inventory all reference the wrong grain.

**Inventory**: track available-to-promise, not just on-hand. **Decide when you reserve** —
at cart (protects the customer, risks hoarding), at checkout start (a reasonable middle),
or at order (risks overselling). **Multi-location inventory and backorders** turn this into
a real allocation problem.

**Pricing and promotions** get complicated faster than any other area: price lists,
customer-group pricing, quantity breaks, currency-specific prices, and **stacking rules for
discounts** (order of application changes the total — decide and document it). **⚠️ Test
promotion logic adversarially**; discount stacking is a business-logic vulnerability and
promo abuse is a real fraud category (§7.1 → `ecommerce-payment-methods-sca-fraud-and-pci`).

### 13.2 Checkout

**[DURABLE] Checkout conversion is where the money is, and the levers are well-established:**
guest checkout (**forced account creation is among the most reliably damaging choices you
can make**), minimal fields with sensible autofill and address autocomplete, **wallets
surfaced early** (Apple/Google Pay skip the form entirely), **all costs shown before the
final step** — surprise shipping and tax at the last screen is the top cited abandonment
reason — a visible progress indicator, inline validation, trust signals, and a mobile
experience designed first rather than adapted.

**Accessibility is a conversion feature and, increasingly, a legal requirement** (§11) —
keyboard navigation, labelled inputs, sufficient contrast, and screen-reader-usable error
messages.

**⚠️ The webhook, not the redirect, confirms the order** (§3.2 → `ecommerce-payments-architecture-and-integration`). Design the post-payment
experience so a customer who closes the tab still gets their order.

---
