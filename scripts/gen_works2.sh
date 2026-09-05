#!/bin/bash
# DeYoung works expansion — +12 (2 more per category, files 04 & 05)
set -u
OUT=/home/z/my-project/public/works
mkdir -p "$OUT"

gen() {
  if [ -s "$OUT/$1" ]; then echo "SKIP $1"; return 0; fi
  for attempt in 1 2 3; do
    z-ai image -p "$2" -o "$OUT/$1" -s 1152x864 && [ -s "$OUT/$1" ] && { echo "OK $1"; return 0; }
    sleep 3
  done
  echo "FAIL $1"; return 1
}

gen portrait-04.png "Corporate headshot of a Nigerian businessman with glasses, navy suit, soft grey studio backdrop, professional portrait photography, clean lighting, high quality, detailed"
gen portrait-05.png "Creative portrait of a Nigerian artist with paint-stained hands resting on chin, warm studio light, dark backdrop, professional portrait photography, high quality, detailed"

gen brand-04.png "Packaging design shoot of a premium coffee bag with red and black label on a stone surface, moody studio lighting, brand product photography, high quality, detailed"
gen brand-05.png "Rebrand reveal photo: shopping bag, tote and poster with matching red and white identity arranged on a steps, brand campaign photography, high quality, detailed"

gen editorial-04.png "Editorial fashion shot of two models in monochrome outfits with one red accent piece, against a minimal white studio background, high fashion magazine photography, high quality, detailed"
gen editorial-05.png "Street style editorial of a model crossing a Lagos street at blue hour, neon signs bokeh, fashion magazine photography, cinematic, high quality, detailed"

gen event-04.png "Outdoor naming ceremony celebration with family and traditional decorations, candid joy, professional event photography, colorful, high quality, detailed"
gen event-05.png "Concert crowd with hands up under red stage lights and confetti falling, professional live event photography, energetic, high quality, detailed"

gen studio-04.png "Green screen studio with actor on mark and crew adjusting cinema lights, behind the scenes production photography, professional, high quality, detailed"
gen studio-05.png "Audio recording booth with voice actor at a condenser microphone through glass, red accent studio lighting, professional photography, high quality, detailed"

gen commercial-04.png "Perfume bottle commercial shot with silk fabric flowing behind it on a red backdrop, luxury advertising photography, dramatic lighting, high quality, detailed"
gen commercial-05.png "Food commercial shot of a burger with steam and flying ingredients on dark slate, advertising food photography, dramatic light, high quality, detailed"

echo "=== DONE ==="
ls "$OUT" | wc -l
