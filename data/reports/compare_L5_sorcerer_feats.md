# Build comparison: sorcerer, level 5

Each row swaps the candidate into the reference party in place of its sorcerer and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 646 | yes |
| standard | 509 | yes |
| feat: alert | 509 | yes |
| feat: lucky | 509 | yes |
| feat: war caster | 509 | yes |
| feat: resilient | 438 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: lucky | +14% (0.91×) | +21% | +9% ≈ | +7% ≈ | +22% | +17% | +9% ≈ |
| feat: tough | +13% (0.90×) | +22% | +13% | +3% ≈ | +29% | +13% | +2% ≈ |
| feat: war caster | +12% (0.89×) | +29% | +8% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| standard | +11% (0.88×) | +19% | +10% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| feat: alert | +9% (0.87×) | +18% | +10% | +5% ≈ | +9% ≈ | +10% | +2% ≈ |
| feat: resilient | +7% (0.85×) | +16% | +7% ≈ | +4% ≈ | +9% ≈ | +3% ≈ | +3% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
