---
id: skill-14-buying-and-sourcing-666f790fc9
purpose: 14 buying and sourcing
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-networking-enclosures-and-productization/SKILL.md
requires: ["skill-13-prototype-product-f9661d85a5"]
links: []
---

## §14. Buying and Sourcing

**Suppliers**: **Adafruit** and **SparkFun** (⚠️ **more expensive, and the documentation
and tutorials are the actual product — worth it while learning**), **Pimoroni** (UK),
**Mouser / Digi-Key / RS / Farnell** (components proper, genuine parts, real datasheets),
**AliExpress / LCSC** (⚠️ **cheap, slow, variable — fine for passives and modules, risky
for critical ICs**), **Seeed**, **Waveshare**, **Core Electronics**, **The Pi Hut**.

> **⚠️ GOTCHA — counterfeits and fakes are endemic at the cheap end**, and they cost more
> time than money. The recurring ones: **fake FTDI and CH340 USB-serial chips** (drivers
> may refuse them), **relabelled or lower-grade ICs**, **SD cards reporting far more
> capacity than they have** (⚠️ **test any cheap card with `f3` or H2testw before trusting
> data to it**), **18650 cells with impossible capacity claims** (§4.3 → `maker-power-electronics-and-io`), and **power
> supplies that don't deliver rated current** or lack real isolation.
>
> **The rule: buy passives and generic modules cheaply, buy anything critical — ICs,
> power supplies, lithium cells, SD cards — from a reputable distributor.**

**[DURABLE] Buy a starter kit for your first project.** A decent Arduino or Pi kit with
assorted resistors, LEDs, jumpers, sensors, and a breadboard removes the friction of
discovering mid-project that you don't own a 220Ω resistor. **Then buy an assortment box
of resistors, capacitors, and headers** — you'll use them forever.
