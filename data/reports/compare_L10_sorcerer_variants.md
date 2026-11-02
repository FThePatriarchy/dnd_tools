# Build comparison: sorcerer, level 10

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| standard | 1,676 | yes |
| optimized spells | 1,676 | yes |
| casual spells | 1,676 | yes |
| feat: alert | 1,676 | yes |
| feat: war caster | 1,676 | yes |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,065 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: war caster | +12% (0.82×) | +20% | +3% ≈ | +26% | +24% | +5% ≈ | -1% ≈ |
| standard | +12% (0.82×) | +21% | +4% ≈ | +25% | +23% | +4% ≈ | -0% ≈ |
| optimized spells | +12% (0.82×) | +21% | +4% ≈ | +25% | +23% | +4% ≈ | -0% ≈ |
| feat: alert | +10% (0.80×) | +27% | +7% ≈ | +4% ≈ | +15% | +9% ≈ | -1% ≈ |
| casual spells | +5% (0.77×) | +14% | +2% ≈ | +9% ≈ | +6% ≈ | +2% ≈ | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
