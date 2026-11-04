# Build comparison: sorcerer, level 5

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI split | 533 | yes |
| 14 Con, 13 Wis; ASI split | 533 | yes |
| standard | 509 | yes |
| 14 Dex, 13 Wis; ASI split | 509 | yes |
| 14 Dex, 13 Con; ASI con first | 498 | yes |
| 14 Con, 13 Dex | 470 | yes |
| 14 Con, 13 Wis | 470 | no |
| 14 Wis, 13 Con | 470 | no |
| 14 Con, 13 Dex; ASI con first | 462 | no |
| 14 Con, 13 Wis; ASI con first | 462 | no |
| 14 Wis, 13 Con; ASI con first | 462 | no |
| 14 Dex, 13 Wis | 440 | no |
| 14 Dex, 13 Wis; ASI con first | 438 | no |
| 14 Wis, 13 Dex; ASI con first | 407 | no |
| 14 Wis, 13 Dex | 406 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | +11% (0.88×) | +19% | +10% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| 14 Dex, 13 Wis; ASI split | +11% (0.88×) | +19% | +10% ≈ | +3% ≈ | +18% | +12% | +4% ≈ |
| 14 Con, 13 Dex; ASI split | +10% (0.88×) | +21% | +9% ≈ | +4% ≈ | +10% | +13% | +2% ≈ |
| 14 Con, 13 Wis; ASI split | +10% (0.87×) | +21% | +9% ≈ | +3% ≈ | +10% | +13% | +2% ≈ |
| 14 Dex, 13 Con; ASI con first | +9% (0.87×) | +18% | +8% ≈ | +1% ≈ | +15% | +12% | +3% ≈ |
| 14 Con, 13 Dex | +6% (0.85×) | +20% | +8% ≈ | +2% ≈ | +7% ≈ | -1% ≈ | +2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
