# Build comparison: cleric, level 5

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Str; ASI split | 503 | yes |
| 14 Con, 13 Dex; ASI split | 503 | yes |
| 14 Con, 13 Str; ASI con first | 464 | yes |
| 14 Con, 13 Dex; ASI con first | 464 | yes |
| 14 Str, 13 Con; ASI con first | 464 | yes |
| 14 Dex, 13 Con; ASI con first | 464 | no |
| standard | 445 | yes |
| 14 Con, 13 Dex | 445 | no |
| 14 Str, 13 Con | 445 | no |
| 14 Str, 13 Dex; ASI split | 445 | no |
| 14 Dex, 13 Con | 445 | no |
| 14 Dex, 13 Str; ASI split | 445 | no |
| 14 Str, 13 Dex; ASI con first | 410 | no |
| 14 Dex, 13 Str; ASI con first | 410 | no |
| 14 Str, 13 Dex | 386 | no |
| 14 Dex, 13 Str | 386 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Dex; ASI split | +3% ≈ (0.82×) | +4% ≈ | +1% ≈ | +1% ≈ | -1% ≈ | +13% | -0% ≈ |
| 14 Con, 13 Str; ASI split | +3% ≈ (0.82×) | +2% ≈ | +1% ≈ | -0% ≈ | +0% ≈ | +13% | +0% ≈ |
| 14 Con, 13 Dex; ASI con first | +2% ≈ (0.81×) | +2% ≈ | +1% ≈ | -1% ≈ | -1% ≈ | +11% | -1% ≈ |
| standard | +0% ≈ (0.80×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| 14 Con, 13 Str; ASI con first | -1% ≈ (0.79×) | +1% ≈ | -5% ≈ | -1% ≈ | -0% ≈ | +1% ≈ | -0% ≈ |
| 14 Str, 13 Con; ASI con first | -1% ≈ (0.79×) | +1% ≈ | -5% ≈ | -1% ≈ | -0% ≈ | +1% ≈ | -0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
