# Build comparison: barbarian, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,350 | yes |
| feat: polearm master | 1,161 | yes |
| standard | 1,125 | yes |
| feat: alert | 1,125 | yes |
| feat: lucky | 1,125 | yes |
| feat: great weapon master | 1,125 | yes |
| feat: resilient | 950 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: tough | +6% (0.85×) | +13% | +8% ≈ | -3% ≈ | +6% ≈ | +11% | +2% ≈ |
| feat: lucky | +6% (0.84×) | +6% ≈ | +6% ≈ | -2% ≈ | +4% ≈ | +15% | +5% ≈ |
| feat: great weapon master | +4% (0.83×) | +4% ≈ | +8% ≈ | -2% ≈ | +6% ≈ | +7% ≈ | +4% ≈ |
| feat: alert | +4% (0.83×) | +6% ≈ | +5% ≈ | +0% ≈ | +1% ≈ | +11% | +2% ≈ |
| standard | +3% ≈ (0.82×) | +4% ≈ | +6% ≈ | -3% ≈ | +4% ≈ | +6% ≈ | +2% ≈ |
| feat: resilient | -0% ≈ (0.80×) | +3% ≈ | +5% ≈ | -15% | +3% ≈ | +3% ≈ | +2% ≈ |
| feat: polearm master | -2% ≈ (0.78×) | +1% ≈ | +5% ≈ | -17% | +2% ≈ | -4% ≈ | +3% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
