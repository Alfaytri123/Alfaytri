#!/usr/bin/env bash
# Download the rendered deliverables into output/ and verify their checksums.
# With --sources, also fetch the 11 generated clips, the fonts and the reference
# stills needed to re-render locally with scripts/build.sh.
#
# Needs outbound HTTPS to d2ol7oe51mr4n9.cloudfront.net (deliverables) and, for
# --sources, d8j0ntlcm91z4.cloudfront.net (generated media) and github.com (fonts).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT_CDN=https://d2ol7oe51mr4n9.cloudfront.net/user_3BiFgptSIlNEBqmFayoRfUtddGd
GEN_CDN=https://d8j0ntlcm91z4.cloudfront.net/user_3BiFgptSIlNEBqmFayoRfUtddGd

fetch() {  # url dest md5
  curl -fsSL --retry 3 -o "$2" "$1"
  if [ -n "${3:-}" ]; then echo "$3  $2" | md5sum -c --quiet - && echo "ok  $2"; else echo "got $2"; fi
}

mkdir -p output
fetch $OUT_CDN/74bde6ab-900c-4c50-9f4e-69c6d673c402.mp4 output/heat-to-comfort_9x16_1080x1920.mp4 1562c7a8180d070331d99d1dab3d7e38
fetch $OUT_CDN/50f28435-5fa9-4122-b3cc-462bc60ecb9b.mp4 output/heat-to-comfort_9x16_social.mp4    cb4b84d58aabf23960e68ff7ca47c5e9
fetch $OUT_CDN/ce331a2d-dce3-425c-9679-6c8b43cc07d8.jpg output/storyboard.jpg                       f4421e25b1081243fae17b2fab50d570
fetch $OUT_CDN/4ccd055d-ed38-4196-9e80-00028889f544.jpg output/qc_contact_sheet.jpg                 dad57f85ffa898ebbc325cf751b88409
fetch $OUT_CDN/46b8fc25-0af7-476f-913c-17753a1ff831.zip output/audio_stems.zip                      4077ea12013b9142ab0c9e32f5a83c67

[ "${1:-}" = "--sources" ] || exit 0

mkdir -p clips fonts refs
while read -r name stamp; do
  fetch "$GEN_CDN/hf_20261026_${stamp}.mp4" "clips/$name.mp4"
done <<'EOF'
c01 154521_f4d8252f-7efa-46e8-907f-da44924b0c0b
c02 154427_b9a78569-7371-4335-a34f-1fd7a1562d0f
c03 154415_6fd0d631-0a19-4182-b93d-b01ebb40ab5e
c04 154415_a8d07cce-b381-4fd2-9291-72bc8948ff2e
c05 154521_01c87d6f-fc03-4c46-bc6a-bb57dcf0d150
c06 154415_4fc9d843-546b-4e79-b042-eb2ac84b61b4
c07 154427_e0e6234d-d7fe-44cc-a525-b2e75d762021
c08 154415_46e4e9d7-363e-4635-a626-ccaf223cdefd
c09 154415_ecd1b00b-6c76-4598-aaf0-6086a5830870
c10 154521_7b79f5b8-2e76-42dc-862a-2a4e4b55b777
c11 154415_71d52cf9-0962-4e1c-8d4e-a88d6a8f498b
EOF
fetch $GEN_CDN/hf_20261026_153101_f19a7983-46aa-4890-9661-7a30f55f65d6.png refs/room.png
fetch $GEN_CDN/hf_20261026_153102_ef20246f-80c7-4af0-a192-6b5cf04db59d.png refs/man.png
fetch $GEN_CDN/hf_20261026_153101_551f620f-8bac-4e5d-b2b8-d6d760a02b53.png refs/technician.png
for w in Bold ExtraBold Medium; do
  fetch "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-$w.ttf" "fonts/Tajawal-$w.ttf"
done
fetch https://github.com/google/fonts/raw/main/ofl/tajawal/OFL.txt fonts/OFL.txt
echo "sources ready: run scripts/build.sh ."
