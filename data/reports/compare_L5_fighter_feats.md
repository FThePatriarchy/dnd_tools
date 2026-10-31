# Build comparison: fighter, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,954 | yes |
| standard | 1,592 | yes |
| feat: alert | 1,592 | yes |
| feat: lucky | 1,592 | yes |
| feat: great weapon master | 1,592 | yes |
| feat: polearm master | 1,388 | yes |
| feat: resilient | 1,376 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: tough | +6% (0.85×) | +13% | +5% ≈ | -0% ≈ | +1% ≈ | +17% | +4% ≈ |
| feat: lucky | +6% (0.84×) | +9% ≈ | +5% ≈ | +3% ≈ | -0% ≈ | +16% | +2% ≈ |
| feat: alert | +4% (0.83×) | +2% ≈ | +5% ≈ | -2% ≈ | +4% ≈ | +13% | -1% ≈ |
| feat: great weapon master | +4% (0.83×) | -0% ≈ | +6% ≈ | -0% ≈ | +3% ≈ | +12% | +2% ≈ |
| feat: polearm master | +2% ≈ (0.81×) | +5% ≈ | +5% ≈ | +1% ≈ | +1% ≈ | -1% ≈ | +0% ≈ |
| standard | +0% ≈ (0.80×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| feat: resilient | -1% ≈ (0.79×) | +0% ≈ | -3% ≈ | -2% ≈ | -1% ≈ | -2% ≈ | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
