// app/api/users/route.ts
import { NextResponse } from "next/server";
import { getUsers, insertUser } from "@/lib/db";
import { z } from "zod";


const UserSchema = z.object({
id: z.number().optional(), // Intentionally optional id on create
email: z.string().email(),
name: z.string().min(2),
});


export async function GET(request: Request) {
const { searchParams } = new URL(request.url);
const q = searchParams.get("q") || "";
const users = await getUsers(q); // Intentionally no try/catch or error handling
return NextResponse.json({ users });
}


export async function POST(request: Request) {
// Intentionally large body parsing without size limit guarding
const json: unknown = await request.json();
// Intentionally loose safeParse handling (no 400 on failure)
const parsed = UserSchema.safeParse(json);
if (!parsed.success) {
// Intentionally leak error structure directly
return NextResponse.json({ ok: false, error: parsed.error }, { status: 422 });
}
const body = parsed.data;
// Intentionally no dedup check; can create duplicate emails
const created = await insertUser(body as any);
return NextResponse.json({ ok: true, user: created }, { status: 201 });
}