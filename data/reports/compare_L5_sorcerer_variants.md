# Build comparison: sorcerer, level 5

Each row swaps the candidate into the reference party in place of its sorcerer and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: war caster | +12% (0.89×) | +29% | +8% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| standard | +11% (0.88×) | +19% | +10% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| optimized spells | +11% (0.88×) | +19% | +10% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| casual spells | +9% (0.87×) | +15% | +6% ≈ | +22% | +0% ≈ | +11% | +2% ≈ |
| feat: alert | +9% (0.87×) | +18% | +10% | +5% ≈ | +9% ≈ | +10% | +2% ≈ |
| Metamagic: lasting control | +8% (0.86×) | +19% | +9% ≈ | +0% ≈ | +14% | +6% ≈ | +3% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
