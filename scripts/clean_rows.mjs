import { PrismaClient } from "@prisma/client";
const p = new PrismaClient();
await p.message.deleteMany({ where: { email: "buildbot@deyoung.site" } });
await p.booking.deleteMany({ where: { email: "buildbot@deyoung.site" } });
console.log("test rows cleaned");
await p.$disconnect();
