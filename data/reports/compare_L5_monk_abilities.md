# Build comparison: monk, level 5

Each row swaps the candidate into the reference party in place of its rogue and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Wis; ASI split | 843 | yes |
| 14 Con, 13 Str; ASI split | 843 | yes |
| standard | 808 | yes |
| 14 Wis, 13 Str; ASI split | 808 | yes |
| 14 Con, 13 Wis | 745 | yes |
| 14 Con, 13 Str | 745 | yes |
| 14 Str, 13 Wis; ASI split | 745 | no |
| 14 Wis, 13 Str | 701 | no |
| 14 Wis, 13 Con; ASI con first | 695 | no |
| 14 Str, 13 Wis | 647 | no |
| 14 Con, 13 Wis; ASI con first | 645 | no |
| 14 Con, 13 Str; ASI con first | 645 | no |
| 14 Str, 13 Con; ASI con first | 645 | no |
| 14 Wis, 13 Str; ASI con first | 614 | no |
| 14 Str, 13 Wis; ASI con first | 570 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Wis; ASI split | +8% (0.86×) | +22% | +7% ≈ | +2% ≈ | +9% ≈ | +13% | -1% ≈ |
| 14 Con, 13 Str; ASI split | +8% (0.86×) | +22% | +7% ≈ | +2% ≈ | +9% ≈ | +13% | -1% ≈ |
| standard | +8% (0.86×) | +20% | +8% ≈ | +4% ≈ | +7% ≈ | +13% | -1% ≈ |
| 14 Wis, 13 Str; ASI split | +8% (0.86×) | +20% | +8% ≈ | +4% ≈ | +7% ≈ | +13% | -1% ≈ |
| 14 Con, 13 Wis | +8% (0.86×) | +21% | +6% ≈ | +3% ≈ | +7% ≈ | +13% | -1% ≈ |
| 14 Con, 13 Str | +8% (0.86×) | +21% | +6% ≈ | +3% ≈ | +7% ≈ | +13% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
