# Showcase Asset Audit

This audit covers the static product showcase only. The main application assets under `static/assets/images` remain untouched unless a reference audit proved an exact duplicate was safe to remove.

## Byte Baseline

| Checkpoint | `static/assets` bytes |
| --- | ---: |
| Before Task12 showcase work | 84,754,424 |
| After Task12 initial screenshot refresh | 85,625,018 |
| After this review fix | 80,079,772 |

The review fix reduces the asset directory by 5,545,246 bytes. The reduction is the seven superseded PNGs and one unreferenced video, offset by the optimized WebP files and the small favicon.

## Optimized Showcase Images

The source files were real Playwright screenshots. Pillow 12.2 converted them to WebP at quality 88; images wider than 1,440px were resized with Lanczos. Text remains inspectable in the browser screenshots.

| Source (deleted) | Before bytes / SHA-256 | Replacement | After bytes / SHA-256 | Size |
| --- | --- | --- | --- | --- |
| `agent-workbench.png` | 477,415 / `E33C85381F31DA4768BCFFE7080EEFDEF65C370E9FB93230561E0A85735A188E` | `agent-workbench.webp` | 59,902 / `A95C947C441A5FC28DA8BB65E92C7F9144015B6132838F9479E8E39C3150AA41` | 1440 x 900 |
| `agent-mobile.png` | 86,501 / `CB461B31F311B1CCAE1241360D254E673A1A12AF9573965E5A3EE439D84120E1` | `agent-mobile.webp` | 21,362 / `103047FCA80FFDFDEFA09D62F0B4B6DA3CC761CA18FAF62DC273C1AA5651D2FC` | 390 x 844 |
| `overview.png` | 1,279,329 / `8BC330A27FD1D143313BF326254397DB6E71313FDA7AD4F48731C5286D35FD78` | `overview.webp` | 94,234 / `056E13354E9A00C90D9FCF26F8DEB1B8B0DBB4D8DA118073EC71779DDADBE64B` | 1440 x 793 |
| `resume-lab.png` | 1,164,616 / `2AF410212C847FD968EE7079442BBC821140FCBB7818C572DA373AC4663FC552` | `resume-lab.webp` | 84,328 / `539918F58910F81465C23CEC247CA98A80C7A5BC20478161AFE1B18B1F91CA42` | 1440 x 804 |
| `interview.png` | 1,229,564 / `F623FF143B33EDB31F805C5CEB3B5161DC77CF1C3C0B084CAA045A4C0C4BC40E` | `interview.webp` | 80,276 / `22B88272EC29D80CD27A481F15117BC952051B3B396EB6AEAD5FCA339B499459` | 1440 x 809 |
| `pipeline.png` | 1,076,580 / `9B720EC40064D2E9C64166D4E873D0B90C2321E022C89470D14DA49FF386228F` | `pipeline.webp` | 56,778 / `A971D11DB189FD3DF5BDC70336CE672A1809A2DB21289422DC76B91502C87D1E` | 1440 x 803 |
| `opportunity-workspace.png` | 306,678 / `79B1A0282CE0B5F24AD2C33909A9E4A3F211C722EC81EB986C8B879C212589EA` | `opportunity-workspace.webp` | 44,182 / `DFAA0511FD5EE22E2B907556BFD097A37DC441462B56910D9843762740A1A52` | 1440 x 900 |

## Moves, Additions, Deletions（迁移、新增、删除）

- **Moved in the previous showcase commit:** four exact duplicate module screenshots moved from `static/assets/images/showcase/` to `static/assets/showcase/`; SHA-256 was unchanged. The old paths are now absent because the new showcase is their only reference.
- **Added in this fix:** seven WebP replacements and `static/assets/showcase/favicon.png` (64 x 64, 8,318 bytes, SHA-256 `2FD163B366BDA11B808CCC8F0B5094044367B8722AA2C287139C334057B155FE`).
- **Deleted after reference audit:** `static/assets/images/success (2).mp4` (373,943 bytes, SHA-256 `5609AA7549607C1F36D717FE018F940AA043C20483603631108ED875A4129FCD`). `rg` and tracked-file search found no source or dynamic reference; no other `success` asset was removed.
- **Retained:** `coach.png`, all non-showcase dynamic application assets, and the original logo source. The large logo is no longer used as a favicon.

## Reference Rule

`static/showcase.html` references only relative paths under `static/assets/showcase/` plus relative repository documentation links. The page is a GitHub Pages project exhibit, not an online backend; the complete Agent runs after local `start.bat` launch.
