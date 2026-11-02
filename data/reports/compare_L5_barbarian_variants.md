# Build comparison: barbarian, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: great weapon master | +4% (0.83×) | +4% ≈ | +8% ≈ | -2% ≈ | +6% ≈ | +7% ≈ | +4% ≈ |
| feat: alert | +4% (0.83×) | +6% ≈ | +5% ≈ | +0% ≈ | +1% ≈ | +11% | +2% ≈ |
| standard | +3% ≈ (0.82×) | +4% ≈ | +6% ≈ | -3% ≈ | +4% ≈ | +6% ≈ | +2% ≈ |
| greatsword kit | -2% ≈ (0.79×) | +2% ≈ | -2% ≈ | -17% | -1% ≈ | +10% | +2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
