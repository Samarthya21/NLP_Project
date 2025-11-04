import { NextResponse } from "next/server";
import axios from "axios";
import { parseBookingCommand } from "@/lib/parser";

export async function POST(req) {
  try {
    const { text } = await req.json();
    const parsedData = parseBookingCommand(text);
    console.log("Parsed Data:", parsedData);
    //const mlResponse = await axios.post("https://public-ml-server.example.com/api", parsedData, {
    //  headers: { "Content-Type": "application/json" }
    //});

    return NextResponse.json({
      parsed: parsedData,
      //mlResponse: mlResponse.data
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
