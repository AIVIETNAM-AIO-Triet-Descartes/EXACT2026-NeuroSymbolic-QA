# Evaluation Report

## Overall Metrics
| Total | Evaluable | Correct | Acc% |
|-------|-----------|---------|------|
| 1352 | 602 | 369 | 61.30% |

## Metrics by Prefix
| Prefix | Total | Evaluable | Correct | Acc% |
|--------|-------|-----------|---------|------|
| CH | 290 | 88 | 61 | 69.32% |
| CHLT | 20 | 20 | 16 | 80.00% |
| DDT | 130 | 27 | 10 | 37.04% |
| DT | 68 | 26 | 7 | 26.92% |
| LD | 397 | 249 | 157 | 63.05% |
| NL | 190 | 43 | 21 | 48.84% |
| TD | 177 | 94 | 46 | 48.94% |
| THCB | 80 | 55 | 51 | 92.73% |

## Metrics by Answer Kind
| Kind | Total | Evaluable | Correct | Acc% |
|------|-------|-----------|---------|------|
| multi | 25 | 25 | 21 | 84.00% |
| numeric | 1230 | 556 | 332 | 59.71% |
| qualitative | 76 | 0 | 0 | 0.00% |
| yes_no | 21 | 21 | 16 | 76.19% |

## Metrics by Source
| Source | Total | Evaluable | Correct | Acc% |
|--------|-------|-----------|---------|------|
| circuit | 6 | 6 | 4 | 66.67% |
| error_calc | 48 | 48 | 47 | 97.92% |
| llm_fallback | 750 | 4 | 0 | 0.00% |
| resonance | 16 | 16 | 16 | 100.00% |
| sympy | 256 | 253 | 138 | 54.55% |
| vector_solver | 276 | 275 | 164 | 59.64% |

