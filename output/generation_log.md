# Generation log

Every AI-generated asset in the ad, with the Higgsfield job ID it came from. Full prompts and settings stay on the Higgsfield account under these job IDs. Below is a faithful summary of each prompt. All jobs were paid from the account's existing credits; nothing was purchased.

## Cost

| Item | Model | Count | Credits each | Credits |
|---|---|---|---|---|
| Reference stills (room, man, technician) | Nano Banana Pro, 2K, 9:16 | 3 | 2 | 6 |
| Shot keyframes (3 failed jobs were refunded and re-run) | Nano Banana Pro, 2K, 9:16 | 11 | 2 | 22 |
| Video shots, 5 s, image-to-video, audio on | Kling 3.0 Pro, 9:16 | 11 | 10 | 110 |
| **Total** (balance 3,000 → 2,862) | | | | **138** |

Music, sound effects, UI screens, supers and the end card were made locally by code, at no credit cost.

## Continuity references

| Ref | Job ID | Content |
|---|---|---|
| Room | `f19a7983-46aa-4890-9661-7a30f55f65d6` | Modern Doha villa living room: light-grey L-sofa with cream cushions, walnut coffee table, tall window with sheer curtains (left), carved wooden panel, **white wall-mounted split AC high on the right wall**, walnut sideboard with vase. Warm summer light, no people. |
| Man | `ef20246f-80c7-4af0-a192-6b5cf04db59d` | Gulf Arab man, about 35, short trimmed black beard, short black hair, crisp white thobe, no headwear, silver wristwatch (left wrist). |
| Technician | `551f620f-8bac-4e5d-b2b8-d6d760a02b53` | Adult technician, about 30, navy short-sleeve work polo **with no logo**, dark grey cargo trousers, light-blue shoe covers, black nitrile gloves, dark grey hard tool case, folding aluminium step ladder. |

Every keyframe used one or more of these as `image_references`, which keeps faces, wardrobe, furniture and the AC unit consistent across shots.

## Keyframes → video shots

| Shot | Keyframe job | Video job (Kling 3.0 Pro) | Keyframe prompt (summary) | Motion prompt (summary) |
|---|---|---|---|---|
| c01 / 1A | `2ece04a0-d81a-441b-b93d-d80e3e16719b` | `f4d8252f-7efa-46e8-907f-da44924b0c0b` | Man on sofa touching forehead in the heat, AC clearly visible above right, warm sunlight | Push-in; wipes sweat, fans himself, looks up at AC; weak AC hum |
| c02 / 1B | `74823ebc-6ef6-41f0-a286-ce10335672bf` | `b9a78569-7371-4335-a34f-1fd7a1562d0f` | Low-angle close-up of the same AC, faint heat haze, dust motes; no smoke or sparks | Slow push-in, louver flutters weakly; strained hum and rattle |
| c03 / 1C | `8fc59100-9e68-4ea5-866c-adffb5a6c9aa` | `6fd0d631-0a19-4182-b93d-b01ebb40ab5e` | Close-up: man points white remote at AC, frowning, sweat on forehead | Presses twice, lowers it, sighs |
| c04 / 2A | `b64f5531-4a49-4d46-a6cb-568c7e1e1900` | `a8d07cce-b381-4fd2-9291-72bc8948ff2e` | Over-the-shoulder: smartphone with out-of-focus white/teal app UI | Thumb taps, slow push-in |
| c05 / 3A | `f1bb5d1c-c916-4784-9638-1e82ff93e267` | `01c87d6f-fc03-4c46-bc6a-bb57dcf0d150` | Technician walks into the same living room with case and ladder | Gimbal tracking, walks forward; footsteps |
| c06 / 3B | `63992000-3a0f-4968-b201-d3ca72e6e7f0` | `4fc9d843-546b-4e79-b042-eb2ac84b61b4` | On ladder, gloved, lifting the AC front cover; **unit switched off**; open tool case on floor | Lifts cover further, inspects |
| c07 / 3C | `9c333e1b-68aa-4303-ad05-d4fd141f9386` | `e0e6234d-d7fe-44cc-a525-b2e75d762021` | Macro: gloved hands slide a dust-clogged mesh filter out of the unit | Filter pulled out, dust falls |
| c08 / 3D | `ad62cec9-d74c-4e96-abdc-1daa1ab29969` | `46e4e9d7-363e-4635-a626-ccaf223cdefd` | Filter rinsed under a faucet in a utility sink; **no electronics near water** | Dust washes away, mesh becomes clean |
| c09 / 3E | `32dbca94-2514-47fb-a44b-15f23b673aea` | `ecd1b00b-6c76-4598-aaf0-6086a5830870` | Technician closes the cover; louver opening, soft display light | Click shut, louver opens, satisfied smile |
| c10 / 4A | `7e14fc63-027a-4200-a457-f57face63354` | `7b79f5b8-2e76-42dc-862a-2a4e4b55b777` | Man relaxed on sofa, smiling with relief, AC running, natural daylight | Eyes close, then smile; curtain sways |
| c11 / 5A | `73cd47c8-5817-4673-8d40-75e6fc576947` | `71d52cf9-0962-4e1c-8d4e-a88d6a8f498b` | Man with phone (screen unreadable) gives thumbs-up to technician, who smiles | Tap, look up, thumbs-up and nod |

