# Build comparison: fighter, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| standard | 1,592 | yes |
| greatsword + great weapon fighting | 1,569 | yes |
| sword and shield + dueling | 1,465 | yes |
| sword and shield + defense | 1,335 | yes |
| archer + archery | 505 | yes |
| archer + defense | 471 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sword and shield + dueling | +2% ≈ (0.81×) | +8% ≈ | -5% ≈ | -1% ≈ | -1% ≈ | +11% | +0% ≈ |
| greatsword + great weapon fighting | +2% ≈ (0.81×) | +0% ≈ | -2% ≈ | +1% ≈ | -1% ≈ | +12% | +1% ≈ |
| standard | +0% ≈ (0.80×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| sword and shield + defense | -1% ≈ (0.79×) | +11% | -8% ≈ | -2% ≈ | -0% ≈ | -4% ≈ | -1% ≈ |
| archer + archery | -13% (0.69×) | -16% | -15% | -25% | -11% | -10% | -2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.

## Reference party: casual (fighter_5_casual, cleric_5_casual, rogue_5_casual, wizard_5_casual)

Base rating 2,618 XP (0.60× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | +2% ≈ (0.61×) | +1% ≈ | -1% ≈ | -1% ≈ | +3% ≈ | +13% | -0% ≈ |
| greatsword + great weapon fighting | -1% ≈ (0.59×) | -1% ≈ | -7% ≈ | -1% ≈ | -11% | +15% | -0% ≈ |
| sword and shield + defense | -3% ≈ (0.58×) | +0% ≈ | +2% ≈ | +1% ≈ | +3% ≈ | +6% ≈ | -26% |
| sword and shield + dueling | -4% (0.57×) | +2% ≈ | +2% ≈ | +2% ≈ | +3% ≈ | -3% ≈ | -24% |
| archer + archery | -27% (0.44×) | -32% | -25% | -27% | -17% | -19% | -38% |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
