export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "http://localhost:8000";

export const TEAM_COLORS: Record<string, string> = {
  "Red Bull": "#3671C6",
  Ferrari: "#E8002D",
  Mercedes: "#27F4D2",
  McLaren: "#FF8000",
  "Aston Martin": "#229971",
  Alpine: "#FF87BC",
  Williams: "#64C4FF",
  "RB": "#6692FF",
  "Kick Sauber": "#52E252",
  Haas: "#B6BABD",
};

export const POSITION_COLORS: Record<number, string> = {
  1: "#FFD700",
  2: "#C0C0C0",
  3: "#CD7F32",
};