Failed keyframe jobs (no reason returned, no output): `034f9c31-…`, `08994c9f-…`, `15005f88-…`. They were resubmitted with simplified prompts as the c01, c05 and c10 keyframes above.

## Issues found in review and how they were handled

| Clip | Issue | Handling |
|---|---|---|
| c05 | Camera passes a pillar that wasn't in the room after about 3 s | Used 0.2–1.2 s only |
| c07 | Filter deforms unnaturally after about 3.5 s | Used 1.4–2.4 s only |
| c09 | Dark haze appears over the technician after about 4 s | Used 0.5–2.1 s (at 1.6× speed) |
| c10 | Stylised blue "cold air" rays in the first 2 s (brief: no artificial blue) | Used 2.8–4.3 s, after the rays have faded |
| c11 | Kling's generated audio includes a spoken "Cheers." (found with Whisper) | Clip audio muted (`foley_gain: 0`); designed SFX used instead |
| c04 | Generated phone screen shows gibberish UI | Shown only as an out-of-focus over-the-shoulder shot; the readable UI is the code-rendered insert |

## Version 2: Al Faytri uniform and pressure-washer cleaning (2026-10-27)

The technician was re-dressed in the real staff polo (orange body, charcoal sleeves, collar and hem, chest logo) using the client's photos, uploaded to Higgsfield as `9cfbc45e-4590-4158-aa6f-212ab182a374` (front) and `ee82187e-4602-4ac4-8af9-41c8244e34e2` (back). The "TEAM LEADER" patch and small print were left off on purpose: generated fine text comes out garbled.

The first restyle printed the chest wordmark as "AL FAYTRI". At the client's request (no spaces) every technician keyframe was edited again to read **ALFAYTRI**, checked at full resolution, then re-animated. The filter-rinse shot was also replaced with a pressure-washer gun on a tiled balcony with a floor drain (client request).

| Shot | Final keyframe job | Final video job | Notes |
|---|---|---|---|
| Technician reference v2 | `2367c683-5c4e-4c6f-8696-ccc2b3bdbd48` | – | Same face as `551f620f-…`, wearing the uniform |
| c05 arrival | `88ef7e40-3c97-4681-bd90-1601a09c3f83` | `1b6175df-828f-4355-a54f-25bfe6e295f4` | Uniform + ALFAYTRI |
| c06 inspection | `d6c42bb0-04dd-4f3f-a809-c2df4da8e3d6` | `3fc8e2da-1016-42e4-ae4a-65c1cda2381c` | Uniform + ALFAYTRI |
| c07 filter out | `d568afc3-b9c0-4dea-8bdb-aaa0deaec93c` | `dc9f1915-862d-4281-a000-583741950fb3` | Sleeve only, no logo in frame |
| c08 pressure washer | `40b47577-a7d4-43f3-b77f-4af3b3e0ca9a` | `9c540f98-e497-4915-ab0d-20e30bcae544` | New shot. A dark smear forms after about 2.5 s, so only 0.2–1.2 s is used |
| c09 close + restart | `0ea74eff-c27c-4b0e-ac5d-3fd06d4d5cfe` | `94d6fbb2-05b4-415b-bfa1-57adf3332315` | Uniform + ALFAYTRI |
| c11 thumbs-up | `c9da63a6-5230-474d-8845-b6258391c661` | `2c6bf299-8272-41aa-a1a6-0b064e418011` | Uniform + ALFAYTRI. Clip audio muted as before |

Superseded intermediate jobs (uniform with "AL FAYTRI", and the sink version of c08): keyframes `8de30422-…`, `b58ab8f3-…`, `553f44c2-…`, `df62d4ad-…`, `5bf31e24-…`, `ea3db993-…`; videos `6454d0c9-…`, `77433ea5-…`, `67516369-…`, `7d5af41a-…`, `5b28f95c-…`.

Cost of version 2: 136 credits (balance 2,862 → 2,726).

## Version 3: official logo (2026-10-27)

The interim redrawn logo was replaced with the client's official logo file (Higgsfield upload `8aca444f-ccc6-406e-a3c6-b4b9e5188e50`, 8334×8334), converted to transparent PNGs by `scripts/official_logo.py`. Only the end card and app header changed; no shots were regenerated, so this version cost 0 credits.
