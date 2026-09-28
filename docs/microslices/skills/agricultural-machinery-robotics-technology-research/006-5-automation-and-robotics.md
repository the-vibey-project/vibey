---
id: skill-5-automation-and-robotics-013410ef18
purpose: 5 automation and robotics
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/agricultural-machinery-robotics-technology-research/SKILL.md
requires: ["skill-4-precision-agriculture-76418eaf47"]
links: ["skill-6-artificial-intelligence-and-farm-software-fa7de20650"]
---

## 5. Automation and robotics

### Levels of automation

1. **Manual:** operator supplies perception, decision, and control.
2. **Operator assist:** machine holds speed, route, section control, or implement depth.
3. **Supervised automation:** machine performs a bounded task while a person monitors and intervenes.
4. **Coordinated autonomy:** multiple machines share routes, task state, and constraints.
5. **Unsupervised autonomy:** system performs a defined operation with remote exception handling.

The last level is task-specific, not a general human replacement. A machine that autonomously follows a mapped route in an open field is very different from one that identifies ripe fruit, reaches through a deformable canopy, avoids workers, handles variable terrain, and preserves product quality.

### Agricultural robot tasks

Robotics is especially attractive where work is repetitive, dangerous, labor-constrained, precise, or difficult to schedule:

- autonomous scouting and crop imaging;
- mechanical weeding and targeted spraying;
- precision seeding and transplanting;
- orchard and vineyard pruning, thinning, and harvesting;
- greenhouse transport, climate control, and harvesting;
- dairy milking, feeding, cleaning, and animal monitoring;
- poultry and swine environmental control and inspection;
- autonomous mowing, mowing of orchards, and under-canopy maintenance;
- harvesting, sorting, packing, palletizing, and internal logistics;
- drone and ground-robot surveillance;
- robotic milking and individual-animal management.

USDA’s National Agricultural Library notes that many commercial agricultural robots still have limited decision-making capacity and often follow preprogrammed paths, even as machine vision and AI are being advertised for targeted herbicide application, disease prediction, and combine optimization. [USDA NAL robotics and automation](https://www.nal.usda.gov/research-tools/food-safety-research-projects/bridging-gaps-production-agriculture-advancements-robotics-and-automation)

### Why farm robotics is hard

Outdoor agriculture has unstructured, changing environments:

- plants grow, bend, overlap, and hide fruit or weeds;
- mud, dust, rain, glare, snow, and fog degrade sensors;
- field boundaries and obstacles change;
- GNSS can be unavailable or inaccurate;
- biological targets vary in size, maturity, color, and disease;
- equipment must avoid people, animals, and wildlife;
- quality damage can be more expensive than labor;
- safe failure is difficult during spraying, cutting, lifting, and harvesting.

Testing should report task completion, false positives and negatives, damage, hours of supervision, downtime, energy, maintenance, weather envelope, and performance across farms—not just a best-case demonstration.
