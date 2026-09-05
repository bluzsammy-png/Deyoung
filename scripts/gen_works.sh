#!/bin/bash
# DeYoung portfolio works — 18 real work samples, 3 per category.
# Portrait / Brand / Editorial / Event / Studio / Commercial
set -u
OUT=/home/z/my-project/public/works
mkdir -p "$OUT"

gen() { # $1 file  $2 prompt
  if [ -s "$OUT/$1" ]; then echo "SKIP $1 (exists)"; return 0; fi
  for attempt in 1 2 3; do
    echo "[$1] attempt $attempt ..."
    z-ai image -p "$2" -o "$OUT/$1" -s 1152x864 && [ -s "$OUT/$1" ] && { echo "OK $1"; return 0; }
    sleep 3
  done
  echo "FAIL $1"
  return 1
}

# ---------- PORTRAIT ----------
gen portrait-01.png "Studio portrait of a young Nigerian woman with braided hair, dramatic deep red and black studio backdrop, professional portrait photography, softbox rim lighting, confident expression, sharp focus, high quality, detailed"
gen portrait-02.png "Black and white portrait of a Nigerian man in a tailored suit, dramatic side lighting, dark background, professional studio portrait photography, sharp focus, magazine quality, high quality, detailed"
gen portrait-03.png "Outdoor golden hour portrait of a smiling Nigerian woman in colorful ankara fashion, soft bokeh city background, warm sunlight, professional portrait photography, high quality, detailed"

# ---------- BRAND ----------
gen brand-01.png "Product photography of a luxury shea butter skincare jar on a round podium, warm studio lighting, brand campaign shot, minimal elegant styling, high quality, detailed"
gen brand-02.png "Brand identity flat lay with business cards, letterhead and stationery mockup in red black and white color scheme, top down studio photography, professional branding shoot, high quality, detailed"
gen brand-03.png "Lifestyle brand photo of a barista pouring espresso coffee in a modern Lagos cafe, branded apron, warm tones, professional commercial lifestyle photography, high quality, detailed"

# ---------- EDITORIAL ----------
gen editorial-01.png "Editorial fashion photograph of a model in avant-garde red and black outfit against a concrete wall, magazine cover style, dramatic lighting, high fashion editorial photography, high quality, detailed"
gen editorial-02.png "African male model in flowing agbada robe striding across a rooftop at dusk, cinematic fashion editorial, dramatic sky, magazine quality, high quality, detailed"
gen editorial-03.png "High fashion editorial portrait with bold red gel lighting and dramatic shadow patterns across the face, studio fashion shoot, magazine quality, high quality, detailed"

# ---------- EVENT ----------
gen event-01.png "Traditional Nigerian wedding entrance with couple in aso oke attire, guests celebrating, confetti in the air, professional event photography, vibrant colors, joyful, high quality, detailed"
gen event-02.png "Corporate award night on stage, speaker receiving a plaque under bright stage lights, blurred audience in foreground, professional event coverage photography, high quality, detailed"
gen event-03.png "Birthday party celebration moment with sparkler cake and cheering friends in a decorated venue, candid event photography, warm festive lighting, high quality, detailed"

# ---------- STUDIO ----------
gen studio-01.png "Behind the scenes of a video production studio with cinema camera on tripod, red and black set design, softbox lights glowing, professional studio photography, high quality, detailed"
gen studio-02.png "Podcast studio session with two hosts wearing headphones at a table with microphones, moody red accent lighting, professional studio photography, high quality, detailed"
gen studio-03.png "Photography studio interior with seamless paper backdrop and professional lighting rigs set up, clean modern workspace, high quality, detailed"

# ---------- COMMERCIAL ----------
gen commercial-01.png "Commercial advertisement shot of a soda bottle with dynamic water splash on a bold red background, high speed commercial photography, bold advertising style, high quality, detailed"
gen commercial-02.png "Cinematic TV commercial style shot of a happy family enjoying dinner together at a warm lit table, advertising photography, high quality, detailed"
gen commercial-03.png "Sneaker commercial hero shot floating over a red gradient background with dramatic rim lighting, advertising product photography, high quality, detailed"

echo "=== DONE ==="
ls -la "$OUT"
