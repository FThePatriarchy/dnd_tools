# Build comparison: bard, level 10

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI con first | 837 | yes |
| 14 Con, 13 Wis; ASI con first | 837 | yes |
| 14 Dex, 13 Con; ASI split | 800 | yes |
| 14 Dex, 13 Wis; ASI con first | 800 | yes |
| 14 Con, 13 Dex | 797 | yes |
| 14 Con, 13 Wis | 797 | no |
| standard | 751 | yes |
| 14 Dex, 13 Wis | 751 | no |
| 14 Con, 13 Dex; ASI split | 747 | no |
| 14 Con, 13 Wis; ASI split | 747 | no |
| 14 Wis, 13 Con; ASI split | 747 | no |
| 14 Dex, 13 Wis; ASI split | 704 | no |
| 14 Wis, 13 Con | 701 | no |
| 14 Wis, 13 Dex; ASI split | 657 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Dex | -9% (0.67×) | -4% ≈ | -17% | +5% ≈ | -16% | -18% | -1% ≈ |
| 14 Con, 13 Dex; ASI con first | -10% (0.66×) | -5% ≈ | -17% | +2% ≈ | -18% | -17% | -1% ≈ |
| 14 Con, 13 Wis; ASI con first | -10% (0.66×) | -5% ≈ | -17% | +2% ≈ | -18% | -17% | -1% ≈ |
| standard | -10% (0.66×) | -3% ≈ | -16% | -2% ≈ | -18% | -17% | -1% ≈ |
| 14 Dex, 13 Con; ASI split | -10% (0.66×) | -2% ≈ | -16% | +2% ≈ | -19% | -21% | -1% ≈ |
| 14 Dex, 13 Wis; ASI con first | -10% (0.66×) | -2% ≈ | -16% | +2% ≈ | -19% | -21% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
