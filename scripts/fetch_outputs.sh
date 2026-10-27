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
fetch $OUT_CDN/d8fdb4ac-1105-4e8f-bc7b-e2eb4c1a860c.mp4 output/heat-to-comfort_9x16_1080x1920.mp4 775557b5b24ba1dba1aedc36aa3b214d
fetch $OUT_CDN/736ba957-30e7-41cb-8044-83d8d4506b83.mp4 output/heat-to-comfort_9x16_social.mp4    3b1db4a36e1ef79bf311ecf75c0f63cf
fetch $OUT_CDN/73314dc6-1f07-4dd5-8387-3ba8837724b1.jpg output/storyboard.jpg                       33f64fd6dbe85afedd61c42e7b628384
fetch $OUT_CDN/f081270f-51ae-408f-a778-fa42183eab9e.jpg output/qc_contact_sheet.jpg                 a66d182be3ab8fc517a61175b8afac0a
fetch $OUT_CDN/95a25e8c-5612-4189-ac90-ece51365ae7c.zip output/audio_stems.zip                      75d3ec8e3e1802d8976110212d315088
fetch $OUT_CDN/d0b7699e-6ac8-4753-be11-ee1fb6729b6d.zip output/alfaytri_logo_interim.zip            635e54d59b4494ddb70cb7109a97c4fc

[ "${1:-}" = "--sources" ] || exit 0

mkdir -p clips fonts refs
while read -r name stamp; do
  day=20261026; case "$name" in c05|c06|c07|c08|c09|c11) day=20261027;; esac
  fetch "$GEN_CDN/hf_${day}_${stamp}.mp4" "clips/$name.mp4"
done <<'EOF'
c01 154521_f4d8252f-7efa-46e8-907f-da44924b0c0b
c02 154427_b9a78569-7371-4335-a34f-1fd7a1562d0f
c03 154415_6fd0d631-0a19-4182-b93d-b01ebb40ab5e
c04 154415_a8d07cce-b381-4fd2-9291-72bc8948ff2e
c05 145838_1b6175df-828f-4355-a54f-25bfe6e295f4
c06 145837_3fc8e2da-1016-42e4-ae4a-65c1cda2381c
c07 143956_dc9f1915-862d-4281-a000-583741950fb3
c08 145338_9c540f98-e497-4915-ab0d-20e30bcae544
c09 145837_94d6fbb2-05b4-415b-bfa1-57adf3332315
c10 154521_7b79f5b8-2e76-42dc-862a-2a4e4b55b777
c11 145837_2c6bf299-8272-41aa-a1a6-0b064e418011
EOF
fetch $GEN_CDN/hf_20261026_153101_f19a7983-46aa-4890-9661-7a30f55f65d6.png refs/room.png
fetch $GEN_CDN/hf_20261026_153102_ef20246f-80c7-4af0-a192-6b5cf04db59d.png refs/man.png
fetch $GEN_CDN/hf_20261026_153101_551f620f-8bac-4e5d-b2b8-d6d760a02b53.png refs/technician.png
for w in Bold ExtraBold Medium; do
  fetch "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-$w.ttf" "fonts/Tajawal-$w.ttf"
done
fetch https://github.com/google/fonts/raw/main/ofl/tajawal/OFL.txt fonts/OFL.txt
python3 scripts/brand_logo.py .
echo "sources ready: run scripts/build.sh ."
