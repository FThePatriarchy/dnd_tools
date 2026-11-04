# Build comparison: barbarian, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI split | 1,238 | yes |
| 14 Dex, 13 Con; ASI con first | 1,125 | yes |
| standard | 1,125 | yes |
| 14 Con, 13 Dex | 1,050 | yes |
| 14 Wis, 13 Con | 1,050 | yes |
| 14 Con, 13 Dex; ASI con first | 1,045 | yes |
| 14 Wis, 13 Con; ASI con first | 1,045 | no |
| 14 Dex, 13 Wis; ASI con first | 950 | no |
| 14 Dex, 13 Wis | 945 | no |
| 14 Wis, 13 Dex; ASI con first | 887 | no |
| 14 Wis, 13 Dex | 886 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Dex; ASI split | +4% (0.83×) | +6% ≈ | +8% ≈ | -3% ≈ | +4% ≈ | +13% | +1% ≈ |
| standard | +3% ≈ (0.82×) | +4% ≈ | +6% ≈ | -3% ≈ | +4% ≈ | +6% ≈ | +2% ≈ |
| 14 Dex, 13 Con; ASI con first | +2% ≈ (0.81×) | +10% | +7% ≈ | -17% | +3% ≈ | +9% ≈ | +2% ≈ |
| 14 Con, 13 Dex; ASI con first | +2% ≈ (0.81×) | +1% ≈ | +7% ≈ | -11% | +4% ≈ | +11% | +1% ≈ |
| 14 Wis, 13 Con | +1% ≈ (0.80×) | +2% ≈ | +7% ≈ | -12% | +4% ≈ | +4% ≈ | +0% ≈ |
| 14 Con, 13 Dex | +0% ≈ (0.80×) | +2% ≈ | +7% ≈ | -15% | +4% ≈ | +4% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
