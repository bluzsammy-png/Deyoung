// Queue the campaign film v7 scenes into the LIVE production queue.
// The Kaggle GPU fleet claims these through /api/worker/claim.
//
// usage: DATABASE_URL='<supabase tx pooler url>' node scripts/film_v7_queue.mjs
import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();

const FILM = "campaign-v7";

// [scene N|spoken line] header is parsed by the worker (piper TTS, local).
// The rest of the prompt drives the local LTX-Video render.
const SCENES = [
  {
    n: 1, seconds: 7, model: "deyo.2", voice: "amy@up",
    line: "Daddy, watch! I made a movie!",
    prompt:
      "Children's cartoon style, warm and rounded 2D animation, a cheerful little girl at a bedroom desk leaps up from her drawing pad holding it high, glowing sparkles burst from the paper and swirl around her beaming face, soft morning light through the window, cozy pastel bedroom, gentle camera push-in, bright modern TV-cartoon look, smooth motion",
  },
  {
    n: 2, seconds: 8, model: "deyo.1", voice: "alan",
    line: "Every child has a story inside. DeYoung sets it free.",
    prompt:
      "Children's cartoon style, 2D animation, drawings of a tiny castle, a rocket ship and a friendly dragon lift off a sketchbook page and grow into a living colorful world filling the screen, the girl watches in wonder from below, floating paint splashes turn into clouds, sweeping camera pull-back revealing the expanding cartoon world, vivid modern animation look",
  },
  {
    n: 3, seconds: 7, model: "deyo.3-pro", voice: "alba",
    line: "Type an idea. Pick a style. Press render.",
    prompt:
      "Modern anime style, crisp cel shading, the same little girl reimagined as a determined anime hero sprinting across moonlit city rooftops, glowing story panels and text ribbons streaming past her like wind trails, neon city lights below, dramatic low-angle tracking shot, cinematic anime action framing, dynamic motion",
  },
  {
    n: 4, seconds: 6, model: "deyo.3", voice: "alba",
    line: "One idea becomes a whole world.",
    prompt:
      "Modern anime style, the anime hero leaps high above the city and touches a floating glowing storyboard panel, it erupts into a swirling galaxy of colorful scenes and characters spreading across the sky, epic wide shot, bloom and particles, cinematic anime scale, sweeping motion",
  },
  {
    n: 5, seconds: 6, model: "deyo.2", voice: "alan",
    line: "And the characters really talk.",
    prompt:
      "Minimal stick man style, hand-drawn whiteboard look, a friendly stick figure with an expressive round head walks confidently along a drawn line that unrolls behind it into a film storyboard, simple drawn speech bubbles pop beside its head as it gestures and chats, playful bouncy animation, clean black ink on white background with a single red accent",
  },
  {
    n: 6, seconds: 6, model: "deyo.2-pro", voice: "amy",
    line: "It made my film before dinner.",
    prompt:
      "Real life, cinematic live action, a proud teenage girl sits at a home desk talking directly to the camera with natural lively mouth movement and a happy grin, her laptop screen glows on her face, posters and fairy lights in the room behind, shallow depth of field, warm evening light, documentary interview framing, natural motion",
  },
  {
    n: 7, seconds: 7, model: "deyo.1-pro", voice: "lessac",
    line: "No studio. No budget. Just her imagination.",
    prompt:
      "Real life, cinematic live action, a mother and her young daughter cuddled on a couch watching a cartoon premiere on the living room TV, the daughter points excitedly at the screen and both laugh, warm lamp light, soft bokeh, gentle slow push-in, filmic color grade, natural family warmth",
  },
  {
    n: 8, seconds: 6, model: "deyo.2", voice: "joe",
    line: "And yes, we actually talk!",
    prompt:
      "Children's cartoon style, a chubby round blue cartoon creature with big expressive eyes hops onto a desk facing the camera, it talks with exaggerated lively mouth movement and waves its little arms, mischievous charming energy, soft studio backdrop, gentle bounce animation, bright modern cartoon look",
  },
  {
    n: 9, seconds: 8, model: "deyo-max", voice: "alba",
    line: "Cartoons. Anime. Real life. Every style, one story.",
    prompt:
      "Creative style-morph montage, a single young hero walking forward seamlessly transforms between art styles as the camera tracks with them, starting as a 2D children's cartoon, shifting into a bold anime hero mid-stride, becoming a real live-action teenager, then a hand-drawn stick figure, then back to cartoon, each style shift marked by a flash of red ribbon energy, dynamic continuous tracking shot, inventive and smooth",
  },
  {
    n: 10, seconds: 8, model: "deyo.1", voice: "alan",
    line: "Our fleet renders every scene in parallel, checks it, merges it, ships it.",
    prompt:
      "Minimal stick man style, whiteboard look, a team of stick figures on floating platforms each draws a different film scene at the same time, glowing scene cards slide along a conveyor of arrows into a big funnel that assembles them into one film strip, the stick figures high-five as the completed film strip glows, clean ink lines, one red accent, playful engineering diagram energy",
  },
  {
    n: 11, seconds: 7, model: "deyo.3", voice: "lessac",
    line: "From imagination to the big screen, in a single day.",
    prompt:
      "Real life, cinematic live action, a warm premiere night in a living room, a projector beam cuts through darkness toward a wall screen playing a colorful cartoon, silhouettes of kids on beanbags cheer with popcorn flying, floating dust in the projector beam, rich cinematic contrast, slow dolly along the beam, filmic grade",
  },
  {
    n: 12, seconds: 8, model: "deyo-max", voice: "ryan",
    line: "DeYoung. Every story deserves a screen.",
    prompt:
      "Elegant 3D end card, a glossy red film strip spirals slowly through a black studio void, converging into a bright red play button emblem glowing at center, subtle gold particles drift, soft studio reflections, slow majestic camera orbit, premium cinematic logo reveal mood, deep blacks and rich reds, no readable text",
  },
];

