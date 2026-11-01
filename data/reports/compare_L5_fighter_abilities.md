# Build comparison: fighter, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI split | 1,773 | yes |
| standard | 1,592 | yes |
| 14 Dex, 13 Con | 1,592 | yes |
| 14 Wis, 13 Con | 1,592 | yes |
| 14 Con, 13 Dex; ASI con first | 1,532 | yes |
| 14 Dex, 13 Con; ASI con first | 1,532 | yes |
| 14 Wis, 13 Con; ASI con first | 1,532 | no |
| 14 Dex, 13 Wis | 1,411 | no |
| 14 Wis, 13 Dex | 1,411 | no |
| 14 Dex, 13 Wis; ASI con first | 1,376 | no |
| 14 Wis, 13 Dex; ASI con first | 1,376 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Dex, 13 Con; ASI con first | +3% (0.82×) | +10% ≈ | -2% ≈ | -2% ≈ | +0% ≈ | +13% | +0% ≈ |
| 14 Con, 13 Dex; ASI split | +3% (0.82×) | +4% ≈ | +3% ≈ | -1% ≈ | +1% ≈ | +13% | +0% ≈ |
| 14 Con, 13 Dex; ASI con first | +2% ≈ (0.81×) | +9% ≈ | -6% ≈ | -3% ≈ | -0% ≈ | +14% | -0% ≈ |
| 14 Dex, 13 Con | +0% ≈ (0.80×) | -1% ≈ | +3% ≈ | +0% ≈ | +0% ≈ | +1% ≈ | -1% ≈ |
| standard | +0% ≈ (0.80×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| 14 Wis, 13 Con | -0% ≈ (0.80×) | +0% ≈ | +0% ≈ | -0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
