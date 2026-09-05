import { createContext, useContext, useState } from "react";
import { registerUser, recoverUser } from "../api/client";

const AuthContext = createContext(null);

function readStorage(key) {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

export function AuthProvider({ children }) {
  const [userId, setUserId] = useState(() => readStorage("therapelio_user_id"));
  const [prenom, setPrenom] = useState(() => readStorage("therapelio_prenom"));
  const [poste, setPoste] = useState(() => readStorage("therapelio_poste"));

  function saveProfile(id, newPrenom, newPoste) {
    try {
      localStorage.setItem("therapelio_user_id", id);
      localStorage.setItem("therapelio_prenom", newPrenom || "");
      localStorage.setItem("therapelio_poste", newPoste || "");
    } catch {
      // Stockage indisponible (navigation privée stricte, etc.) : le profil reste
      // actif pour la session en cours via l'état React, simplement non persistant.
    }
    setUserId(id);
    setPrenom(newPrenom || "");
    setPoste(newPoste || "");
  }

  async function register(registrationCode, prenomInput, posteInput) {
    const result = await registerUser(registrationCode, prenomInput, posteInput);
    saveProfile(result.user_id, prenomInput, posteInput);
    return result.recovery_code;
  }

  async function recover(recoveryCode) {
    const result = await recoverUser(recoveryCode);
    saveProfile(result.user_id, result.prenom, result.poste);
  }

  function logout() {
    try {
      localStorage.removeItem("therapelio_user_id");
      localStorage.removeItem("therapelio_prenom");
      localStorage.removeItem("therapelio_poste");
    } catch {
      // rien à faire si le stockage est indisponible
    }
    setUserId("");
    setPrenom("");
    setPoste("");
  }

  const hasProfile = Boolean(userId && prenom);

  return (
    <AuthContext.Provider value={{ userId, prenom, poste, hasProfile, register, recover, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un AuthProvider");
  return ctx;
}