async function main() {
  // 1) internal owner subscription for the campaign
  let sub = await db.subscription.findFirst({
    where: { email: "studio@deyoung.film", provider: "campaign" },
  });
  if (!sub) {
    sub = await db.subscription.create({
      data: {
        name: "Campaign Studio", email: "studio@deyoung.film", planCode: "elite",
        status: "active", provider: "campaign",
        periodStart: new Date(), periodEnd: new Date(Date.now() + 365 * 864e5),
      },
    });
    console.log("created campaign subscription", sub.id);
  } else {
    console.log("reusing campaign subscription", sub.id);
  }

  // 2) clear stale campaign-v7 rows (idempotent re-run) and old queued v6 scenes
  const stale = await db.videoRequest.findMany({
    where: { email: "studio@deyoung.film", status: { in: ["queued", "rendering", "failed"] } },
    select: { id: true, status: true },
  });
  for (const s of stale) {
    await db.videoRequest.delete({ where: { id: s.id } });
  }
  console.log(`removed ${stale.length} stale studio job(s)`);

  // 3) queue the fleet scenes, scene order = createdAt order (claim order)
  const ids = [];
  for (const sc of SCENES) {
    const row = await db.videoRequest.create({
      data: {
        subscriptionId: sub.id,
        email: "studio@deyoung.film",
        prompt: `[scene ${sc.n}|${sc.line}] ${sc.prompt}`,
        seconds: sc.seconds,
        resolution: "720p",
        withAudio: true,
        watermark: false,
        queuePriority: 100,
        status: "queued",
        model: sc.model,
        voice: sc.voice,
        notes: `${FILM} scene ${sc.n}`,
      },
    });
    ids.push(row.id);
    console.log(`queued scene ${sc.n} (${sc.seconds}s, ${sc.model}, voice ${sc.voice}) -> ${row.id}`);
  }
  const total = SCENES.reduce((a, s) => a + s.seconds, 0);
  console.log(`DONE: ${ids.length} scenes, ${total}s target runtime`);
  await db.$disconnect();
}

main().catch((e) => { console.error(e); process.exit(1); });
