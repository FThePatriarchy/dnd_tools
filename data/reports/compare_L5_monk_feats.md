# Build comparison: monk, level 5

Each row swaps the candidate into the reference party in place of its monk and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,020 | yes |
| standard | 808 | yes |
| feat: alert | 808 | yes |
| feat: lucky | 808 | yes |
| feat: resilient | 614 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: lucky | +14% (0.91×) | +19% | +9% ≈ | +13% | +16% | +26% | +0% ≈ |
| feat: alert | +9% (0.87×) | +22% | +8% ≈ | +3% ≈ | +12% | +14% | -1% ≈ |
| feat: tough | +9% (0.87×) | +24% | +8% ≈ | +5% ≈ | +7% ≈ | +12% | -1% ≈ |
| standard | +8% (0.86×) | +20% | +8% ≈ | +4% ≈ | +7% ≈ | +13% | -1% ≈ |
| feat: resilient | +6% (0.84×) | +17% | +5% ≈ | -0% ≈ | +3% ≈ | +11% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
