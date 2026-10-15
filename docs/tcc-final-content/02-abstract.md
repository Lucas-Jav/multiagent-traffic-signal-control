# Abstract

> English version adapted faithfully from `01-resumo.md`. No claim absent from the Portuguese
> abstract was added. All numerical values come from the validated FINAL N = 10 analysis.

**DISTRIBUTED AND COOPERATIVE CONTROL OF URBAN TRAFFIC SIGNALS**

## Text

Urban traffic-signal control affects travel times, queues and network discharge capacity, and the
choice between fixed-time plans, local adaptation and cooperation among intersections remains an
open question. This work investigates whether local information exchange among decentralized
traffic-signal controllers improves network performance compared with a non-cooperative local
adaptive controller and with fixed-time control, under different demand conditions. A reactive,
distributed and decentralized system, with one agent per intersection, was implemented and
evaluated in the SUMO 1.27.1 simulator (TraCI interface, Python 3.12) on a synthetic 3×3 network
with nine intersections. Five strategies were compared: calibrated fixed-time (B0), local adaptive
(B1), local pressure (B2), compact cooperative (C1) and expanded cooperative (C2). The final
campaign, frozen before execution, used 200 runs in the main experiment (four demand scenarios:
balanced, directional peak, demand shift and localized saturation) and 90 runs in a
communication-degradation experiment (packet loss of 0, 20, 50 and 100% over the directional-peak
demand), with 10 seeds per condition, for a total of 290 runs. The analysis relied on
seed-paired comparisons and 95% paired bootstrap confidence intervals, and included a west–east
reference route. The results indicate that the effect of cooperation was scenario-dependent.
Relative to the local-pressure controller, the compact cooperative controller performed worse in
the balanced and demand-shift scenarios, showed a trade-off in the directional peak (waiting time
−15.2% and mean queue −18.3%, but throughput −5.7%) and was advantageous under localized saturation
(throughput +8.8%, waiting time −19.5%, mean queue −17.3%). Calibrated fixed-time control
outperformed the local-pressure controller in the directional-peak, demand-shift and localized-saturation
scenarios. The expanded communication sent about 2.3 times more bytes than the compact one
without a general traffic benefit, and communication degradation was non-monotonic. No evidence
of general superiority of cooperation was observed: the largest benefit appeared under localized
saturation, while in other regimes local adaptive control or calibrated fixed-time control were
more competitive. The conclusions hold for the synthetic network, the simulation and the frozen
parameterization used.

**Keywords:** traffic-signal control; distributed control; multi-agent cooperation; traffic simulation; SUMO; urban networks.