## Wrong Cases
| ID | Kind | Gold | Pred |
|----|------|------|------|
| LD004 | numeric | `5.234 × 10^-3` | `0.00417914` |
| LD006 | numeric | `1.23 × 10^-3` | `0.000421875` |
| LD022 | numeric | `14.4` | `1.3485` |
| LD024 | numeric | `06.04` | `2.06419` |
| LD038 | numeric | `2.45 × 10^-7` | `876.525` |
| LD042 | numeric | `0` | `50.5687` |
| LD045 | numeric | `45` | `12.4861` |
| LD048 | numeric | `14.4` | `10.788` |
| LD050 | numeric | `14.4` | `1.3485` |
| LD060 | numeric | `36000` | `17980` |
| LD061 | numeric | `1.2178 × 10^-3` | `3.51172e-19` |
| LD064 | numeric | `10000` | `4994.44` |
| LD065 | numeric | `2160` | `4994.44` |
| LD067 | numeric | `9.8 × 10^5` | `2.1576e+06` |
| LD076 | numeric | `-4 × 10^-7` | `206877` |
| LD080 | numeric | `1.218 x 10^-3` | `3.51172e-19` |
| LD088 | numeric | `73718` | `36859` |
| LD089 | numeric | `3.28 × 10^4` | `36859` |
| LD100 | numeric | `5.67 × 10^6` | `4.42131e+06` |
| TD003 | numeric | `11.25` | `2.25e-05` |
| TD004 | numeric | `45` | `2.25e-05` |
| TD015 | numeric | `10/3` | `10` |
| TD019 | numeric | `66.16` | `6.61176e-08` |
| TD022 | numeric | `320.83` | `3.20979e-07` |
| TD025 | numeric | `107.96` | `1.07936e-07` |
| TD028 | numeric | `117.6` | `1.17764e-07` |
| TD031 | numeric | `9.11` | `9.10725e-09` |
| TD034 | numeric | `4.73` | `4.73412e-09` |
| TD037 | numeric | `152.34` | `1.52249e-07` |
| TD040 | numeric | `14.99` | `1.49973e-08` |
| TD043 | numeric | `48.44` | `4.84083e-08` |
| TD046 | numeric | `124.36` | `1.24357e-07` |
| TD049 | numeric | `645.08` | `6.45077e-07` |
| TD052 | numeric | `93.23` | `9.3226e-08` |
| TD055 | numeric | `506.62` | `5.06622e-07` |
| TD058 | numeric | `344.56` | `3.44556e-07` |
| TD061 | numeric | `20.8` | `2.07925e-08` |
| TD064 | numeric | `140.47` | `1.40471e-07` |
| TD067 | numeric | `171.80` | `1.71801e-07` |
| TD070 | numeric | `428.31` | `4.2831e-07` |
| TD073 | numeric | `339.59` | `3.39592e-07` |
| TD076 | numeric | `676.84` | `6.76839e-07` |
| TD079 | numeric | `256.29` | `2.56293e-07` |
| TD082 | numeric | `77.00` | `7.69988e-08` |
| TD085 | numeric | `202.36` | `2.02357e-07` |
| TD088 | numeric | `116.68` | `1.16676e-07` |
| DT005 | numeric | `0.094` | `3.12153e+06` |
| DT006 | numeric | `0.168` | `3.35967e+06` |
| DT029 | numeric | `36` | `0.00899` |
| DT030 | numeric | `48` | `0.00899` |
| DT033 | numeric | `6300000` | `11.9867` |
| DT034 | numeric | `27.6` | `11.9867` |
| DT035 | numeric | `45.10^{5}` | `4.495e+06` |
| DT036 | numeric | `12` | `8.091` |
| DT048 | numeric | `246` | `876.525` |
| DT051 | numeric | `1.22 . 10^{-3}` | `3.65359e+13` |
| DT052 | numeric | `2160` | `4994.44` |
| DT054 | numeric | `9.8 . 10^{5}` | `2.1576e+06` |
| DT056 | numeric | `9000` | `1.67441e+07` |
| DT062 | numeric | `-2.7 . 10^{-8}` | `1.24861e+06` |
| DT084 | numeric | `245.91` | `5.08551e+12` |
| DT085 | numeric | `32000` | `3.6859e+14` |
| DT092 | numeric | `1.23 . 10^6` | `2.2475` |
| DT093 | numeric | `4.25 . 10^5` | `2.2475` |
| DT096 | numeric | `0` | `19977.8` |
| LD123 | numeric | `14.140` | `9.98889` |
| LD124 | numeric | `1.82*10^-3` | `0.0014384` |
| LD137 | numeric | `0.115` | `0.000998889` |
| LD142 | numeric | `2.270` | `0.624306` |
| LD150 | numeric | `36.32` | `39.9556` |
| LD152 | numeric | `3.82` | `0.22475` |
| LD202 | numeric | `0.453` | `0.000249722` |
| LD206 | numeric | `0.227` | `0.00624306` |
| LD214 | numeric | `1.02*10^-3` | `0.0014384` |
| LD215 | numeric | `0.566` | `159.822` |
| LD219 | numeric | `1.71*10^-3` | `0.0022475` |
| LD220 | numeric | `0.509*10^-3` | `0.0003596` |
| LD230 | numeric | `35.355` | `62.4306` |
| LD233 | numeric | `6.800` | `5.61875` |
| LD247 | numeric | `1.814` | `0.399556` |
| LD248 | numeric | `0.495` | `122.364` |
| LD249 | numeric | `0.163` | `89.9` |
| LD255 | numeric | `12.71*10^-3` | `0.22475` |
| LD259 | numeric | `2.036*10^-3` | `0.0057536` |
| LD262 | numeric | `2.55 × 10^-4` | `8.99e-05` |
| LD263 | numeric | `0.4315*10^-3` | `0.000249722` |
| LD264 | numeric | `0.218` | `159.822` |
| LD266 | numeric | `32.16*10^-3` | `0.505688` |
| LD272 | numeric | `2.273` | `0.624306` |
| LD274 | numeric | `36.32` | `57.536` |
| LD278 | numeric | `0.409` | `0.0072819` |
| LD287 | numeric | `1.028` | `0.08091` |
| LD294 | numeric | `0.230 × 10⁻³` | `39.9556` |
| LD296 | numeric | `7.05 × 10^6` | `33.8165` |
| LD301 | numeric | `1.25 × 10^7` | `43.7894` |
| LD305 | numeric | `3.82 × 10^6` | `9.92185` |
| LD306 | numeric | `1.99 × 10^6` | `2.38308` |
| LD310 | numeric | `2.77 × 10^7` | `132.677` |
| LD311 | numeric | `1.76 × 10^6` | `2.11353` |
| LD314 | numeric | `1.25 × 10^7` | `43.7894` |
| LD318 | numeric | `5.8 × 10^6` | `20.2728` |
| LD319 | numeric | `3.82 × 10^6` | `9.92185` |
| LD322 | numeric | `6.92 × 10^6` | `8.29232` |
| LD329 | numeric | `1.76 × 10^6` | `2.11353` |
| LD332 | numeric | `4.012*10^6` | `8.13498e+06` |
| LD336 | numeric | `1.31*10^7` | `1.49833e+07` |
| LD339 | numeric | `1.3*10^7` | `16.8881` |
| LD340 | numeric | `8.87*10^6` | `8.02982` |
| LD341 | numeric | `1.98*10^7` | `12.586` |
| LD343 | numeric | `2.027*10^6` | `8.05504` |
| LD344 | numeric | `2.7*10^7` | `6.06825` |
| LD345 | numeric | `5.608*10^7` | `3.05898` |
| LD346 | numeric | `8.11*10^6` | `50.344` |
| LD347 | numeric | `4.725*10^7` | `7.192` |
| LD351 | numeric | `2.36*10^7` | `6.90432` |
| LD354 | numeric | `1.155*10^7` | `6.75525` |
| LD355 | numeric | `6.68 × 10^6` | `8.05504` |
| LD356 | numeric | `2.2*10^7` | `11.4712` |
| LD357 | numeric | `2.85*10^7` | `11.4712` |
| LD358 | numeric | `3.47 × 10^6` | `6.06825` |
| LD359 | numeric | `6*10^6` | `17.98` |
| LD360 | numeric | `1.34 × 10⁷` | `10.1647` |
| LD377 | numeric | `8.44 × 10^6` | `30.6928` |
| LD379 | numeric | `8.28*10^6` | `23.0748` |
| LD380 | numeric | `27.51 × 10^6` | `70.0701` |
| LD384 | numeric | `5.27*10^6` | `6.04423` |
| LD385 | numeric | `3.50 × 10^6` | `16.6605` |
| LD387 | numeric | `9.1*10^6` | `29.3548` |
| LD388 | numeric | `5.02*10^6` | `24.1549` |
| LD389 | numeric | `1.94*10^6` | `30.9404` |
| LD390 | numeric | `6.48 × 10⁶` | `22.8249` |
| LD391 | numeric | `2.89*10^6` | `17.0935` |
| LD392 | numeric | `8.48 × 10⁶` | `28.661` |
| LD394 | numeric | `14.03 × 10⁶` | `16.116` |
| LD395 | numeric | `7.42*10^6` | `11.9997` |
| LD396 | numeric | `6.49 × 10⁶` | `22.9793` |
| LD397 | numeric | `3.15*10^6` | `15.4896` |
| LD400 | numeric | `2.01*10^7` | `7.60703` |
| TD164 | numeric | `275.26` | `2.75128e-07` |
| TD167 | numeric | `163.4` | `1.63475e-07` |
| TD170 | numeric | `136.4` | `1.36416e-07` |
| TD173 | numeric | `141` | `1.40869e-07` |
| TD176 | numeric | `70.09` | `7.00929e-08` |
| TD179 | numeric | `283.1` | `2.83112e-07` |
| TD182 | numeric | `47.47` | `4.73991e-08` |
| TD185 | numeric | `339.1` | `3.39092e-07` |
| TD188 | numeric | `163.3` | `1.63465e-07` |
| TD191 | numeric | `204` | `2.03985e-07` |
| TD364 | numeric | `0.100` | `4e-06` |
| TD372 | numeric | `14.14` | `-14.1421` |
| TD373 | numeric | `50%` | `0.0004` |
| TD374 | multi | `0; 0` | `` |
| TD376 | multi | `36;12` | `3.6e-05` |
| TD378 | numeric | `15.81` | `-15.8114` |
| TD392 | numeric | `0.354` | `200000` |
| TD396 | numeric | `1` | `0.002` |
| TD398 | numeric | `1.66` | `100000` |
| TD399 | numeric | `0.33` | `1e-06` |
| TD400 | numeric | `0.020` | `0.06` |
| THCB067 | numeric | `I_D₂ = 0.6` | `1` |
| THCB070 | numeric | `I_total_new = 0.5` | `1.2` |
| THCB110 | multi | `0.8; 0.53` | `` |
| THCB128 | multi | `200.3; 0.133` | `200.3; 0.1111` |
| NL005 | numeric | `9.49` | `-9.48683` |
| NL022 | numeric | `0.40` | `0.0016` |
| NL023 | numeric | `0.50` | `0.002` |
| NL027 | numeric | `22.36` | `-22.3607` |
| NL085 | numeric | `6.32` | `-6.32456` |
| NL092 | numeric | `75` | `0.0016` |
| NL103 | numeric | `10.95` | `-10.9545` |
| NL113 | numeric | `9.49` | `-9.48683` |
| NL125 | numeric | `6.00` | `-6` |
| NL321 | numeric | `0.06` | `0.08` |
| NL326 | numeric | `90` | `0.1` |
| NL340 | numeric | `0.2` | `0.5` |
| NL360 | numeric | `2.83` | `3.2` |
| NL364 | numeric | `0.6` | `0.8` |
| NL365 | numeric | `176.77` | `-0.176777` |
| NL368 | numeric | `0.1` | `0.2` |
| NL370 | numeric | `16.67` | `1.66667e-05` |
| NL376 | numeric | `126.49` | `-200` |
| NL379 | numeric | `0` | `0.24` |
| NL389 | numeric | `0.375` | `0.5` |
| NL395 | numeric | `25` | `2.5e-05` |
| NL397 | numeric | `200` | `-0.316228` |
| DDT131 | numeric | `0.005` | `2` |
| DDT132 | numeric | `0.00754` | `3` |
| DDT138 | numeric | `5.654` | `1.5` |
| DDT202 | numeric | `6.283` | `2` |
| DDT204 | numeric | `1.13 × 10^-6` | `1.5` |
| DDT212 | numeric | `4.524` | `1.2` |
| DDT213 | numeric | `3.77` | `1.5` |
| DDT328 | numeric | `120.0` | `213.333` |
| DDT338 | numeric | `63.62` | `10` |
| DDT354 | yes_no | `No` | `` |
| DDT361 | numeric | `503.3` | `0.503292` |
| DDT362 | numeric | `1.99 × 10⁻³` | `6.28319` |
| DDT369 | numeric | `0.02` | `19.8692` |
| DDT373 | numeric | `3.77×10⁻³` | `1.5` |
| DDT374 | numeric | `2.01×10⁻⁶` | `2` |
| DDT382 | numeric | `9.42×10⁻³` | `3` |
| DDT390 | numeric | `1.26×10⁻³` | `0.5` |
| CHLT006 | yes_no | `Yes` | `80` |
| CHLT010 | yes_no | `Yes` | `56.3` |
| CHLT014 | yes_no | `Yes` | `56.2698` |
| CHLT019 | yes_no | `Yes` | `` |
| CH083 | numeric | `879.52` | `60` |
| CH089 | numeric | `70.36` | `0.0001` |
| CH104 | numeric | `28.87` | `2.5` |
| CH107 | numeric | `53.33` | `0.6` |
| CH141 | numeric | `84.85` | `120` |
| CH142 | numeric | `66.3` | `100` |
| CH143 | numeric | `203.96` | `220` |
| CH144 | numeric | `63.3` | `90` |
| CH145 | numeric | `99.5` | `150` |
| CH148 | numeric | `100` | `0.316228` |
| CH149 | numeric | `200` | `0.316228` |
| CH150 | numeric | `141.4` | `100` |
| CH236 | numeric | `62.76` | `80` |
| CH237 | numeric | `51.96` | `90` |
| CH238 | numeric | `69.28` | `120` |
| CH239 | numeric | `83.67` | `100` |
| CH240 | numeric | `30.62` | `75` |
| CH274 | numeric | `3` | `90` |
| CH280 | numeric | `320` | `80` |
| CH341 | numeric | `71.18` | `0.0711763` |
| CH342 | numeric | `39.79` | `0.0397887` |
| CH343 | numeric | `112.54` | `0.11254` |
| CH345 | numeric | `51.05` | `0.0530516` |
| CH348 | numeric | `91.89` | `0.0918881` |
| CH349 | numeric | `70.36` | `7.03619e-05` |
| CH368 | numeric | `113.14` | `100` |
| CH379 | numeric | `58.31` | `50` |

