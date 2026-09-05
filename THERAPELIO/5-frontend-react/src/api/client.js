const API_BASE = import.meta.env.VITE_API_BASE || "https://therapelio-api.onrender.com";

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export async function registerUser(registrationCode, prenom, poste) {
  const response = await fetch(`${API_BASE}/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ registration_code: registrationCode, prenom, poste }),
  });
  const data = await parseJsonSafe(response);
  if (!response.ok) throw new Error(data.detail || "Code entreprise invalide.");
  return data;
}

export async function recoverUser(recoveryCode) {
  const response = await fetch(`${API_BASE}/v1/auth/recover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recovery_code: recoveryCode }),
  });
  const data = await parseJsonSafe(response);
  if (!response.ok) throw new Error(data.detail || "Code introuvable.");
  return data;
}

export async function sendChatMessage({ message, sessionId, history, userId, prenom, poste }) {
  const response = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      history,
      user_id: userId || "",
      prenom: prenom || "",
      poste: poste || "",
    }),
  });
  return parseJsonSafe(response);
}

export async function fetchSlots(eventTypeId) {
  const response = await fetch(`${API_BASE}/v1/therapists/slots/${eventTypeId}`);
  const data = await parseJsonSafe(response);
  return { ok: response.ok, data };
}

export async function createBooking({ eventTypeId, start, name, email }) {
  const response = await fetch(`${API_BASE}/v1/bookings/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ eventTypeId, start, name, email }),
  });
  return { ok: response.ok, data: await parseJsonSafe(response) };
}