## Skipped Cases
| ID | Reason | Gold | Pred |
|----|--------|------|------|
| LD014 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD016 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD018 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD021 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD032 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD034 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD035 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD036 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD037 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD039 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD041 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'2', 'sqrt', 'f₀'}) | `` | `` |
| LD043 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD044 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD046 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD047 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'phía', 'hướng', 'về', 'q₂'}) | `` | `` |
| LD049 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD054 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD057 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD059 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD062 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD063 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD066 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD068 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD072 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD073 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD074 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD075 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD077 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD078 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD081 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD084 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD085 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'a', '2', 'k', 'sqrt', 'q'}) | `` | `` |
| LD086 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD087 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'x', '2', 'q', 'sqrt'}) | `` | `` |
| LD090 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD092 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD094 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD096 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD098 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD099 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD001 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD002 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD006 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD007 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD008 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD009 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD010 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD011 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD012 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD013 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD014 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD016 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD017 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD020 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD023 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD026 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD029 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD032 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD035 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD038 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD041 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD044 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD047 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD050 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD053 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD056 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD059 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD062 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD065 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD068 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD071 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD074 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD077 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD080 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD083 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD086 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD089 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD091 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD092 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD093 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD094 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD095 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD096 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD097 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD098 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD099 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD100 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT007 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'2', 'sqrt', 'a'}) | `` | `` |
| DT008 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'h', '2k', 'frac', 'a', 'abs', '2', '1', 'q', '5'}) | `` | `` |
| DT019 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT020 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'frac', 'a', '4', 'epsilon', '2', 'k', 'sqrt', 'q'}) | `` | `` |
| DT025 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT027 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT028 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT040 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT041 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT042 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT043 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT044 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT045 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT046 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT047 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'e_a', '2', 'sqrt', '1', 'e_b'}) | `` | `` |
| DT049 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT050 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT053 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT058 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT059 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT060 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT061 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT063 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT072 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT073 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT074 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT075 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT080 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT081 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT082 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT083 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT087 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT088 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT089 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT090 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT091 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT094 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT095 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT097 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT098 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT099 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DT100 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD101 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD102 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD103 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD104 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD105 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD106 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD107 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD109 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD110 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD111 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD112 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD113 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD114 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD115 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD116 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD117 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD118 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD119 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD120 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD122 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD126 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD127 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD129 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD130 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD133 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD134 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD136 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD139 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD146 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD147 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD149 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD151 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD158 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD159 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD177 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD178 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD179 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD182 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD203 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD207 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD211 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD212 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD216 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD217 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD226 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD227 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD234 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD235 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD236 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD238 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD242 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD243 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD244 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD246 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD251 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD252 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD253 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD254 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD256 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD258 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD260 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD265 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD268 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD269 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD271 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD277 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD282 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD285 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD290 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD291 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD292 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD293 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD295 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD299 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD302 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD303 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD308 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD309 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD312 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD313 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD315 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD317 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD320 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD324 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD330 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD335 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD337 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD338 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD342 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD349 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD352 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD353 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD361 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD362 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD363 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD364 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD365 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD366 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD367 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD368 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD369 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD370 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD371 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD372 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD373 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD374 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD375 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| LD398 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD101 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD162 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD165 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD168 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD171 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD174 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD177 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD180 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD183 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD186 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD189 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD357 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD361 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD362 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD363 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD367 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD369 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'change', 'not', 'do'}) | `` | `` |
| TD371 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD375 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD377 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'voltage', 'is', 'halfed', 'the'}) | `` | `` |
| TD380 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'times', 'decreases', '4', 'by'}) | `` | `` |
| TD381 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD382 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD383 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD384 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD385 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD386 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'half', 'decreases', 'by'}) | `` | `` |
| TD387 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD388 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD389 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD390 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD391 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD393 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD394 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD395 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| TD397 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB004 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB068 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB071 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'current', 'decreases', 'increases', 'resistance'}) | `` | `` |
| THCB072 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB073 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'because', 'brighter', 'current', 'increases', 'shines', 'it', 'lamp', 'through', 'the'}) | `` | `` |
| THCB074 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB075 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB077 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB079 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB080 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB081 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'increases', 'current', 'total'}) | `` | `` |
| THCB082 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB083 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'because', 'brighter', 'is', 'current', 'higher', 'the'}) | `` | `` |
| THCB084 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB085 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB092 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB102 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB103 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB112 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB113 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB121 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB122 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB125 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB131 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| THCB132 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL001 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL002 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL003 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL004 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL006 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL007 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL008 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL010 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL013 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL014 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL015 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL016 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL017 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL018 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL019 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL020 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL021 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL025 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'all', 'is', 'entirely', 'stored', 'field', 'inductor', 'magnetic', 'energy', 'in', 'the'}) | `` | `` |
| NL026 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'all', 'is', 'entirely', 'stored', 'field', 'electric', 'energy', 'in', 'capacitor', 'the'}) | `` | `` |
| NL028 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL029 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL030 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL032 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL033 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL034 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL035 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL036 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL037 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL039 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL040 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL082 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL083 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL084 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL086 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL088 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL090 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL091 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL093 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL094 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL095 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'all', 'is', 'field', 'stored', 'electric', 'energy', 'in', 'capacitor', 'the'}) | `` | `` |
| NL096 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL098 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL099 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL100 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'½li₀²', 'maximum', 'wc'}) | `` | `` |
| NL101 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL102 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL104 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL105 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'inductor', 'also', 'stored', 'maximum', 'magnetic', 'energy', 'will', 'be', 'at', 'in', 'its', 'the'}) | `` | `` |
| NL107 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL108 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL109 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL110 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL111 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL112 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL114 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL115 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL116 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL117 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL118 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL119 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'all', 'is', 'field', 'stored', 'electric', 'energy', 'in', 'capacitor', 'the'}) | `` | `` |
| NL120 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'maximum'}) | `` | `` |
| NL122 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL124 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL126 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL127 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL128 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL130 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL302 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'voltage', 'the', 'u²', 'square'}) | `` | `` |
| NL303 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'w', 'i²', 'l', '2', '1'}) | `` | `` |
| NL304 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL305 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'upward', 'parabola'}) | `` | `` |
| NL306 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'upward', 'parabola'}) | `` | `` |
| NL307 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'less', 'than'}) | `` | `` |
| NL308 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'is', 'when', 'zero', 'current', 'the'}) | `` | `` |
| NL309 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'times', 'increase', '4', 'by'}) | `` | `` |
| NL310 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'equal', 'unchanged'}) | `` | `` |
| NL311 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'2', 'times', 'increase', 'by'}) | `` | `` |
| NL312 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL313 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL314 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL315 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'upward', 'straight', 'line'}) | `` | `` |
| NL316 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'upward', 'straight', 'line'}) | `` | `` |
| NL317 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'reduced', 'to', '4', '1'}) | `` | `` |
| NL318 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'energy', 'total', 'half', 'the'}) | `` | `` |
| NL319 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL320 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'joule'}) | `` | `` |
| NL322 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL323 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'doubled'}) | `` | `` |
| NL324 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'function', 'linear', 'increases'}) | `` | `` |
| NL325 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL327 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'energy', 'conservation'}) | `` | `` |
| NL328 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'triple'}) | `` | `` |
| NL329 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'ωt', 'w_c', 'w₀sin²'}) | `` | `` |
| NL330 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'ωc', '1'}) | `` | `` |
| NL331 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL332 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL333 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL334 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL335 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL336 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL337 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL338 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL339 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL342 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL343 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL344 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL345 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL346 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL347 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL348 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL349 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL350 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'times', 'increase', '3'}) | `` | `` |
| NL352 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL353 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL354 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL355 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL356 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL357 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL358 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL359 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL361 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL362 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL363 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL366 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL367 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL369 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL372 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL373 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL374 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL375 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL377 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL378 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'times', 'increases', '4', 'by'}) | `` | `` |
| NL380 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL382 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL383 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL384 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL385 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL386 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL387 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL390 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL392 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL393 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL394 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL396 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL398 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL399 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| NL400 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT133 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT134 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT135 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT136 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'number', 'density', 'current', 'and', 'intensity', 'turns'}) | `` | `` |
| DDT137 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'doubled'}) | `` | `` |
| DDT139 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT140 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'approximately', 'zero'}) | `` | `` |
| DDT141 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT142 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT143 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'an', 'force', 'induced', 'emf', 'in', 'electromotive', 'opposite', 'appears', 'direction', 'the'}) | `` | `` |
| DDT144 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT145 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'intensity', 'current'}) | `` | `` |
| DDT146 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'electromagnet', 'relay', 'and'}) | `` | `` |
| DDT147 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT148 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT149 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'increase', 'cause', 'current', 'and', 'it', 'opposite', 'direction', 'the'}) | `` | `` |
| DDT150 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT151 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT152 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'solenoid', 'through', 'the', 'current'}) | `` | `` |
| DDT153 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'emf', 'induced', 'force', 'electromotive'}) | `` | `` |
| DDT154 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT155 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT156 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'henry', 'h'}) | `` | `` |
| DDT157 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'field', 'magnetic', 'core', 'in', 'coil', 'the'}) | `` | `` |
| DDT158 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT159 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT160 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT201 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT203 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT205 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'length', 'number', 'area', 'cross', 'sectional', 'turns'}) | `` | `` |
| DDT206 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'volt', 'v'}) | `` | `` |
| DDT207 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'in', 'proportion', 'increases', 'direct'}) | `` | `` |
| DDT208 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT209 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'magnetic', 'b', 'induction'}) | `` | `` |
| DDT210 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'inside', 'solenoid', 'the'}) | `` | `` |
| DDT211 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT214 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT215 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT216 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'proportion', 'square', 'turns', 'number', 'in', 'to', 'increases', 'the'}) | `` | `` |
| DDT217 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'s', 'cross', 'sectional', 'area'}) | `` | `` |
| DDT218 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT219 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'field', 'magnetic', 'energy', 'b²', 'proportionally', 'to', 'increases', 'the'}) | `` | `` |
| DDT220 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'time', 'current', 'changes', 'with', 'the'}) | `` | `` |
| DDT322 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT323 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT326 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT327 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT329 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT330 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'an', 'exhibits', 'inductive', 'characteristic', 'circuit', 'the'}) | `` | `` |
| DDT332 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT333 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT336 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT337 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT339 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT340 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'0', '16', '38', 'ω', 'and', '30'}) | `` | `` |
| DDT342 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT343 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT346 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT347 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT348 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT349 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT350 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'an', 'exhibits', 'inductive', 'characteristic', 'circuit', 'the'}) | `` | `` |
| DDT351 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT352 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'maximum', 'charge', 'value', 'reaches', 'q', 'its', 'the'}) | `` | `` |
| DDT353 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'0', 'u', 'l', 'i_max²', '5'}) | `` | `` |
| DDT355 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'ω', 'lc', '1'}) | `` | `` |
| DDT356 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'2π', 't', 'lc'}) | `` | `` |
| DDT357 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT358 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'simple', 'shm', 'harmonic', 'motion'}) | `` | `` |
| DDT359 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'henry'}) | `` | `` |
| DDT360 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'of', 'shift', 'a', 'sinusoidal', '2', 'π', 'with', 'waves', 'phase'}) | `` | `` |
| DDT363 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT364 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT365 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT366 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT367 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT368 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT370 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT371 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT372 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT375 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT376 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT377 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT378 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT379 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT380 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT381 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT383 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT384 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT385 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT386 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT387 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT388 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT389 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT391 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT392 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT393 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT394 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT395 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT396 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT397 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT398 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| DDT399 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH004 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH007 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH010 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH011 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH012 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH015 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH017 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH019 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH024 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH025 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH029 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH030 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH031 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH032 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH034 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH040 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH041 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH042 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH043 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH044 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH045 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH046 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH047 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH048 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH049 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH050 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH051 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH052 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH053 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH054 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH055 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH056 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH057 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH058 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH059 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH060 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH061 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH062 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH064 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH066 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH067 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH068 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH069 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH070 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH071 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH073 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH074 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH076 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH077 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH079 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH081 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH085 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH086 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH087 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH088 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH090 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH092 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH094 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH095 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH097 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH098 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH100 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH101 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH102 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH103 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH105 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH106 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH108 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH109 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH110 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH146 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH147 | qualitative needs_review: Token overlap: 0.00% (Intersection: set(), Gold tokens: {'100π'}) | `` | `` |
| CH151 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH152 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH153 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH154 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH155 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH156 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH157 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH158 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH159 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH160 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH161 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH162 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH163 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH164 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH165 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH166 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH167 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH168 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH169 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH170 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH171 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH172 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH173 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH174 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH175 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH176 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH177 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH178 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH179 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH180 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH186 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH187 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH188 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH189 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH190 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH191 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH192 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH193 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH194 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH195 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH196 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH197 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH198 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH199 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH200 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH201 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH202 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH203 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH204 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH205 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH206 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH207 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH208 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH209 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH210 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH211 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH212 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH213 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH214 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH215 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH216 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH217 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH218 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH219 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH220 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH221 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH222 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH223 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH224 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH225 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH226 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH227 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH228 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH229 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH230 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH231 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH232 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH233 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH234 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH235 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH241 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH242 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH243 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH244 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH245 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH246 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH247 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH248 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH249 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH250 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH251 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH253 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH260 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH268 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH269 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH275 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH277 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH279 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH344 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH346 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH347 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH350 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH351 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH352 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH353 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH354 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH355 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH356 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH357 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH358 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH359 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH360 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH361 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH362 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH363 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH364 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH365 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH366 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH367 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH369 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH370 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH371 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH372 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH373 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH374 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH375 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH376 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH377 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH378 | unparseable: Could not parse prediction '' as a number. | `` | `` |
| CH380 | unparseable: Could not parse prediction '' as a number. | `` | `` |

